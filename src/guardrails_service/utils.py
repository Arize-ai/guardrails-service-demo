import json
from typing import List, Dict, Any
from pathlib import Path


class DataLoader:
    def __init__(self, data_dir: str = "demo/data"):
        self.data_dir = Path(data_dir)

    def get_available_datasets(self) -> List[str]:
        """Get list of available dataset files"""
        datasets = []
        for file in self.data_dir.glob("*.json"):
            datasets.append(file.stem)
        return sorted(datasets)

    def load_dataset(self, dataset_name: str) -> List[Dict[str, Any]]:
        """Load any dataset by name"""
        dataset_file = self.data_dir / f"{dataset_name}.json"
        if not dataset_file.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_file}")

        with open(dataset_file, "r") as f:
            return json.load(f)

    def load_datasets(self) -> List[Dict[str, Any]]:
        """Load all datasets"""
        datasets = []
        for file in self.get_available_datasets():
            datasets.append(self.load_dataset(file))
        return sorted(datasets)
