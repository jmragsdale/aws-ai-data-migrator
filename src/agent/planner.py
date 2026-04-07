"""Migration planning using Claude."""

import json
from typing import Dict, List, Any, Optional
import anthropic
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MigrationPlanner:
    """Plans data migrations using Claude AI."""

    def __init__(self, api_key: str):
        """
        Initialize migration planner.

        Args:
            api_key: Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_plan(
        self, schema_analysis: Dict[str, Any], total_records: int, max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate comprehensive migration plan.

        Args:
            schema_analysis: Output from SchemaAnalyzer
            total_records: Total number of records to migrate
            max_retries: Number of retries for API calls

        Returns:
            Migration plan with table and bucket design
        """
        system_prompt = """You are a database migration architect specializing in AWS migrations.
Design a comprehensive migration plan including:

1. DynamoDB table design:
   - Table name and description
   - Partition key and sort key selection with justification
   - Global Secondary Indexes (GSIs) for access patterns
   - Estimated item size and storage
   - Read/write capacity or pay-per-request

2. S3 bucket organization:
   - Bucket naming and structure
   - Folder organization strategy
   - Partitioning strategy by time, source, or type
   - Lifecycle rules for cost optimization
   - Versioning and backup strategy

3. Data mapping:
   - How source fields map to DynamoDB attributes
   - Large text or binary data should go to S3
   - Reference resolution strategy

4. Performance considerations:
   - Sorting strategies
   - Filtering patterns
   - Batch processing recommendations

5. Cost optimization:
   - Storage class recommendations
   - DynamoDB billing mode selection
   - Potential cost savings

Provide detailed, production-ready recommendations."""

        user_message = f"""Design a migration plan for:

Total Records: {total_records}

Schema Analysis:
{json.dumps(schema_analysis, indent=2, default=str)}

Provide a comprehensive migration plan in JSON format with sections for:
- dynamodb_design (table_name, partition_key, sort_key, gsis, billing_mode, estimated_storage_gb)
- s3_organization (bucket_naming, folder_structure, lifecycle_rules)
- data_mapping (field_mappings, large_data_fields)
- performance_considerations (key_patterns, recommendations)
- cost_estimation (estimated_monthly_cost, storage_class)"""

        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )

                response_text = response.content[0].text
                logger.info("Migration plan generated successfully")

                # Parse JSON from response
                try:
                    import re

                    json_match = re.search(r"\{[\s\S]*\}", response_text)
                    if json_match:
                        plan = json.loads(json_match.group())
                        return {
                            "status": "success",
                            "plan": plan,
                            "model": response.model,
                            "total_records": total_records,
                        }
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON response")
                    return {"status": "success", "raw_plan": response_text, "total_records": total_records}

            except anthropic.APIError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"API error on attempt {attempt + 1}, retrying: {e}")
                    continue
                logger.error(f"Plan generation failed after {max_retries} attempts: {e}")
                return {"status": "error", "message": str(e)}

        return {"status": "error", "message": "Max retries exceeded"}

    def validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a migration plan.

        Args:
            plan: Migration plan to validate

        Returns:
            Validation results
        """
        issues = []

        # Check DynamoDB design
        dynamodb = plan.get("dynamodb_design", {})
        if not dynamodb.get("partition_key"):
            issues.append("DynamoDB partition key not specified")
        if not dynamodb.get("table_name"):
            issues.append("DynamoDB table name not specified")

        # Check S3 design
        s3 = plan.get("s3_organization", {})
        if not s3.get("bucket_naming"):
            issues.append("S3 bucket naming strategy not specified")

        # Check data mapping
        mapping = plan.get("data_mapping", {})
        if not mapping.get("field_mappings"):
            issues.append("Field mappings not specified")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": [],
        }

    def create_terraform_config(self, plan: Dict[str, Any]) -> str:
        """
        Generate Terraform configuration from plan.

        Args:
            plan: Migration plan

        Returns:
            Terraform HCL code
        """
        dynamodb = plan.get("dynamodb_design", {})
        s3 = plan.get("s3_organization", {})

        terraform = f"""# Auto-generated from migration plan

module "dynamodb" {{
  source = "./modules/dynamodb"

  table_name = "{dynamodb.get('table_name', 'migration-table')}"
  partition_key = "{dynamodb.get('partition_key', 'id')}"
  sort_key = "{dynamodb.get('sort_key', 'timestamp')}"

  billing_mode = "{dynamodb.get('billing_mode', 'PAY_PER_REQUEST')}"

  tags = {{
    migration = "true"
    source = "migration-planner"
  }}
}}

module "s3" {{
  source = "./modules/s3"

  bucket_name = "{s3.get('bucket_naming', 'migration-bucket')}"

  versioning = true
  encryption = "AES256"

  lifecycle_rules = [
    {{
      days = 90
      storage_class = "GLACIER"
    }}
  ]

  tags = {{
    migration = "true"
    source = "migration-planner"
  }}
}}
"""
        return terraform
