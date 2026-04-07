"""AWS and Anthropic credential management."""

import os
from typing import Optional
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CredentialManager:
    """Manages AWS and Anthropic API credentials."""

    def __init__(self, aws_profile: Optional[str] = None, aws_region: str = "us-east-1"):
        """
        Initialize credential manager.

        Args:
            aws_profile: AWS profile name (uses default if None)
            aws_region: AWS region for services
        """
        self.aws_profile = aws_profile or "default"
        self.aws_region = aws_region
        self._validate_credentials()

    def _validate_credentials(self) -> None:
        """Validate that all required credentials are present."""
        # Check Anthropic API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        logger.info("Anthropic API key found")

        # Check AWS credentials
        try:
            session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
            credentials = session.get_credentials()
            if not credentials:
                raise NoCredentialsError()
            logger.info(f"AWS credentials validated for profile '{self.aws_profile}'")
        except (NoCredentialsError, PartialCredentialsError) as e:
            raise ValueError(f"AWS credentials not found or incomplete for profile '{self.aws_profile}': {e}")

    def get_boto3_session(self) -> boto3.Session:
        """
        Get configured boto3 session.

        Returns:
            Configured boto3 Session
        """
        return boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)

    def get_s3_client(self):
        """Get S3 client."""
        session = self.get_boto3_session()
        return session.client("s3")

    def get_dynamodb_client(self):
        """Get DynamoDB client."""
        session = self.get_boto3_session()
        return session.client("dynamodb")

    def get_dynamodb_resource(self):
        """Get DynamoDB resource."""
        session = self.get_boto3_session()
        return session.resource("dynamodb")

    def get_anthropic_api_key(self) -> str:
        """
        Get Anthropic API key.

        Returns:
            API key
        """
        return os.getenv("ANTHROPIC_API_KEY", "")

    @staticmethod
    def mask_value(value: str, show_chars: int = 4) -> str:
        """
        Mask sensitive value for logging.

        Args:
            value: Value to mask
            show_chars: Number of characters to show at end

        Returns:
            Masked value
        """
        if len(value) <= show_chars:
            return "*" * len(value)
        return "*" * (len(value) - show_chars) + value[-show_chars:]
