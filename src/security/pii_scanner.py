"""PII detection and reporting."""

import re
from typing import Dict, List, Any, Optional
from src.utils.logger import get_logger
import anthropic

logger = get_logger(__name__)


class PIIScanner:
    """Scans data for personally identifiable information."""

    # Common PII patterns
    PII_PATTERNS = {
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
        "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "passport": re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
    }

    def __init__(self, api_key: str):
        """
        Initialize PII scanner.

        Args:
            api_key: Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.pii_findings: List[Dict[str, Any]] = []

    def scan_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan a document for PII using regex patterns.

        Args:
            document: Document to scan

        Returns:
            PII findings
        """
        findings = {"document_id": str(document.get("_id", "unknown")), "pii_detected": [], "fields": []}

        for field, value in document.items():
            if not isinstance(value, str):
                continue

            for pii_type, pattern in self.PII_PATTERNS.items():
                matches = pattern.findall(value)
                if matches:
                    findings["pii_detected"].append(pii_type)
                    findings["fields"].append({"field": field, "type": pii_type, "count": len(matches)})

        return findings

    def scan_batch(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Scan a batch of documents for PII.

        Args:
            documents: List of documents to scan

        Returns:
            Aggregated PII findings
        """
        all_findings = []
        pii_field_map: Dict[str, List[str]] = {}

        for doc in documents:
            findings = self.scan_document(doc)
            if findings["pii_detected"]:
                all_findings.append(findings)
                for field_info in findings["fields"]:
                    field_name = field_info["field"]
                    if field_name not in pii_field_map:
                        pii_field_map[field_name] = []
                    pii_field_map[field_name].append(field_info["type"])

        return {
            "total_documents_scanned": len(documents),
            "documents_with_pii": len(all_findings),
            "pii_fields": pii_field_map,
            "findings": all_findings,
        }

    def analyze_with_claude(self, sample_data: str, sample_size: int = 10) -> Dict[str, Any]:
        """
        Use Claude to perform deeper PII analysis on sample data.

        Args:
            sample_data: Sample data string to analyze
            sample_size: Number of documents in sample

        Returns:
            Claude's analysis results
        """
        system_prompt = """You are a PII (Personally Identifiable Information) detection specialist.
Analyze the provided data sample and identify:
1. All types of PII present
2. Which fields contain PII
3. Severity of exposure (critical, high, medium, low)
4. Recommended actions (encrypt, redact, flag, skip)

Be thorough and precise. Return your analysis as a structured JSON response."""

        user_message = f"""Analyze this sample of {sample_size} documents for PII:

{sample_data}

Provide findings in this JSON format:
{{
  "pii_types_detected": [],
  "fields_with_pii": {{}},
  "severity": "critical|high|medium|low",
  "recommended_actions": []
}}"""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            response_text = response.content[0].text
            logger.info(f"Claude PII analysis completed for {sample_size} documents")

            return {
                "status": "success",
                "analysis": response_text,
                "model": response.model,
            }
        except Exception as e:
            logger.error(f"Claude PII analysis failed: {e}")
            return {"status": "error", "message": str(e)}

    def generate_report(self, batch_findings: Dict[str, Any], claude_analysis: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate PII scan report.

        Args:
            batch_findings: Findings from batch scan
            claude_analysis: Optional Claude analysis results

        Returns:
            Formatted report
        """
        report = [
            "PII SCAN REPORT",
            "=" * 50,
            f"Total Documents Scanned: {batch_findings['total_documents_scanned']}",
            f"Documents with PII: {batch_findings['documents_with_pii']}",
            "",
        ]

        if batch_findings["pii_fields"]:
            report.append("Fields with PII Detected:")
            for field, types in batch_findings["pii_fields"].items():
                unique_types = list(set(types))
                report.append(f"  - {field}: {', '.join(unique_types)}")
        else:
            report.append("No PII detected using regex patterns")

        if claude_analysis and claude_analysis.get("status") == "success":
            report.append("\nClaude Deep Analysis:")
            report.append(claude_analysis.get("analysis", ""))

        report.append("=" * 50)
        return "\n".join(report)
