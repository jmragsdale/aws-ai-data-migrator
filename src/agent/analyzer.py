"""Schema analysis using Claude."""

import json
from typing import Dict, List, Any, Optional
import anthropic
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SchemaAnalyzer:
    """Analyzes data schemas using Claude AI."""

    def __init__(self, api_key: str):
        """
        Initialize schema analyzer.

        Args:
            api_key: Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze_documents(self, documents: List[Dict[str, Any]], max_retries: int = 3) -> Dict[str, Any]:
        """
        Analyze documents to infer schema.

        Args:
            documents: Sample documents to analyze
            max_retries: Number of retries for API calls

        Returns:
            Analysis results with field mappings and patterns
        """
        system_prompt = """You are a data schema analysis expert. Analyze the provided sample documents and identify:
1. All fields and their data types
2. Field patterns and consistency
3. Relationships between fields
4. Implicit schemas and constraints
5. Inconsistencies or anomalies

Provide a structured JSON analysis that includes:
- field_map: Dictionary mapping field names to inferred types
- patterns: List of discovered patterns
- relationships: Fields that relate to each other
- inconsistencies: Fields with inconsistent data types across documents
- recommendations: Schema design recommendations

Be thorough and precise."""

        user_message = f"""Analyze these {len(documents)} sample documents:

{json.dumps(documents, indent=2, default=str)}

Provide analysis in JSON format with the schema described above."""

        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )

                response_text = response.content[0].text
                logger.info(f"Schema analysis completed for {len(documents)} documents")

                # Parse JSON from response
                try:
                    # Extract JSON from response
                    import re

                    json_match = re.search(r"\{[\s\S]*\}", response_text)
                    if json_match:
                        analysis = json.loads(json_match.group())
                        return {
                            "status": "success",
                            "document_count": len(documents),
                            "analysis": analysis,
                            "model": response.model,
                        }
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON response, returning raw text")
                    return {"status": "success", "document_count": len(documents), "raw_analysis": response_text}

            except anthropic.APIError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"API error on attempt {attempt + 1}, retrying: {e}")
                    continue
                logger.error(f"Schema analysis failed after {max_retries} attempts: {e}")
                return {"status": "error", "message": str(e)}

        return {"status": "error", "message": "Max retries exceeded"}

    def detect_inconsistencies(
        self, field_map: Dict[str, List[str]], documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect data type inconsistencies.

        Args:
            field_map: Mapping of field names to observed types
            documents: Sample documents

        Returns:
            Inconsistency report
        """
        inconsistencies = {}

        for field, types in field_map.items():
            unique_types = list(set(types))
            if len(unique_types) > 1:
                inconsistencies[field] = {
                    "observed_types": unique_types,
                    "type_count": len(unique_types),
                    "examples": self._get_field_values(documents, field),
                }

        return {"total_inconsistencies": len(inconsistencies), "fields": inconsistencies}

    @staticmethod
    def _get_field_values(documents: List[Dict[str, Any]], field: str, limit: int = 5) -> List[Any]:
        """Get sample values for a field."""
        values = []
        for doc in documents:
            if field in doc:
                values.append(doc[field])
                if len(values) >= limit:
                    break
        return values

    def infer_field_types(self, documents: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Infer types for each field.

        Args:
            documents: Sample documents

        Returns:
            Field name to inferred type mapping
        """
        type_map = {}

        for doc in documents:
            for field, value in doc.items():
                if field not in type_map:
                    type_map[field] = self._infer_type(value)

        return type_map

    @staticmethod
    def _infer_type(value: Any) -> str:
        """Infer Python type as string."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "unknown"
