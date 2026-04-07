"""Pytest configuration and fixtures."""

import pytest
from moto import mock_dynamodb, mock_s3
import boto3
from pathlib import Path
import json


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def anthropic_key(monkeypatch):
    """Mock Anthropic API key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")


@pytest.fixture
@mock_dynamodb
def dynamodb():
    """Create mock DynamoDB."""
    return boto3.resource("dynamodb", region_name="us-east-1")


@pytest.fixture
@mock_s3
def s3():
    """Create mock S3."""
    return boto3.resource("s3", region_name="us-east-1")


@pytest.fixture
@mock_s3
def s3_client():
    """Create mock S3 client."""
    return boto3.client("s3", region_name="us-east-1")


@pytest.fixture
@mock_dynamodb
def dynamodb_client():
    """Create mock DynamoDB client."""
    return boto3.client("dynamodb", region_name="us-east-1")


@pytest.fixture
def sample_documents():
    """Get sample documents for testing."""
    return [
        {
            "_id": "doc1",
            "name": "Product A",
            "price": 99.99,
            "in_stock": True,
            "tags": ["electronics", "popular"],
        },
        {
            "_id": "doc2",
            "name": "Product B",
            "price": "49.99",  # Different type
            "in_stock": "yes",  # Different type
            "tags": ["office"],
        },
        {
            "_id": "doc3",
            "name": "Product C",
            "price": 150.00,
            "in_stock": 1,  # Different type
            "description": "A great product",
            "tags": ["electronics", "office", "popular"],
        },
    ]


@pytest.fixture
def sample_json_file(tmp_path):
    """Create a temporary JSON file for testing."""
    data = [
        {"id": 1, "name": "Item 1", "value": 100},
        {"id": 2, "name": "Item 2", "value": 200},
    ]
    file_path = tmp_path / "test_data.json"
    with open(file_path, "w") as f:
        json.dump(data, f)
    return str(file_path)


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a temporary CSV file for testing."""
    csv_path = tmp_path / "test_data.csv"
    csv_path.write_text("id,name,value\n1,Item 1,100\n2,Item 2,200\n")
    return str(csv_path)


@pytest.fixture
def sample_files_dir(tmp_path):
    """Create a temporary directory with sample files."""
    (tmp_path / "document.txt").write_text("Test document content")
    (tmp_path / "image.png").write_bytes(b"fake png data")
    (tmp_path / "video.mp4").write_bytes(b"fake video data")
    return str(tmp_path)


@pytest.fixture
def migration_plan():
    """Get sample migration plan."""
    return {
        "dynamodb_design": {
            "table_name": "test-table",
            "partition_key": "id",
            "sort_key": "timestamp",
            "billing_mode": "PAY_PER_REQUEST",
            "estimated_storage_gb": 50,
        },
        "s3_organization": {
            "bucket_naming": "test-bucket-prod",
            "folder_structure": "year/month/day",
        },
        "data_mapping": {
            "field_mappings": {"_id": "id", "created_at": "timestamp"}
        },
    }
