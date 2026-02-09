import chromadb
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from transformers import AutoTokenizer, AutoModel
import torch
import json
import uuid
from datetime import datetime
import os
from abc import ABC, abstractmethod

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class BaseVectorDatabase(ABC):
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    compare_to: int = 1
    threshold: float = 0.5

    def __init__(self, collection_name: str, persist_directory: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

        # Use a lightweight model for embeddings
        self.model_name = os.getenv("EMBEDDING_MODEL_NAME", DEFAULT_MODEL_NAME)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.eval()

    @abstractmethod
    def get_threshold(self) -> float:
        """Get the threshold for this type of detection"""
        pass

    @abstractmethod
    def calculate_detection_score(
        self, request: Dict[str, Any], threshold: float = None, compare_to: int = None
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """Calculate detection score with subclass-specific logic"""
        pass

    def _vectorize_request(self, request: Dict[str, Any]) -> List[float]:
        """Convert request data to vector representation"""
        text = request.get("text", "")

        # Tokenize and encode
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512, padding=True
        )

        with torch.no_grad():
            outputs = self.model(**inputs)
            # Use mean pooling of token embeddings
            embeddings = outputs.last_hidden_state.mean(dim=1).squeeze()

        return embeddings.numpy().tolist()

    def add_entry(self, request: Dict[str, Any]) -> int:
        """Add a single entry to the vector database"""
        vector = self._vectorize_request(request)
        entry_id = str(uuid.uuid4())
        self.collection.add(
            embeddings=[vector],
            documents=[json.dumps(request)],
            metadatas=[request],
            ids=[entry_id],
        )
        return 1

    def add_baseline_data(self, requests: List[Dict[str, Any]]) -> int:
        """Add baseline dataset to vector database"""
        vectors = []
        documents = []
        metadatas = []
        ids = []

        for req in requests:
            vector = self._vectorize_request(req)
            vectors.append(vector)
            documents.append(json.dumps(req))
            metadatas.append(
                {
                    "timestamp": req.get("timestamp", datetime.now().isoformat()),
                    "text_length": len(req.get("text", "")),
                }
            )
            ids.append(str(uuid.uuid4()))

        self.collection.add(
            embeddings=vectors, documents=documents, metadatas=metadatas, ids=ids
        )

        return len(requests)

    def find_similar(
        self, request: Dict[str, Any], n_results: int = None, threshold: float = None
    ) -> Tuple[List[Dict], List[float]]:
        """Find n most similar requests in the baseline"""
        query_vector = self._vectorize_request(request)

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=self.compare_to if n_results is None else n_results,
            include=["documents", "metadatas", "distances"],
        )

        similar_requests = []
        distances = []
        if (
            results["documents"]
            and results["documents"][0]
            and results["distances"]
            and results["distances"][0]
        ):
            for doc, distance, metadata in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0],
            ):
                distances.append(distance)
                if threshold is not None and distance < threshold:
                    req_data = json.loads(doc)
                    req_data["metadata"] = metadata
                    similar_requests.append(req_data)
        return similar_requests, distances

    def _calculate_base_stats(
        self, request: Dict[str, Any], threshold: float = None, compare_to: int = None
    ) -> Dict[str, Any]:
        """Calculate base statistics for similarity analysis"""
        threshold = threshold if threshold is not None else self.get_threshold()
        compare_to = compare_to if compare_to is not None else self.compare_to

        similar_requests, distances = self.find_similar(
            request, n_results=compare_to, threshold=threshold
        )

        if not distances:
            return {"reason": "No baseline data available", "threshold": threshold}

        median_distance = float(np.median(distances))
        mean_distance = float(np.mean(distances))
        min_distance = float(min(distances))
        max_distance = float(max(distances))

        stats = {
            "median_distance": median_distance,
            "mean_distance": mean_distance,
            "min_distance": min_distance,
            "max_distance": max_distance,
            "threshold": threshold,
            "similar_records_count": len(similar_requests),
            "similar_records": similar_requests,
            "distances": distances,
        }

        return stats

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the baseline collection"""
        count = self.collection.count()
        return {"total_records": count, "collection_name": self.collection.name}

    def clear_baseline(
        self, before: Optional[datetime] = None, after: Optional[datetime] = None
    ) -> int:
        """Clear baseline data with optional date filtering

        Args:
            before: Remove entries before this date (exclusive)
            after: Remove entries after this date (inclusive)

        Returns:
            Number of records removed
        """
        try:
            if before is None and after is None:
                # Clear all data
                count = self.collection.count()
                collection_name = self.collection.name
                self.client.delete_collection(name=collection_name)
                self.collection = self.client.get_or_create_collection(
                    name=collection_name, metadata={"hnsw:space": "cosine"}
                )
                return count

            # Get all records to filter by date
            all_results = self.collection.get(include=["documents", "metadatas"])

            if not all_results["ids"]:
                return 0

            ids_to_remove = []

            for i, metadata in enumerate(all_results["metadatas"]):
                timestamp_str = metadata.get("timestamp")
                if not timestamp_str:
                    continue

                try:
                    record_timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                    should_remove = False

                    if before is not None and after is not None:
                        # Remove entries between after (inclusive) and before (exclusive)
                        should_remove = after <= record_timestamp < before
                    elif before is not None:
                        # Remove entries before this date (exclusive)
                        should_remove = record_timestamp < before
                    elif after is not None:
                        # Remove entries after this date (inclusive)
                        should_remove = record_timestamp >= after

                    if should_remove:
                        ids_to_remove.append(all_results["ids"][i])

                except (ValueError, TypeError):
                    # Skip records with invalid timestamps
                    continue

            if ids_to_remove:
                self.collection.delete(ids=ids_to_remove)

            return len(ids_to_remove)

        except Exception:
            return 0

    def get_baseline_entries(
        self, before: Optional[datetime] = None, after: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get baseline entries with optional date filtering

        Args:
            before: Get entries before this date (exclusive)
            after: Get entries after this date (inclusive)

        Returns:
            List of baseline entries
        """
        try:
            # Get all records
            all_results = self.collection.get(include=["documents", "metadatas"])

            if not all_results["documents"]:
                return []

            entries = []

            for i, (doc, metadata) in enumerate(
                zip(all_results["documents"], all_results["metadatas"])
            ):
                try:
                    # Parse the document to get the original request data
                    request_data = json.loads(doc)

                    # Get timestamp from metadata or document
                    timestamp_str = metadata.get("timestamp") or request_data.get(
                        "timestamp"
                    )
                    if not timestamp_str:
                        continue

                    # Parse timestamp
                    record_timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )

                    # Apply date filtering
                    should_include = True

                    if before is not None and after is not None:
                        # Include entries between after (inclusive) and before (exclusive)
                        should_include = after <= record_timestamp < before
                    elif before is not None:
                        # Include entries before this date (exclusive)
                        should_include = record_timestamp < before
                    elif after is not None:
                        # Include entries after this date (inclusive)
                        should_include = record_timestamp >= after

                    if should_include:
                        entries.append(
                            {
                                "text": request_data.get("text", ""),
                                "timestamp": record_timestamp,
                            }
                        )

                except (ValueError, TypeError, json.JSONDecodeError):
                    # Skip records with invalid data
                    continue

            return entries

        except Exception:
            return []


class AnomalyVectorDatabase(BaseVectorDatabase):
    """Vector database for anomaly detection - dissimilarity indicates anomaly"""

    def __init__(self, persist_directory: str = "./chroma_db"):
        super().__init__("traffic_baseline", persist_directory)
        self.threshold = float(os.getenv("ANOMALY_THRESHOLD", "0.7"))
        self.compare_to = int(os.getenv("ANOMALY_COMPARE_TO", "10"))

    def get_threshold(self) -> float:
        return self.threshold

    def calculate_detection_score(
        self, request: Dict[str, Any], threshold: float = None, compare_to: int = None
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """Calculate if request is anomalous based on vector similarity"""

        if threshold is None:
            threshold = self.threshold
        if compare_to is None:
            compare_to = self.compare_to

        stats = self._calculate_base_stats(request, threshold, compare_to)

        if not stats["distances"]:
            return True, 1.0, stats

        # For anomaly detection: use median distance (robust against outliers)
        # We want to know if the request is generally unusual, not just different from one edge case
        median_distance = stats["median_distance"]
        threshold_used = stats["threshold"]

        # For anomaly detection: high distance = anomaly
        is_anomaly = median_distance > threshold_used
        confidence_score = float(1.0 - median_distance)

        # Update stats to reflect which metric was used for decision
        stats["detection_distance"] = median_distance
        stats["detection_metric"] = "median_distance"

        return is_anomaly, confidence_score, stats


class MaliciousVectorDatabase(BaseVectorDatabase):
    """Vector database for malicious detection - similarity indicates malicious content"""

    def __init__(self, persist_directory: str = "./chroma_db"):
        super().__init__("malicious_baseline", persist_directory)
        self.threshold = float(os.getenv("MALICIOUS_THRESHOLD", "0.25"))
        self.compare_to = int(os.getenv("MALICIOUS_COMPARE_TO", "10"))

    def get_threshold(self) -> float:
        return self.threshold

    def calculate_detection_score(
        self, request: Dict[str, Any], threshold: float = None, compare_to: int = None
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """Calculate if request is malicious based on vector similarity"""

        if threshold is None:
            threshold = self.threshold
        if compare_to is None:
            compare_to = self.compare_to

        stats = self._calculate_base_stats(request, threshold, compare_to)

        if not stats["distances"]:
            return False, 0.0, stats

        # For malicious detection: use minimum distance (closest match)
        # If ANY known malicious pattern is very similar, that's a strong signal
        min_distance = stats["min_distance"]
        threshold_used = stats["threshold"]

        # For malicious detection: low distance (high similarity) = malicious
        is_malicious = min_distance < threshold_used
        # Invert confidence score so similarity becomes confidence
        confidence_score = float(min_distance)

        # Update stats to reflect which metric was used for decision
        stats["detection_distance"] = min_distance
        stats["detection_metric"] = "min_distance"

        return is_malicious, confidence_score, stats
