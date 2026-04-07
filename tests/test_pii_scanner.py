"""Tests for PII scanner."""

import pytest
from src.security.pii_scanner import PIIScanner


class TestPIIScanner:
    """Test PII detection."""

    def test_scan_document_email(self, anthropic_key):
        """Test email detection."""
        scanner = PIIScanner("sk-ant-test-key")

        document = {
            "_id": "doc1",
            "name": "John Doe",
            "email": "john.doe@example.com",
        }

        result = scanner.scan_document(document)

        assert "email" in result["pii_detected"]

    def test_scan_document_ssn(self, anthropic_key):
        """Test SSN detection."""
        scanner = PIIScanner("sk-ant-test-key")

        document = {
            "_id": "doc1",
            "name": "Jane Smith",
            "ssn": "123-45-6789",
        }

        result = scanner.scan_document(document)

        assert "ssn" in result["pii_detected"]

    def test_scan_document_phone(self, anthropic_key):
        """Test phone number detection."""
        scanner = PIIScanner("sk-ant-test-key")

        document = {
            "_id": "doc1",
            "name": "Bob Jones",
            "phone": "555-123-4567",
        }

        result = scanner.scan_document(document)

        assert "phone" in result["pii_detected"]

    def test_scan_document_credit_card(self, anthropic_key):
        """Test credit card detection."""
        scanner = PIIScanner("sk-ant-test-key")

        document = {
            "_id": "doc1",
            "card": "4532-1234-5678-9010",
        }

        result = scanner.scan_document(document)

        assert "credit_card" in result["pii_detected"]

    def test_scan_document_ip_address(self, anthropic_key):
        """Test IP address detection."""
        scanner = PIIScanner("sk-ant-test-key")

        document = {
            "_id": "doc1",
            "ip": "192.168.1.100",
        }

        result = scanner.scan_document(document)

        assert "ip_address" in result["pii_detected"]

    def test_scan_batch(self, sample_documents, anthropic_key):
        """Test batch scanning."""
        scanner = PIIScanner("sk-ant-test-key")

        documents = [
            {"_id": "1", "email": "user1@example.com"},
            {"_id": "2", "phone": "555-987-6543"},
            {"_id": "3", "name": "Safe Document"},
        ]

        result = scanner.scan_batch(documents)

        assert result["total_documents_scanned"] == 3
        assert result["documents_with_pii"] == 2

    def test_generate_report(self, anthropic_key):
        """Test report generation."""
        scanner = PIIScanner("sk-ant-test-key")

        batch_findings = {
            "total_documents_scanned": 10,
            "documents_with_pii": 3,
            "pii_fields": {
                "email": ["email"],
                "phone": ["phone"],
            },
            "findings": [],
        }

        report = scanner.generate_report(batch_findings)

        assert "PII SCAN REPORT" in report
        assert "email" in report
        assert "phone" in report
