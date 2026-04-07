"""Conflict resolution using Claude."""

import json
from typing import Dict, List, Any
import anthropic
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConflictResolver:
    """Resolves data inconsistencies using Claude AI."""

    RESOLUTION_STRATEGIES = ["coerce", "split", "nullable", "skip", "transform"]

    def __init__(self, api_key: str):
        """
        Initialize conflict resolver.

        Args:
            api_key: Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=api_key)

    def resolve_inconsistencies(self, inconsistencies: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """
        Generate resolution strategies for data inconsistencies.

        Args:
            inconsistencies: Report from analyzer.detect_inconsistencies()
            max_retries: Number of retries for API calls

        Returns:
            Resolution plan with strategies for each inconsistent field
        """
        system_prompt = """You are a data migration specialist expert in handling schema inconsistencies.
Analyze the inconsistent fields and propose resolution strategies.

Available resolution strategies:
1. coerce: Convert all values to a single type (specify target type)
2. split: Create separate fields for different value types
3. nullable: Make the field nullable and handle null values
4. skip: Exclude this field from migration
5. transform: Apply a transformation function to normalize values

For each field, recommend:
- Best strategy given data patterns
- Implementation approach
- Potential data loss or transformation
- Validation approach

Provide pragmatic, production-ready recommendations."""

        user_message = f"""Resolve these data inconsistencies:

{json.dumps(inconsistencies, indent=2, default=str)}

For each field, provide resolution in JSON format:
{{
  "field_name": {{
    "recommended_strategy": "coerce|split|nullable|skip|transform",
    "justification": "explanation",
    "implementation": "how to implement",
    "expected_data_loss": 0-100,
    "alternative_strategies": []
  }}
}}"""

        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )

                response_text = response.content[0].text
                logger.info("Conflict resolution completed")

                # Parse JSON from response
                try:
                    import re

                    json_match = re.search(r"\{[\s\S]*\}", response_text)
                    if json_match:
                        resolution = json.loads(json_match.group())
                        return {
                            "status": "success",
                            "resolution_plan": resolution,
                            "model": response.model,
                        }
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON response")
                    return {"status": "success", "raw_resolution": response_text}

            except anthropic.APIError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"API error on attempt {attempt + 1}, retrying: {e}")
                    continue
                logger.error(f"Resolution generation failed after {max_retries} attempts: {e}")
                return {"status": "error", "message": str(e)}

        return {"status": "error", "message": "Max retries exceeded"}

    def apply_resolution(self, document: Dict[str, Any], resolution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply resolution strategy to a document.

        Args:
            document: Document to transform
            resolution_plan: Resolution strategies per field

        Returns:
            Transformed document
        """
        transformed = document.copy()

        for field, strategy_info in resolution_plan.items():
            if field not in document:
                continue

            strategy = strategy_info.get("recommended_strategy")
            value = document[field]

            if strategy == "skip":
                del transformed[field]
            elif strategy == "coerce":
                target_type = strategy_info.get("target_type", "string")
                transformed[field] = self._coerce_value(value, target_type)
            elif strategy == "nullable":
                if value is None or value == "":
                    transformed[field] = None
            elif strategy == "split":
                # Create separate field for this type variant
                type_field = f"{field}_type"
                transformed[type_field] = type(value).__name__
            # For "transform", assume transformation is specified in implementation

        return transformed

    @staticmethod
    def _coerce_value(value: Any, target_type: str) -> Any:
        """Coerce value to target type."""
        if value is None:
            return None

        if target_type == "string":
            return str(value)
        elif target_type == "integer":
            try:
                return int(float(str(value)))
            except (ValueError, TypeError):
                return None
        elif target_type == "float":
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        elif target_type == "boolean":
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "yes", "1")
        else:
            return value

    def generate_resolution_report(self, resolution_plan: Dict[str, Any]) -> str:
        """
        Generate a human-readable resolution report.

        Args:
            resolution_plan: Resolution strategies per field

        Returns:
            Formatted report
        """
        report = ["CONFLICT RESOLUTION PLAN", "=" * 50, ""]

        for field, strategy_info in resolution_plan.items():
            report.append(f"Field: {field}")
            report.append(f"  Strategy: {strategy_info.get('recommended_strategy')}")
            report.append(f"  Justification: {strategy_info.get('justification')}")
            report.append(f"  Data Loss Risk: {strategy_info.get('expected_data_loss')}%")
            report.append("")

        report.append("=" * 50)
        return "\n".join(report)
