"""Configuration management for AWS AI Data Migrator."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv


class Config:
    """Configuration singleton for the application."""

    _instance: Optional["Config"] = None

    def __new__(cls) -> "Config":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize configuration from .env file."""
        if self._initialized:
            return

        # Load from .env file
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        # Required fields
        self.anthropic_api_key: str = self._get_required("ANTHROPIC_API_KEY")
        self.aws_region: str = self._get_optional("AWS_REGION", "us-east-1")
        self.aws_profile: str = self._get_optional("AWS_PROFILE", "default")

        # Optional data sources
        self.source_mongodb_uri: Optional[str] = self._get_optional("SOURCE_MONGODB_URI")
        self.source_filesystem_path: Optional[str] = self._get_optional("SOURCE_FILESYSTEM_PATH")

        # Logging
        self.log_level: str = self._get_optional("LOG_LEVEL", "INFO")

        # Migration settings
        self.migration_name: str = self._get_optional("MIGRATION_NAME", "default-migration")
        self.dry_run: bool = self._get_optional("DRY_RUN", "false").lower() == "true"

        self._initialized = True

    @staticmethod
    def _get_required(key: str) -> str:
        """Get required environment variable."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable '{key}' not set")
        return value

    @staticmethod
    def _get_optional(key: str, default: str = "") -> str:
        """Get optional environment variable with default."""
        return os.getenv(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (safe version without sensitive data)."""
        return {
            "aws_region": self.aws_region,
            "aws_profile": self.aws_profile,
            "log_level": self.log_level,
            "migration_name": self.migration_name,
            "dry_run": self.dry_run,
            "source_mongodb_uri": self._mask_uri(self.source_mongodb_uri),
            "source_filesystem_path": self.source_filesystem_path,
        }

    @staticmethod
    def _mask_uri(uri: Optional[str]) -> Optional[str]:
        """Mask sensitive data in URI."""
        if not uri:
            return None
        if "://" in uri:
            scheme, rest = uri.split("://", 1)
            if "@" in rest:
                auth, host = rest.rsplit("@", 1)
                return f"{scheme}://***:***@{host}"
        return uri
