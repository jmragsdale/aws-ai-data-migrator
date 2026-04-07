"""S3 migration and management."""

import os
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from src.utils.logger import get_logger
from src.utils.manifest import MigrationManifest

logger = get_logger(__name__)


class S3Migrator:
    """Handles S3 bucket creation and file migration."""

    def __init__(self, region: str = "us-east-1"):
        """
        Initialize S3 migrator.

        Args:
            region: AWS region
        """
        self.region = region
        self.client = boto3.client("s3", region_name=region)
        self.manifest = MigrationManifest()

    def create_bucket(
        self,
        bucket_name: str,
        versioning: bool = True,
        encryption: str = "AES256",
        public_access_block: bool = True,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create S3 bucket with proper configuration.

        Args:
            bucket_name: Name of bucket
            versioning: Enable versioning
            encryption: SSE-S3 or SSE-KMS
            public_access_block: Block all public access
            tags: Optional resource tags

        Returns:
            Bucket configuration details
        """
        # Create bucket
        try:
            if self.region == "us-east-1":
                self.client.create_bucket(Bucket=bucket_name)
            else:
                self.client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": self.region},
                )
            logger.info(f"Created S3 bucket: {bucket_name}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
                logger.warning(f"Bucket {bucket_name} already exists")
            else:
                logger.error(f"Failed to create bucket {bucket_name}: {e}")
                raise

        # Enable versioning
        if versioning:
            self.client.put_bucket_versioning(
                Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
            )
            logger.info(f"Enabled versioning for {bucket_name}")

        # Enable encryption
        encryption_config = {"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": encryption}}]}
        self.client.put_bucket_encryption(
            Bucket=bucket_name, ServerSideEncryptionConfiguration=encryption_config
        )
        logger.info(f"Enabled {encryption} encryption for {bucket_name}")

        # Block public access
        if public_access_block:
            self.client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                },
            )
            logger.info(f"Blocked public access for {bucket_name}")

        # Add tags
        if tags:
            tag_set = [{"Key": k, "Value": v} for k, v in tags.items()]
            self.client.put_bucket_tagging(Bucket=bucket_name, Tagging={"TagSet": tag_set})
            logger.info(f"Added tags to {bucket_name}")

        return {
            "bucket_name": bucket_name,
            "region": self.region,
            "versioning": versioning,
            "encryption": encryption,
            "public_access_blocked": public_access_block,
        }

    def upload_file(
        self,
        bucket: str,
        file_path: str,
        s3_key: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload file to S3 with metadata and tags.

        Args:
            bucket: Target bucket
            file_path: Local file path
            s3_key: S3 object key (defaults to file name)
            metadata: Object metadata
            tags: Object tags

        Returns:
            S3 object key
        """
        if not s3_key:
            s3_key = Path(file_path).name

        file_size = os.path.getsize(file_path)

        try:
            # Use multipart upload for large files
            if file_size > 100 * 1024 * 1024:  # 100MB
                self._multipart_upload(bucket, file_path, s3_key, metadata)
            else:
                extra_args = {}
                if metadata:
                    extra_args["Metadata"] = metadata

                self.client.upload_file(file_path, bucket, s3_key, ExtraArgs=extra_args)

            logger.info(f"Uploaded {s3_key} to {bucket} ({file_size} bytes)")

            # Add tags if provided
            if tags:
                self._tag_object(bucket, s3_key, tags)

            self.manifest.add_resource(
                "s3_object",
                s3_key,
                f"s3://{bucket}/{s3_key}",
                {"size_bytes": file_size, "metadata": metadata},
            )

            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload {file_path}: {e}")
            raise

    def _multipart_upload(
        self, bucket: str, file_path: str, s3_key: str, metadata: Optional[Dict[str, str]] = None
    ) -> None:
        """Upload large file using multipart upload."""
        chunk_size = 50 * 1024 * 1024  # 50MB chunks
        file_size = os.path.getsize(file_path)

        # Initiate multipart upload
        response = self.client.create_multipart_upload(
            Bucket=bucket, Key=s3_key, Metadata=metadata or {}
        )
        upload_id = response["UploadId"]

        try:
            parts = []
            with open(file_path, "rb") as f:
                part_number = 1
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break

                    part_response = self.client.upload_part(
                        Bucket=bucket,
                        Key=s3_key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=chunk,
                    )
                    parts.append({"PartNumber": part_number, "ETag": part_response["ETag"]})
                    part_number += 1

            # Complete upload
            self.client.complete_multipart_upload(
                Bucket=bucket, Key=s3_key, UploadId=upload_id, MultipartUpload={"Parts": parts}
            )
        except Exception as e:
            self.client.abort_multipart_upload(Bucket=bucket, Key=s3_key, UploadId=upload_id)
            raise

    def _tag_object(self, bucket: str, key: str, tags: Dict[str, str]) -> None:
        """Apply tags to S3 object."""
        tag_set = [{"Key": k, "Value": v} for k, v in tags.items()]
        self.client.put_object_tagging(Bucket=bucket, Key=key, Tagging={"TagSet": tag_set})

    def upload_batch(
        self,
        bucket: str,
        file_paths: List[str],
        prefix: str = "",
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Upload batch of files.

        Args:
            bucket: Target bucket
            file_paths: List of file paths
            prefix: S3 key prefix
            metadata: Common metadata for all files
            tags: Common tags for all files

        Returns:
            Upload statistics
        """
        successful = 0
        failed = 0

        for file_path in file_paths:
            try:
                s3_key = f"{prefix}/{Path(file_path).name}".lstrip("/")
                self.upload_file(bucket, file_path, s3_key, metadata, tags)
                successful += 1
            except Exception as e:
                logger.error(f"Failed to upload {file_path}: {e}")
                failed += 1

        return {
            "bucket": bucket,
            "total_files": len(file_paths),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(file_paths) * 100) if file_paths else 0,
        }

    def delete_bucket(self, bucket: str, force: bool = False) -> None:
        """
        Delete S3 bucket.

        Args:
            bucket: Bucket name
            force: Delete all objects first
        """
        try:
            if force:
                # Delete all objects
                paginator = self.client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket):
                    if "Contents" in page:
                        objects = [{"Key": obj["Key"]} for obj in page["Contents"]]
                        self.client.delete_objects(Bucket=bucket, Delete={"Objects": objects})
                logger.info(f"Deleted all objects from {bucket}")

            self.client.delete_bucket(Bucket=bucket)
            logger.info(f"Deleted bucket {bucket}")
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchBucket":
                logger.error(f"Failed to delete bucket {bucket}: {e}")
                raise

    def get_bucket_stats(self, bucket: str) -> Dict[str, Any]:
        """
        Get bucket statistics.

        Args:
            bucket: Bucket name

        Returns:
            Statistics dictionary
        """
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            total_size = 0
            object_count = 0

            for page in paginator.paginate(Bucket=bucket):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        total_size += obj["Size"]
                        object_count += 1

            return {
                "bucket": bucket,
                "object_count": object_count,
                "total_size_bytes": total_size,
                "avg_object_size_bytes": total_size / object_count if object_count > 0 else 0,
            }
        except ClientError as e:
            logger.error(f"Failed to get bucket stats for {bucket}: {e}")
            raise
