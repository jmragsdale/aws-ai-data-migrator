"""DynamoDB migration and management."""

import time
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
from src.utils.logger import get_logger
from src.utils.manifest import MigrationManifest

logger = get_logger(__name__)


class DynamoDBMigrator:
    """Handles DynamoDB table creation and data migration."""

    def __init__(self, region: str = "us-east-1"):
        """
        Initialize DynamoDB migrator.

        Args:
            region: AWS region
        """
        self.region = region
        self.client = boto3.client("dynamodb", region_name=region)
        self.resource = boto3.resource("dynamodb", region_name=region)
        self.manifest = MigrationManifest()

    def create_table(
        self,
        table_name: str,
        partition_key: str,
        sort_key: Optional[str] = None,
        gsis: Optional[List[Dict[str, Any]]] = None,
        billing_mode: str = "PAY_PER_REQUEST",
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create DynamoDB table.

        Args:
            table_name: Name of table
            partition_key: Partition key attribute name
            sort_key: Optional sort key attribute name
            gsis: Optional list of Global Secondary Index definitions
            billing_mode: PROVISIONED or PAY_PER_REQUEST
            tags: Optional resource tags

        Returns:
            Table description
        """
        key_schema = [{"AttributeName": partition_key, "KeyType": "HASH"}]
        attr_definitions = [{"AttributeName": partition_key, "AttributeType": "S"}]

        if sort_key:
            key_schema.append({"AttributeName": sort_key, "KeyType": "RANGE"})
            attr_definitions.append({"AttributeName": sort_key, "AttributeType": "S"})

        params = {
            "TableName": table_name,
            "KeySchema": key_schema,
            "AttributeDefinitions": attr_definitions,
            "BillingMode": billing_mode,
        }

        # Add GSIs if provided
        if gsis:
            params["GlobalSecondaryIndexes"] = gsis

        # Add tags if provided
        if tags:
            params["Tags"] = [{"Key": k, "Value": v} for k, v in tags.items()]

        try:
            response = self.client.create_table(**params)
            table_arn = response["TableDescription"]["TableArn"]
            self.manifest.add_resource("dynamodb_table", table_name, table_arn, {"billing_mode": billing_mode})
            logger.info(f"Created DynamoDB table: {table_name}")
            return response["TableDescription"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                logger.warning(f"Table {table_name} already exists")
                return self.client.describe_table(TableName=table_name)["Table"]
            else:
                logger.error(f"Failed to create table {table_name}: {e}")
                raise

    def batch_write_items(
        self,
        table_name: str,
        items: List[Dict[str, Any]],
        batch_size: int = 25,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Batch write items to table with retry logic.

        Args:
            table_name: Target table name
            items: List of items to write
            batch_size: Items per batch (max 25 for DynamoDB)
            max_retries: Maximum retries per batch

        Returns:
            Write statistics
        """
        table = self.resource.Table(table_name)
        batch_size = min(batch_size, 25)  # DynamoDB limit
        total_written = 0
        failed_items = []

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            retries = 0

            while retries < max_retries:
                try:
                    with table.batch_writer(
                        batch_size=len(batch), overwrite_by_pkeys=["id"]
                    ) as writer:
                        for item in batch:
                            writer.put_item(Item=item)

                    total_written += len(batch)
                    self.manifest.add_resource(
                        "dynamodb_batch", f"{table_name}-batch-{i}", f"arn:aws:dynamodb:{self.region}:batch",
                        {"item_count": len(batch)}
                    )
                    break
                except ClientError as e:
                    retries += 1
                    if retries >= max_retries:
                        failed_items.extend(batch)
                        logger.error(f"Failed to write batch after {max_retries} retries: {e}")
                    else:
                        # Exponential backoff
                        wait_time = 2 ** retries
                        logger.warning(f"Write failed, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)

        return {
            "table_name": table_name,
            "total_items": len(items),
            "written_items": total_written,
            "failed_items": len(failed_items),
            "success_rate": (total_written / len(items) * 100) if items else 0,
        }

    def wait_for_table(self, table_name: str, timeout: int = 300) -> None:
        """
        Wait for table to be active.

        Args:
            table_name: Table name
            timeout: Maximum seconds to wait
        """
        waiter = self.client.get_waiter("table_exists")
        try:
            waiter.wait(TableName=table_name, WaiterConfig={"MaxAttempts": timeout // 5})
            logger.info(f"Table {table_name} is active")
        except Exception as e:
            logger.error(f"Timeout waiting for table {table_name}: {e}")
            raise

    def enable_point_in_time_recovery(self, table_name: str) -> None:
        """
        Enable point-in-time recovery for table.

        Args:
            table_name: Table name
        """
        try:
            self.client.update_continuous_backups(
                TableName=table_name, PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True}
            )
            logger.info(f"Enabled PITR for {table_name}")
        except ClientError as e:
            logger.warning(f"Failed to enable PITR for {table_name}: {e}")

    def delete_table(self, table_name: str) -> None:
        """
        Delete DynamoDB table.

        Args:
            table_name: Table name
        """
        try:
            self.client.delete_table(TableName=table_name)
            logger.info(f"Initiated deletion of table {table_name}")
            # Wait for deletion
            waiter = self.client.get_waiter("table_not_exists")
            waiter.wait(TableName=table_name)
            logger.info(f"Table {table_name} deleted")
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                logger.error(f"Failed to delete table {table_name}: {e}")
                raise

    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """
        Get table statistics.

        Args:
            table_name: Table name

        Returns:
            Table statistics
        """
        try:
            response = self.client.describe_table(TableName=table_name)
            table = response["Table"]
            return {
                "table_name": table_name,
                "item_count": table.get("ItemCount", 0),
                "size_bytes": table.get("TableSizeBytes", 0),
                "status": table.get("TableStatus"),
                "created_at": str(table.get("CreationDateTime")),
                "arn": table.get("TableArn"),
            }
        except ClientError as e:
            logger.error(f"Failed to get table stats for {table_name}: {e}")
            raise
