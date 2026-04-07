"""Resource tagging utilities."""

from datetime import datetime
from typing import Dict, Any, Optional
import boto3


class ResourceTagger:
    """Manages standard AWS resource tagging."""

    def __init__(self, migration_name: str, custom_tags: Optional[Dict[str, str]] = None):
        """
        Initialize resource tagger.

        Args:
            migration_name: Name of the migration for tracking
            custom_tags: Optional custom tags to merge with defaults
        """
        self.migration_name = migration_name
        self.custom_tags = custom_tags or {}
        self.s3_client = boto3.client("s3")
        self.dynamodb_client = boto3.client("dynamodb")

    def get_standard_tags(self) -> Dict[str, str]:
        """
        Generate standard tag set for resources.

        Returns:
            Dictionary of standard tags
        """
        now = datetime.utcnow().isoformat()
        tags = {
            "migration-source": "aws-ai-data-migrator",
            "migration-date": now,
            "migration-name": self.migration_name,
            "migrated-by": "ai-automation",
            "data-classification": "internal",
            "cost-center": "data-ops",
        }
        tags.update(self.custom_tags)
        return tags

    def tag_s3_objects(self, bucket: str, prefix: str, tags: Optional[Dict[str, str]] = None) -> int:
        """
        Apply tags to S3 objects.

        Args:
            bucket: S3 bucket name
            prefix: Object key prefix to tag
            tags: Custom tags to apply (merged with standard tags)

        Returns:
            Number of objects tagged
        """
        all_tags = self.get_standard_tags()
        if tags:
            all_tags.update(tags)

        # Convert to S3 tag format
        tag_set = [{"Key": k, "Value": v} for k, v in all_tags.items()]

        count = 0
        paginator = self.s3_client.get_paginator("list_objects_v2")
        try:
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    self.s3_client.put_object_tagging(
                        Bucket=bucket, Key=obj["Key"], Tagging={"TagSet": tag_set}
                    )
                    count += 1
        except Exception as e:
            raise RuntimeError(f"Failed to tag S3 objects in {bucket}: {e}")

        return count

    def tag_dynamodb_table(self, table_arn: str, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Apply tags to DynamoDB table.

        Args:
            table_arn: ARN of the DynamoDB table
            tags: Custom tags to apply (merged with standard tags)
        """
        all_tags = self.get_standard_tags()
        if tags:
            all_tags.update(tags)

        try:
            self.dynamodb_client.tag_resource(
                ResourceArn=table_arn, Tags=[{"Key": k, "Value": v} for k, v in all_tags.items()]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to tag DynamoDB table {table_arn}: {e}")
