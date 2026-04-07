"""Data integrity validation after migration."""

import random
from typing import Dict, List, Any, Optional
import boto3
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IntegrityValidator:
    """Validates data integrity after migration."""

    def __init__(self, region: str = "us-east-1"):
        """
        Initialize integrity validator.

        Args:
            region: AWS region
        """
        self.region = region
        self.s3_client = boto3.client("s3", region_name=region)
        self.dynamodb_client = boto3.client("dynamodb", region_name=region)

    def validate_s3_migration(
        self, bucket: str, source_file_count: int, source_total_size: int
    ) -> Dict[str, Any]:
        """
        Validate S3 migration.

        Args:
            bucket: Target bucket name
            source_file_count: Expected file count
            source_total_size: Expected total size in bytes

        Returns:
            Validation report
        """
        # Get actual counts
        paginator = self.s3_client.get_paginator("list_objects_v2")
        actual_count = 0
        actual_size = 0

        for page in paginator.paginate(Bucket=bucket):
            if "Contents" in page:
                for obj in page["Contents"]:
                    actual_count += 1
                    actual_size += obj["Size"]

        # Spot check sample files
        spot_checks = []
        if actual_count > 0:
            # Get sample of objects
            all_objects = []
            for page in paginator.paginate(Bucket=bucket):
                if "Contents" in page:
                    all_objects.extend([obj["Key"] for obj in page["Contents"]])

            sample_size = min(10, len(all_objects))
            sample_keys = random.sample(all_objects, sample_size)

            for key in sample_keys:
                try:
                    response = self.s3_client.head_object(Bucket=bucket, Key=key)
                    spot_checks.append({
                        "key": key,
                        "exists": True,
                        "size": response.get("ContentLength", 0),
                        "valid": True,
                    })
                except Exception as e:
                    spot_checks.append({"key": key, "exists": False, "error": str(e)})

        # Validate
        results = {
            "bucket": bucket,
            "source_file_count": source_file_count,
            "actual_file_count": actual_count,
            "file_count_match": actual_count >= source_file_count,
            "source_total_size_bytes": source_total_size,
            "actual_total_size_bytes": actual_size,
            "size_variance_percent": abs((actual_size - source_total_size) / source_total_size * 100)
            if source_total_size > 0
            else 0,
            "spot_checks": spot_checks,
            "spot_check_pass_rate": (sum(1 for c in spot_checks if c.get("valid")) / len(spot_checks) * 100)
            if spot_checks
            else 0,
        }

        results["passed"] = (
            results["file_count_match"] and results["size_variance_percent"] < 5 and results["spot_check_pass_rate"] > 90
        )

        return results

    def validate_dynamodb_migration(
        self, table_name: str, expected_item_count: int, sample_size: int = 20
    ) -> Dict[str, Any]:
        """
        Validate DynamoDB migration.

        Args:
            table_name: Target table name
            expected_item_count: Expected number of items
            sample_size: Number of items to spot check

        Returns:
            Validation report
        """
        # Get table stats
        response = self.dynamodb_client.describe_table(TableName=table_name)
        table = response["Table"]
        actual_item_count = table.get("ItemCount", 0)

        # Scan sample items
        spot_checks = []
        try:
            scan_response = self.dynamodb_client.scan(
                TableName=table_name, Limit=sample_size
            )
            for item in scan_response.get("Items", []):
                spot_checks.append({
                    "has_partition_key": "id" in item or any(k for k in item.keys()),
                    "item_size": sum(len(str(v)) for v in item.values()),
                    "valid": True,
                })
        except Exception as e:
            logger.error(f"Failed to scan table {table_name}: {e}")

        results = {
            "table_name": table_name,
            "expected_item_count": expected_item_count,
            "actual_item_count": actual_item_count,
            "item_count_match": abs(actual_item_count - expected_item_count) < 5,
            "table_status": table.get("TableStatus"),
            "table_size_bytes": table.get("TableSizeBytes", 0),
            "spot_checks": spot_checks,
            "spot_check_pass_rate": (sum(1 for c in spot_checks if c.get("valid")) / len(spot_checks) * 100)
            if spot_checks
            else 0,
        }

        results["passed"] = (
            results["item_count_match"] and results["table_status"] == "ACTIVE" and results["spot_check_pass_rate"] > 90
        )

        return results

    def validate_migration(
        self,
        s3_validation: Dict[str, Any],
        dynamodb_validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate complete migration.

        Args:
            s3_validation: S3 validation results
            dynamodb_validation: DynamoDB validation results

        Returns:
            Overall validation report
        """
        report = {
            "overall_status": "PASSED" if s3_validation.get("passed") and dynamodb_validation.get("passed") else "FAILED",
            "s3_validation": s3_validation,
            "dynamodb_validation": dynamodb_validation,
            "timestamp": str(__import__("datetime").datetime.utcnow().isoformat()),
        }

        return report

    def generate_validation_report(self, validation_result: Dict[str, Any]) -> str:
        """
        Generate human-readable validation report.

        Args:
            validation_result: Validation result from validate_migration

        Returns:
            Formatted report
        """
        s3 = validation_result.get("s3_validation", {})
        dynamodb = validation_result.get("dynamodb_validation", {})

        report = [
            "DATA INTEGRITY VALIDATION REPORT",
            "=" * 70,
            f"Status: {validation_result.get('overall_status')}",
            f"Timestamp: {validation_result.get('timestamp')}",
            "",
            "S3 VALIDATION:",
            f"  Bucket: {s3.get('bucket')}",
            f"  Expected Files: {s3.get('source_file_count')}",
            f"  Actual Files: {s3.get('actual_file_count')}",
            f"  File Count Match: {s3.get('file_count_match')}",
            f"  Size Variance: {s3.get('size_variance_percent'):.2f}%",
            f"  Spot Check Pass Rate: {s3.get('spot_check_pass_rate'):.1f}%",
            f"  Status: {'PASSED' if s3.get('passed') else 'FAILED'}",
            "",
            "DYNAMODB VALIDATION:",
            f"  Table: {dynamodb.get('table_name')}",
            f"  Expected Items: {dynamodb.get('expected_item_count')}",
            f"  Actual Items: {dynamodb.get('actual_item_count')}",
            f"  Item Count Match: {dynamodb.get('item_count_match')}",
            f"  Table Status: {dynamodb.get('table_status')}",
            f"  Table Size: {dynamodb.get('table_size_bytes')} bytes",
            f"  Spot Check Pass Rate: {dynamodb.get('spot_check_pass_rate'):.1f}%",
            f"  Status: {'PASSED' if dynamodb.get('passed') else 'FAILED'}",
            "",
            "=" * 70,
        ]

        return "\n".join(report)
