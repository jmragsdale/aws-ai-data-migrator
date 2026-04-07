"""Tests for S3 and DynamoDB migrators."""

import pytest
from moto import mock_dynamodb, mock_s3
import boto3
from src.migrators.dynamodb import DynamoDBMigrator
from src.migrators.s3 import S3Migrator


class TestDynamoDBMigrator:
    """Test DynamoDB migrator."""

    @mock_dynamodb
    def test_create_table(self):
        """Test table creation."""
        migrator = DynamoDBMigrator(region="us-east-1")
        result = migrator.create_table(
            table_name="test-table",
            partition_key="id",
            sort_key="timestamp",
            billing_mode="PAY_PER_REQUEST",
        )

        assert result["TableName"] == "test-table"
        assert result["BillingModeSummary"]["BillingMode"] == "PAY_PER_REQUEST"

    @mock_dynamodb
    def test_batch_write_items(self):
        """Test batch write."""
        migrator = DynamoDBMigrator(region="us-east-1")

        # Create table
        migrator.create_table("test-table", "id", "timestamp")
        migrator.wait_for_table("test-table")

        # Write items
        items = [
            {"id": {"S": "1"}, "timestamp": {"S": "2024-04-01"}, "data": {"S": "test1"}},
            {"id": {"S": "2"}, "timestamp": {"S": "2024-04-02"}, "data": {"S": "test2"}},
        ]

        result = migrator.batch_write_items("test-table", items, batch_size=25)

        assert result["table_name"] == "test-table"
        assert result["total_items"] == 2

    @mock_dynamodb
    def test_get_table_stats(self):
        """Test getting table statistics."""
        migrator = DynamoDBMigrator(region="us-east-1")

        # Create table
        migrator.create_table("test-table", "id")

        stats = migrator.get_table_stats("test-table")

        assert stats["table_name"] == "test-table"
        assert "item_count" in stats
        assert "size_bytes" in stats

    @mock_dynamodb
    def test_delete_table(self):
        """Test table deletion."""
        migrator = DynamoDBMigrator(region="us-east-1")

        # Create table
        migrator.create_table("test-table", "id")

        # Delete table
        migrator.delete_table("test-table")

        # Verify deletion
        with pytest.raises(Exception):
            migrator.get_table_stats("test-table")


class TestS3Migrator:
    """Test S3 migrator."""

    @mock_s3
    def test_create_bucket(self):
        """Test bucket creation."""
        migrator = S3Migrator(region="us-east-1")
        result = migrator.create_bucket(
            bucket_name="test-bucket",
            versioning=True,
            encryption="AES256",
        )

        assert result["bucket_name"] == "test-bucket"
        assert result["versioning"] is True

    @mock_s3
    def test_upload_file(self, tmp_path):
        """Test file upload."""
        migrator = S3Migrator(region="us-east-1")

        # Create bucket
        migrator.create_bucket("test-bucket")

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Upload
        key = migrator.upload_file("test-bucket", str(test_file), "test.txt")

        assert key == "test.txt"

    @mock_s3
    def test_upload_batch(self, tmp_path):
        """Test batch upload."""
        migrator = S3Migrator(region="us-east-1")

        # Create bucket
        migrator.create_bucket("test-bucket")

        # Create test files
        files = []
        for i in range(3):
            f = tmp_path / f"test{i}.txt"
            f.write_text(f"content {i}")
            files.append(str(f))

        # Upload batch
        result = migrator.upload_batch("test-bucket", files)

        assert result["total_files"] == 3
        assert result["successful"] == 3

    @mock_s3
    def test_get_bucket_stats(self, tmp_path):
        """Test bucket statistics."""
        migrator = S3Migrator(region="us-east-1")

        # Create bucket
        migrator.create_bucket("test-bucket")

        # Create and upload file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        migrator.upload_file("test-bucket", str(test_file), "test.txt")

        # Get stats
        stats = migrator.get_bucket_stats("test-bucket")

        assert stats["bucket"] == "test-bucket"
        assert stats["object_count"] == 1
        assert stats["total_size_bytes"] > 0

    @mock_s3
    def test_delete_bucket(self):
        """Test bucket deletion."""
        migrator = S3Migrator(region="us-east-1")

        # Create bucket
        migrator.create_bucket("test-bucket")

        # Delete bucket
        migrator.delete_bucket("test-bucket", force=True)

        # Verify deletion
        s3 = boto3.client("s3", region_name="us-east-1")
        buckets = s3.list_buckets()
        bucket_names = [b["Name"] for b in buckets["Buckets"]]
        assert "test-bucket" not in bucket_names
