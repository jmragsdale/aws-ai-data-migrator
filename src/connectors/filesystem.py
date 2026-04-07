"""Filesystem data connector."""

import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Iterator, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FileSystemConnector:
    """Connector for scanning and streaming files from filesystem."""

    FILE_CATEGORIES = {
        "documents": [".pdf", ".doc", ".docx", ".txt", ".xlsx", ".csv", ".json", ".xml"],
        "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
        "video": [".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"],
        "audio": [".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"],
    }

    def __init__(self, root_path: str):
        """
        Initialize filesystem connector.

        Args:
            root_path: Root directory to scan
        """
        self.root_path = Path(root_path)
        if not self.root_path.exists():
            raise FileNotFoundError(f"Path not found: {root_path}")
        if not self.root_path.is_dir():
            raise ValueError(f"Path must be a directory: {root_path}")

    def scan_directory(self, recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Scan directory and return file metadata.

        Args:
            recursive: Scan subdirectories

        Returns:
            List of file metadata dictionaries
        """
        files = []
        pattern = "**/*" if recursive else "*"

        for file_path in self.root_path.glob(pattern):
            if file_path.is_file():
                files.append(self._get_file_metadata(file_path))

        logger.info(f"Scanned {len(files)} files in {self.root_path}")
        return files

    def _get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get metadata for a file."""
        stat = file_path.stat()
        mime_type, _ = mimetypes.guess_type(str(file_path))

        return {
            "path": str(file_path),
            "name": file_path.name,
            "size_bytes": stat.st_size,
            "modified_timestamp": stat.st_mtime,
            "mime_type": mime_type or "application/octet-stream",
            "category": self._categorize_file(file_path.suffix),
        }

    @classmethod
    def _categorize_file(cls, suffix: str) -> str:
        """Categorize file by extension."""
        suffix_lower = suffix.lower()
        for category, extensions in cls.FILE_CATEGORIES.items():
            if suffix_lower in extensions:
                return category
        return "other"

    def stream_files(self, category: Optional[str] = None, batch_size: int = 10) -> Iterator[List[Dict[str, Any]]]:
        """
        Stream files in batches.

        Args:
            category: Optional file category to filter
            batch_size: Files per batch

        Yields:
            Batches of file metadata
        """
        all_files = self.scan_directory()

        if category:
            all_files = [f for f in all_files if f["category"] == category]

        for i in range(0, len(all_files), batch_size):
            yield all_files[i : i + batch_size]

    def get_directory_stats(self) -> Dict[str, Any]:
        """
        Get directory statistics.

        Returns:
            Statistics dictionary
        """
        files = self.scan_directory()
        total_size = sum(f["size_bytes"] for f in files)

        categories = {}
        for f in files:
            cat = f["category"]
            if cat not in categories:
                categories[cat] = {"count": 0, "total_size_bytes": 0}
            categories[cat]["count"] += 1
            categories[cat]["total_size_bytes"] += f["size_bytes"]

        return {
            "root_path": str(self.root_path),
            "total_files": len(files),
            "total_size_bytes": total_size,
            "avg_file_size_bytes": total_size / len(files) if files else 0,
            "by_category": categories,
        }

    def read_file(self, file_path: str) -> bytes:
        """
        Read file contents.

        Args:
            file_path: Relative or absolute path to file

        Returns:
            File contents as bytes
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.root_path / path

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return path.read_bytes()

    def list_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List files organized by category.

        Returns:
            Files grouped by category
        """
        files = self.scan_directory()
        result = {cat: [] for cat in self.FILE_CATEGORIES.keys()}
        result["other"] = []

        for file_meta in files:
            result[file_meta["category"]].append(file_meta)

        return result
