"""JSON and CSV data connectors."""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JsonCsvConnector:
    """Connector for JSON and CSV files."""

    def __init__(self, file_path: str):
        """
        Initialize JSON/CSV connector.

        Args:
            file_path: Path to JSON or CSV file
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

    def load_json(self) -> List[Dict[str, Any]]:
        """
        Load JSON file (single document or array).

        Returns:
            List of normalized documents
        """
        with open(self.file_path, "r") as f:
            data = json.load(f)

        # Normalize to list of documents
        if isinstance(data, dict):
            records = [data]
        elif isinstance(data, list):
            records = data
        else:
            raise ValueError("JSON must be a dict or list of dicts")

        logger.info(f"Loaded {len(records)} records from {self.file_path.name}")
        return records

    def load_csv(self, delimiter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load CSV file with auto-delimiter detection.

        Args:
            delimiter: CSV delimiter (auto-detected if None)

        Returns:
            List of normalized documents
        """
        # Auto-detect delimiter
        if delimiter is None:
            with open(self.file_path, "r") as f:
                sample = f.read(1024)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            logger.info(f"Auto-detected CSV delimiter: '{delimiter}'")

        records = []
        with open(self.file_path, "r", newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            records = list(reader)

        logger.info(f"Loaded {len(records)} records from {self.file_path.name}")
        return records

    def load(self) -> List[Dict[str, Any]]:
        """
        Load file based on extension.

        Returns:
            List of normalized documents
        """
        suffix = self.file_path.suffix.lower()
        if suffix == ".json":
            return self.load_json()
        elif suffix == ".csv":
            return self.load_csv()
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def stream(self, batch_size: int = 100) -> Iterator[List[Dict[str, Any]]]:
        """
        Stream documents in batches.

        Args:
            batch_size: Number of documents per batch

        Yields:
            Batches of documents
        """
        records = self.load()
        for i in range(0, len(records), batch_size):
            yield records[i : i + batch_size]

    def normalize_nested_json(self, obj: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        Flatten nested JSON structures.

        Args:
            obj: JSON object to normalize
            prefix: Prefix for nested keys

        Returns:
            Flattened dictionary
        """
        result = {}
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                result.update(self.normalize_nested_json(value, full_key))
            elif isinstance(value, list):
                result[full_key] = json.dumps(value)
            else:
                result[full_key] = value

        return result

    def get_stats(self) -> Dict[str, Any]:
        """
        Get file statistics.

        Returns:
            Statistics dictionary
        """
        file_size = self.file_path.stat().st_size
        records = self.load()

        return {
            "file_path": str(self.file_path),
            "file_size_bytes": file_size,
            "record_count": len(records),
            "avg_record_size": file_size / len(records) if records else 0,
            "sample_record": records[0] if records else None,
        }
