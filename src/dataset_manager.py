"""
Dataset Manager for Phoenix Integration

Manages baseline datasets in Phoenix and syncs them with the vector store.
"""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import httpx
from phoenix.client import Client


class DatasetManager:
    """Manages Phoenix datasets and vector store synchronization"""

    def __init__(
        self,
        phoenix_endpoint: str = None,
        guardrails_api_url: str = None,
    ):
        """
        Initialize the dataset manager

        Args:
            phoenix_endpoint: Phoenix server endpoint URL
            guardrails_api_url: URL to guardrails API
        """
        self.phoenix_endpoint = phoenix_endpoint or os.getenv(
            "PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006"
        )
        self.guardrails_api_url = guardrails_api_url or os.getenv("GUARDRAILS_API_URL")

        self.client = Client(base_url=self.phoenix_endpoint)

        # Path to example data
        self.examples_dir = Path(__file__).parent.parent / "examples" / "data"

    def check_and_sync_datasets(
        self, anomaly_dataset_name: str, malicious_dataset_name: str
    ) -> Dict[str, str]:
        """
        Check for datasets in Phoenix and sync with vector store

        Args:
            anomaly_dataset_name: Name of the anomaly dataset
            malicious_dataset_name: Name of the malicious dataset

        Returns:
            Dictionary with sync status for each dataset
        """
        results = {}

        # Handle anomaly baseline
        try:
            results["anomaly"] = self._sync_dataset(
                dataset_name=anomaly_dataset_name,
                example_file="baseline.json",
                api_endpoint="/anomaly/baseline/upload",
            )
        except Exception as e:
            results["anomaly"] = f"Error: {str(e)}"

        # Handle malicious baseline
        try:
            results["malicious"] = self._sync_dataset(
                dataset_name=malicious_dataset_name,
                example_file="malicious_baseline.json",
                api_endpoint="/malicious/baseline/upload",
            )
        except Exception as e:
            results["malicious"] = f"Error: {str(e)}"

        return results

    def _sync_dataset(
        self, dataset_name: str, example_file: str, api_endpoint: str
    ) -> str:
        """
        Sync a single dataset from Phoenix to vector store

        Args:
            dataset_name: Name of the Phoenix dataset
            example_file: Filename of example data if dataset doesn't exist
            api_endpoint: API endpoint to upload data to vector store

        Returns:
            Status message
        """
        # Check if dataset exists in Phoenix
        dataset_exists = self._check_dataset_exists(dataset_name)

        if dataset_exists:
            # Load from Phoenix
            print(f"Found dataset '{dataset_name}' in Phoenix, loading...")
            records = self._load_dataset_from_phoenix(dataset_name)
            status = f"Loaded from Phoenix ({len(records)} records)"
        else:
            # Create from example data
            print(f"Dataset '{dataset_name}' not found, creating from examples...")
            try:
                records = self._load_example_data(example_file)

                # Create dataset in Phoenix
                self._create_phoenix_dataset(dataset_name, records)
                status = f"Created from examples ({len(records)} records)"
            except Exception as e:
                # If creation fails (e.g., dataset was just created), try to load it
                print(f"Failed to create dataset, attempting to load: {e}")
                if self._check_dataset_exists(dataset_name):
                    records = self._load_dataset_from_phoenix(dataset_name)
                    status = f"Loaded from Phoenix ({len(records)} records)"
                else:
                    raise Exception(f"Dataset upload failed: {str(e)}")

        # Upload to vector store
        uploaded_count = self._upload_to_vector_store(records, api_endpoint)
        status += f", uploaded {uploaded_count} to vector store"

        return status

    def _check_dataset_exists(self, dataset_name: str) -> bool:
        """
        Check if a dataset exists in Phoenix

        Args:
            dataset_name: Name of the dataset

        Returns:
            True if dataset exists, False otherwise
        """
        try:
            datasets = self.client.datasets.list()
            return any(ds["name"] == dataset_name for ds in datasets)
        except Exception as e:
            print(f"Error checking if dataset {dataset_name} exists: {e}")
            return False

    def _load_dataset_from_phoenix(self, dataset_name: str) -> List[Dict]:
        """
        Load dataset from Phoenix and convert to records format

        Args:
            dataset_name: Phoenix dataset name

        Returns:
            List of records with 'text' and 'timestamp' fields
        """
        dataset = self.client.datasets.get_dataset(dataset=dataset_name)
        df = dataset.to_dataframe()

        print(f"Loaded DataFrame with {len(df)} rows")
        print(f"DataFrame columns: {df.columns.tolist()}")
        if len(df) > 0:
            print(f"First row sample: {df.iloc[0].to_dict()}")

        # Convert from Phoenix input/metadata format to records
        records = []
        for _, row in df.iterrows():
            input_data = row.get("input", {})
            metadata = row.get("metadata", {})

            text_val = input_data.get("text", "") if isinstance(input_data, dict) else ""
            timestamp_val = metadata.get("timestamp", "") if isinstance(metadata, dict) else ""

            if text_val:
                record = {
                    "text": str(text_val),
                    "timestamp": (
                        str(timestamp_val)
                        if timestamp_val
                        else datetime.now().isoformat()
                    ),
                }
                records.append(record)

        print(f"Converted to {len(records)} records")
        return records

    def _load_example_data(self, filename: str) -> List[Dict]:
        """
        Load example data from JSON file

        Args:
            filename: Name of the example file

        Returns:
            List of records
        """
        file_path = self.examples_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Example file not found: {file_path}")

        with open(file_path, "r") as f:
            data = json.load(f)

        # Extract requests array
        return data.get("requests", [])

    def _create_phoenix_dataset(self, dataset_name: str, records: List[Dict]) -> None:
        """
        Create a dataset in Phoenix from records

        Args:
            dataset_name: Name for the new dataset
            records: List of records to upload
        """
        try:
            inputs = [{"text": r["text"]} for r in records]
            metadata = [
                {"timestamp": r.get("timestamp", datetime.now().isoformat())}
                for r in records
            ]

            dataset = self.client.datasets.create_dataset(
                name=dataset_name,
                inputs=inputs,
                metadata=metadata,
            )

            print(f"Created dataset '{dataset_name}' in Phoenix")
        except Exception as e:
            print(f"Error creating Phoenix dataset: {e}")
            raise

    def _clear_vector_store(self, clear_endpoint: str) -> int:
        """
        Clear the vector store via API

        Args:
            clear_endpoint: API endpoint for clearing

        Returns:
            Number of records cleared
        """
        try:
            # Make API call to clear all records (no date filters)
            response = httpx.post(
                f"{self.guardrails_api_url}{clear_endpoint}",
                json={},  # Empty request clears all
                timeout=60.0,
            )

            if response.status_code == 200:
                data = response.json()
                cleared = data.get("records_removed", 0)
                print(f"Cleared {cleared} records from vector store")
                return cleared
            else:
                print(f"Failed to clear vector store: {response.status_code}")
                print(f"Response: {response.text}")
                return 0

        except Exception as e:
            print(f"Error clearing vector store: {e}")
            return 0

    def _upload_to_vector_store(self, records: List[Dict], api_endpoint: str) -> int:
        """
        Upload records to the vector store via API

        Args:
            records: List of records to upload
            api_endpoint: API endpoint for upload

        Returns:
            Number of records uploaded
        """
        try:
            # Prepare payload
            payload = {"requests": records}

            # Make API call with extended timeout for large datasets
            response = httpx.post(
                f"{self.guardrails_api_url}{api_endpoint}",
                json=payload,
                timeout=300.0,  # 5 minutes for large uploads
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("records_added", len(records))
            else:
                print(f"Failed to upload to vector store: {response.status_code}")
                print(f"Response: {response.text}")
                return 0

        except Exception as e:
            print(f"Error uploading to vector store: {e}")
            return 0

    def get_dataset_info(self, names: List[str]) -> Dict[str, any]:
        """
        Get information about managed datasets

        Returns:
            Dictionary with dataset information
        """
        info = {}

        try:
            datasets = self.client.datasets.list()
            datasets_by_name = {ds["name"]: ds for ds in datasets}

            for dataset_name in names:
                if dataset_name in datasets_by_name:
                    ds = datasets_by_name[dataset_name]
                    info[dataset_name] = {
                        "exists": True,
                        "name": dataset_name,
                        "created_at": str(ds.get("created_at", "unknown")),
                        "example_count": ds.get("example_count", 0),
                    }
                else:
                    info[dataset_name] = {"exists": False}

        except Exception as e:
            import traceback

            info["error"] = str(e)
            print(f"Error in get_dataset_info: {e}")
            print(traceback.format_exc())

        return info

    def add_to_dataset(self, dataset_name: str, text: str, timestamp: str) -> bool:
        """
        Add a single entry to a Phoenix dataset

        Args:
            dataset_name: Name of the dataset
            text: The request text
            timestamp: ISO format timestamp

        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize timestamp - strip milliseconds to match existing format
            ts = timestamp.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            normalized_timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S")
            print(
                f"Normalized timestamp from '{timestamp}' to '{normalized_timestamp}'"
            )

            if self._check_dataset_exists(dataset_name):
                # Append to existing dataset
                print(f"Appending to existing dataset {dataset_name}")
                self.client.datasets.add_examples_to_dataset(
                    dataset=dataset_name,
                    inputs=[{"text": text}],
                    metadata=[{"timestamp": normalized_timestamp}],
                )
                print(f"Added entry to existing dataset {dataset_name}")
            else:
                # Create new dataset with single entry
                print(f"Creating new dataset {dataset_name} with entry")
                self.client.datasets.create_dataset(
                    name=dataset_name,
                    inputs=[{"text": text}],
                    metadata=[{"timestamp": normalized_timestamp}],
                )
                print(f"Created new dataset {dataset_name} with entry")

            return True

        except Exception as e:
            import traceback

            print(f"Error adding to dataset: {e}")
            print(traceback.format_exc())
            return False

    def sync_dataset_to_vector_store(
        self, type: str, dataset_name: str
    ) -> Dict[str, any]:
        """
        Sync a Phoenix dataset to the vector store

        Clears the vector store first, then uploads all data from Phoenix dataset.

        Args:
            type: 'anomaly' or 'malicious'
            dataset_name: Name of the dataset

        Returns:
            Dictionary with sync results
        """
        api_endpoint = f"/{type}/baseline/upload"
        clear_endpoint = f"/{type}/baseline/clear"

        print(f"=== Starting sync for {type} dataset: {dataset_name} ===")

        try:
            # Check if dataset exists
            print(f"Step 1: Checking if dataset exists...")
            if not self._check_dataset_exists(dataset_name):
                error_msg = f"Dataset {dataset_name} not found"
                print(f"ERROR: {error_msg}")
                return {"success": False, "error": error_msg}

            # Clear the vector store first to avoid duplicates
            print(f"Step 2: Clearing vector store at {clear_endpoint}...")
            records_cleared = self._clear_vector_store(clear_endpoint)
            print(f"Cleared {records_cleared} records")

            # Load records from Phoenix
            print(f"Step 3: Loading records from Phoenix dataset...")
            records = self._load_dataset_from_phoenix(dataset_name)
            print(f"Loaded {len(records)} records from Phoenix")

            # Upload to vector store
            print(f"Step 4: Uploading to vector store at {api_endpoint}...")
            uploaded_count = self._upload_to_vector_store(records, api_endpoint)
            print(f"Uploaded {uploaded_count} records")

            result = {
                "success": True,
                "dataset": dataset_name,
                "records_cleared": records_cleared,
                "records_synced": uploaded_count,
                "total_records": len(records),
            }
            print(f"=== Sync complete for {type}: {result} ===")
            return result

        except Exception as e:
            import traceback

            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"ERROR during {type} sync: {error_msg}")
            return {"success": False, "error": str(e)}
