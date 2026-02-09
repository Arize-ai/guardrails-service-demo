"""
Dataset Manager for Arize Integration

Manages baseline datasets in Arize and syncs them with the vector store.
"""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import httpx
from arize.experimental.datasets import ArizeDatasetsClient
from arize.pandas.proto.flight_pb2 import DatasetType


class DatasetManager:
    """Manages Arize datasets and vector store synchronization"""

    def __init__(
        self,
        arize_api_key: str = None,
        arize_space_id: str = None,
        guardrails_api_url: str = None,
    ):
        """
        Initialize the dataset manager

        Args:
            arize_api_key: Arize API key
            arize_space_id: Arize Space ID
            guardrails_api_url: URL to guardrails API
        """
        self.arize_api_key = arize_api_key or os.getenv("ARIZE_API_KEY")
        self.arize_space_id = arize_space_id or os.getenv("ARIZE_SPACE_ID")
        self.guardrails_api_url = guardrails_api_url or os.getenv("GUARDRAILS_API_URL")

        if not self.arize_api_key:
            raise ValueError("ARIZE_API_KEY must be set")
        if not self.arize_space_id:
            raise ValueError("ARIZE_SPACE_ID must be set")

        self.client = ArizeDatasetsClient(api_key=self.arize_api_key)

        # Path to example data
        self.examples_dir = Path(__file__).parent.parent / "examples" / "data"

    def check_and_sync_datasets(
        self, anomaly_dataset_name: str, malicious_dataset_name: str
    ) -> Dict[str, str]:
        """
        Check for datasets in Arize and sync with vector store

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
        Sync a single dataset from Arize to vector store

        Args:
            dataset_name: Name of the Arize dataset
            example_file: Filename of example data if dataset doesn't exist
            api_endpoint: API endpoint to upload data to vector store

        Returns:
            Status message
        """
        # Check if dataset exists in Arize
        dataset_exists, dataset = self._check_dataset_exists(dataset_name)

        if dataset_exists:
            # Load from Arize
            print(f"Found dataset '{dataset_name}' in Arize, loading...")
            records = self._load_dataset_from_arize(dataset)
            status = f"Loaded from Arize ({len(records)} records)"
        else:
            # Create from example data
            print(f"Dataset '{dataset_name}' not found, creating from examples...")
            try:
                records = self._load_example_data(example_file)

                # Create dataset in Arize
                self._create_arize_dataset(dataset_name, records)
                status = f"Created from examples ({len(records)} records)"
            except Exception as e:
                # If creation fails (e.g., dataset was just created), try to load it
                print(f"Failed to create dataset, attempting to load: {e}")
                dataset_exists, dataset = self._check_dataset_exists(dataset_name)
                if dataset_exists:
                    records = self._load_dataset_from_arize(dataset)
                    status = f"Loaded from Arize ({len(records)} records)"
                else:
                    raise Exception(f"Dataset upload failed: {str(e)}")

        # Upload to vector store
        uploaded_count = self._upload_to_vector_store(records, api_endpoint)
        status += f", uploaded {uploaded_count} to vector store"

        return status

    def _check_dataset_exists(self, dataset_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a dataset exists in Arize (lightweight check without loading data)

        Args:
            dataset_name: Name of the dataset

        Returns:
            Tuple of (exists: bool, dataset_name or None)
        """

        try:
            # List all datasets in the space (lightweight operation)
            datasets_df = self.client.list_datasets(space_id=self.arize_space_id)

            # Check if our dataset name is in the list
            if dataset_name in datasets_df["dataset_name"].values:
                return True, dataset_name
            else:
                return False, None
        except Exception as e:
            print(f"Error checking if dataset {dataset_name} exists: {e}")
            return False, None

    def _load_dataset_from_arize(self, dataset_name: str) -> List[Dict]:
        """
        Load dataset from Arize and convert to records format

        Args:
            dataset_name: Arize dataset name

        Returns:
            List of records with 'text' and 'timestamp' fields
        """
        # Get dataset from Arize
        df = self.client.get_dataset(
            space_id=self.arize_space_id, dataset_name=dataset_name
        )

        print(f"Loaded DataFrame with {len(df)} rows")
        print(f"DataFrame columns: {df.columns.tolist()}")
        if len(df) > 0:
            print(f"First row sample: {df.iloc[0].to_dict()}")

        # Convert to records format expected by vector store
        records = []
        for _, row in df.iterrows():
            # Arize datasets should have 'text' and 'timestamp' columns
            text_val = row.get("text", "")
            timestamp_val = row.get("timestamp", "")

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

    def _create_arize_dataset(self, dataset_name: str, records: List[Dict]) -> str:
        """
        Create a dataset in Arize from records

        Args:
            dataset_name: Name for the new dataset
            records: List of records to upload

        Returns:
            Dataset ID
        """
        try:
            # Convert records to DataFrame
            df = pd.DataFrame(records)

            # Create dataset in Arize
            dataset_id = self.client.create_dataset(
                space_id=self.arize_space_id,
                dataset_name=dataset_name,
                dataset_type=DatasetType.Value("GENERATIVE"),
                data=df,
            )

            print(f"Created dataset '{dataset_name}' in Arize with ID: {dataset_id}")
            return dataset_id
        except Exception as e:
            print(f"Error creating Arize dataset: {e}")
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
        Get information about all managed datasets

        Returns:
            Dictionary with dataset information
        """
        info = {}

        try:
            # Get list of all datasets once
            datasets_df = self.client.list_datasets(space_id=self.arize_space_id)

            for dataset_name in names:
                # Check if dataset exists in the list
                matching_datasets = datasets_df[
                    datasets_df["dataset_name"] == dataset_name
                ]

                if not matching_datasets.empty:
                    dataset_row = matching_datasets.iloc[0]
                    info[dataset_name] = {
                        "exists": True,
                        "name": dataset_name,
                        "created_at": str(dataset_row.get("created_at", "unknown")),
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
        Add a single entry to an Arize dataset

        Args:
            dataset_name: Name of the dataset
            text: The request text
            timestamp: ISO format timestamp

        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize timestamp - strip milliseconds to match existing format
            # Convert "2025-10-15T18:11:11.756Z" to "2025-10-15T18:11:11"
            ts = timestamp.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            normalized_timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S")
            print(
                f"Normalized timestamp from '{timestamp}' to '{normalized_timestamp}'"
            )

            # Check if dataset exists
            dataset_exists, _ = self._check_dataset_exists(dataset_name)

            if dataset_exists:
                # Get existing dataset and append new row
                print(f"Appending to existing dataset {dataset_name}")

                # Load existing data
                existing_df = self.client.get_dataset(
                    space_id=self.arize_space_id,
                    dataset_name=dataset_name
                )

                # Create new row
                new_row = pd.DataFrame(
                    [{"text": text, "timestamp": normalized_timestamp}]
                )

                # Concatenate existing data with new row
                combined_df = pd.concat([existing_df, new_row], ignore_index=True)

                # Update dataset with combined data
                self.client.update_dataset(
                    space_id=self.arize_space_id,
                    dataset_name=dataset_name,
                    data=combined_df,
                )
                print(f"Added entry to existing dataset {dataset_name} (total rows: {len(combined_df)})")
            else:
                # Create new dataset with single entry
                print(f"Creating new dataset {dataset_name} with entry")
                new_row = pd.DataFrame(
                    [{"text": text, "timestamp": normalized_timestamp}]
                )
                self.client.create_dataset(
                    space_id=self.arize_space_id,
                    dataset_name=dataset_name,
                    dataset_type=DatasetType.Value("GENERATIVE"),
                    data=new_row,
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
        Sync an Arize dataset to the vector store

        Clears the vector store first, then uploads all data from Arize dataset.

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
            dataset_exists, _ = self._check_dataset_exists(dataset_name)

            if not dataset_exists:
                error_msg = f"Dataset {dataset_name} not found"
                print(f"ERROR: {error_msg}")
                return {"success": False, "error": error_msg}

            # Clear the vector store first to avoid duplicates
            print(f"Step 2: Clearing vector store at {clear_endpoint}...")
            records_cleared = self._clear_vector_store(clear_endpoint)
            print(f"Cleared {records_cleared} records")

            # Load records from Arize
            print(f"Step 3: Loading records from Arize dataset...")
            records = self._load_dataset_from_arize(dataset_name)
            print(f"Loaded {len(records)} records from Arize")

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
