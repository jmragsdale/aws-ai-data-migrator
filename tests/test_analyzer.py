"""Tests for schema analyzer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.agent.analyzer import SchemaAnalyzer


class TestSchemaAnalyzer:
    """Test schema analyzer."""

    @patch("src.agent.analyzer.anthropic.Anthropic")
    def test_analyze_documents(self, mock_anthropic_class, sample_documents, anthropic_key):
        """Test document analysis."""
        # Mock the Anthropic API response
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [
            Mock(text='{"field_map": {"name": "string", "price": "number"}, "patterns": []}')
        ]
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_client.messages.create.return_value = mock_response

        analyzer = SchemaAnalyzer("sk-ant-test-key")
        result = analyzer.analyze_documents(sample_documents)

        assert result["status"] == "success"
        assert "analysis" in result or "raw_analysis" in result
        assert result["document_count"] == 3

    def test_infer_field_types(self, sample_documents):
        """Test field type inference."""
        analyzer = SchemaAnalyzer("sk-ant-test-key")
        types = analyzer.infer_field_types(sample_documents)

        assert types["_id"] == "string"
        assert types["price"] in ["number", "string"]  # Mixed types
        assert types["name"] == "string"
        assert types["in_stock"] in ["boolean", "string", "integer"]  # Mixed types

    def test_detect_inconsistencies(self, sample_documents):
        """Test inconsistency detection."""
        analyzer = SchemaAnalyzer("sk-ant-test-key")

        field_map = {
            "price": [99.99, "49.99", 150.00],  # Mixed types
            "in_stock": [True, "yes", 1],  # Mixed types
        }

        result = analyzer.detect_inconsistencies(field_map, sample_documents)

        assert result["total_inconsistencies"] == 2
        assert "price" in result["fields"]
        assert "in_stock" in result["fields"]

    def test_get_field_values(self, sample_documents):
        """Test getting field values."""
        analyzer = SchemaAnalyzer("sk-ant-test-key")
        values = analyzer._get_field_values(sample_documents, "name", limit=2)

        assert len(values) <= 2
        assert "Product A" in values or "Product B" in values

    def test_infer_type(self):
        """Test type inference for individual values."""
        analyzer = SchemaAnalyzer("sk-ant-test-key")

        assert analyzer._infer_type("string") == "string"
        assert analyzer._infer_type(42) == "integer"
        assert analyzer._infer_type(3.14) == "number"
        assert analyzer._infer_type(True) == "boolean"
        assert analyzer._infer_type([1, 2, 3]) == "array"
        assert analyzer._infer_type({"key": "value"}) == "object"
        assert analyzer._infer_type(None) == "null"
