"""Tests for data connectors."""

import pytest
from src.connectors.json_csv import JsonCsvConnector
from src.connectors.filesystem import FileSystemConnector


class TestJsonCsvConnector:
    """Test JSON/CSV connector."""

    def test_load_json(self, sample_json_file):
        """Test loading JSON file."""
        connector = JsonCsvConnector(sample_json_file)
        data = connector.load()

        assert len(data) == 2
        assert data[0]["name"] == "Item 1"
        assert data[1]["value"] == 200

    def test_load_csv(self, sample_csv_file):
        """Test loading CSV file."""
        connector = JsonCsvConnector(sample_csv_file)
        data = connector.load()

        assert len(data) == 2
        assert data[0]["name"] == "Item 1"
        assert int(data[1]["value"]) == 200

    def test_stream(self, sample_json_file):
        """Test streaming data."""
        connector = JsonCsvConnector(sample_json_file)
        batches = list(connector.stream(batch_size=1))

        assert len(batches) == 2
        assert len(batches[0]) == 1

    def test_get_stats(self, sample_json_file):
        """Test getting file statistics."""
        connector = JsonCsvConnector(sample_json_file)
        stats = connector.get_stats()

        assert "file_path" in stats
        assert stats["record_count"] == 2
        assert "avg_record_size" in stats

    def test_normalize_nested_json(self, sample_json_file):
        """Test normalizing nested JSON."""
        connector = JsonCsvConnector(sample_json_file)
        nested = {"name": "Test", "details": {"age": 30, "city": "NYC"}}
        flattened = connector.normalize_nested_json(nested)

        assert "name" in flattened
        assert "details.age" in flattened
        assert flattened["details.age"] == 30


class TestFileSystemConnector:
    """Test filesystem connector."""

    def test_scan_directory(self, sample_files_dir):
        """Test directory scanning."""
        connector = FileSystemConnector(sample_files_dir)
        files = connector.scan_directory()

        assert len(files) == 3
        assert any(f["name"] == "document.txt" for f in files)

    def test_categorize_files(self, sample_files_dir):
        """Test file categorization."""
        connector = FileSystemConnector(sample_files_dir)
        categorized = connector.list_by_category()

        assert len(categorized["documents"]) >= 1
        assert len(categorized["images"]) >= 1
        assert len(categorized["video"]) >= 1

    def test_get_directory_stats(self, sample_files_dir):
        """Test directory statistics."""
        connector = FileSystemConnector(sample_files_dir)
        stats = connector.get_directory_stats()

        assert stats["total_files"] == 3
        assert "total_size_bytes" in stats
        assert "by_category" in stats

    def test_stream_files(self, sample_files_dir):
        """Test streaming files."""
        connector = FileSystemConnector(sample_files_dir)
        batches = list(connector.stream_files(batch_size=1))

        assert len(batches) >= 3

    def test_read_file(self, sample_files_dir):
        """Test reading file contents."""
        connector = FileSystemConnector(sample_files_dir)
        content = connector.read_file("document.txt")

        assert b"Test document content" in content
