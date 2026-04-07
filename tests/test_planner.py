"""Tests for migration planner."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.agent.planner import MigrationPlanner


class TestMigrationPlanner:
    """Test migration planner."""

    @patch("src.agent.planner.anthropic.Anthropic")
    def test_generate_plan(self, mock_anthropic_class, anthropic_key):
        """Test plan generation."""
        # Mock the Anthropic API response
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [
            Mock(
                text='{"dynamodb_design": {"table_name": "test-table"}, '
                '"s3_organization": {"bucket_naming": "test-bucket"}}'
            )
        ]
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_client.messages.create.return_value = mock_response

        planner = MigrationPlanner("sk-ant-test-key")
        result = planner.generate_plan({"analysis": "test"}, 1000)

        assert result["status"] == "success"
        assert result["total_records"] == 1000
        assert "plan" in result or "raw_plan" in result

    def test_validate_plan(self):
        """Test plan validation."""
        planner = MigrationPlanner("sk-ant-test-key")

        valid_plan = {
            "dynamodb_design": {
                "table_name": "test-table",
                "partition_key": "id",
            },
            "s3_organization": {
                "bucket_naming": "test-bucket",
            },
            "data_mapping": {
                "field_mappings": {"source_id": "id"},
            },
        }

        result = planner.validate_plan(valid_plan)
        assert result["valid"] is True

    def test_validate_plan_missing_fields(self):
        """Test plan validation with missing fields."""
        planner = MigrationPlanner("sk-ant-test-key")

        invalid_plan = {
            "dynamodb_design": {},
            "s3_organization": {},
        }

        result = planner.validate_plan(invalid_plan)
        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_create_terraform_config(self):
        """Test Terraform config generation."""
        planner = MigrationPlanner("sk-ant-test-key")

        plan = {
            "dynamodb_design": {
                "table_name": "migration-table",
                "partition_key": "id",
                "sort_key": "timestamp",
                "billing_mode": "PAY_PER_REQUEST",
            },
            "s3_organization": {
                "bucket_naming": "migration-bucket-prod",
            },
        }

        terraform = planner.create_terraform_config(plan)

        assert "module" in terraform
        assert "migration-table" in terraform
        assert "migration-bucket-prod" in terraform
        assert "dynamodb" in terraform
        assert "s3" in terraform
