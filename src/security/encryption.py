"""Encryption configuration and validation."""

from typing import Dict, Any, Optional
from enum import Enum
import boto3
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EncryptionType(Enum):
    """Encryption algorithm options."""

    SSE_S3 = "AES256"
    SSE_KMS = "aws:kms"


class EncryptionConfig:
    """Manages encryption configuration for AWS resources."""

    def __init__(self, kms_key_id: Optional[str] = None, encryption_type: EncryptionType = EncryptionType.SSE_S3):
        """
        Initialize encryption configuration.

        Args:
            kms_key_id: Optional KMS key ID for SSE-KMS
            encryption_type: Encryption algorithm to use
        """
        self.kms_key_id = kms_key_id
        self.encryption_type = encryption_type
        self.s3_client = boto3.client("s3")
        self.kms_client = boto3.client("kms")
        self.dynamodb_client = boto3.client("dynamodb")

    def get_s3_encryption_config(self) -> Dict[str, Any]:
        """
        Get S3 encryption configuration.

        Returns:
            S3 encryption configuration dict
        """
        if self.encryption_type == EncryptionType.SSE_KMS and self.kms_key_id:
            return {
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "aws:kms",
                            "KMSMasterKeyID": self.kms_key_id,
                        },
                        "BucketKeyEnabled": True,
                    }
                ]
            }
        else:
            return {
                "Rules": [
                    {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            }

    def get_dynamodb_encryption_config(self) -> Dict[str, Any]:
        """
        Get DynamoDB encryption configuration.

        Returns:
            DynamoDB encryption configuration dict
        """
        config = {"Enabled": True}
        if self.encryption_type == EncryptionType.SSE_KMS and self.kms_key_id:
            config["KMSMasterKeyArn"] = f"arn:aws:kms:us-east-1:123456789012:key/{self.kms_key_id}"
        return config

    def validate_s3_bucket_encryption(self, bucket: str) -> bool:
        """
        Validate that S3 bucket has encryption enabled.

        Args:
            bucket: Bucket name

        Returns:
            True if encryption is properly configured
        """
        try:
            response = self.s3_client.get_bucket_encryption(Bucket=bucket)
            if "ServerSideEncryptionConfiguration" in response:
                logger.info(f"S3 bucket '{bucket}' has encryption enabled")
                return True
        except self.s3_client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
            logger.warning(f"S3 bucket '{bucket}' does not have encryption configured")
            return False
        except Exception as e:
            logger.error(f"Failed to validate S3 encryption for '{bucket}': {e}")
            return False

    def validate_dynamodb_encryption(self, table_name: str) -> bool:
        """
        Validate that DynamoDB table has encryption enabled.

        Args:
            table_name: DynamoDB table name

        Returns:
            True if encryption is properly configured
        """
        try:
            response = self.dynamodb_client.describe_table(TableName=table_name)
            sse_config = response.get("Table", {}).get("SSEDescription", {})
            if sse_config.get("Status") == "ENABLED":
                logger.info(f"DynamoDB table '{table_name}' has encryption enabled")
                return True
            else:
                logger.warning(f"DynamoDB table '{table_name}' does not have encryption enabled")
                return False
        except Exception as e:
            logger.error(f"Failed to validate DynamoDB encryption for '{table_name}': {e}")
            return False

    def generate_terraform_s3_encryption(self) -> str:
        """
        Generate Terraform configuration for S3 encryption.

        Returns:
            Terraform HCL code
        """
        if self.encryption_type == EncryptionType.SSE_KMS:
            return f"""
  server_side_encryption_configuration {{
    rule {{
      apply_server_side_encryption_by_default {{
        sse_algorithm      = "aws:kms"
        kms_master_key_id  = "{self.kms_key_id}"
      }}
      bucket_key_enabled = true
    }}
  }}
"""
        else:
            return """
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
"""

    def generate_terraform_dynamodb_encryption(self) -> str:
        """
        Generate Terraform configuration for DynamoDB encryption.

        Returns:
            Terraform HCL code
        """
        if self.encryption_type == EncryptionType.SSE_KMS:
            return f"""
  server_side_encryption {{
    enabled     = true
    kms_key_arn = "arn:aws:kms:region:account:key/{self.kms_key_id}"
  }}
"""
        else:
            return """
  server_side_encryption {
    enabled = true
  }
"""
