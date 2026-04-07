"""Migration manifest tracking."""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class MigrationManifest:
    """Tracks all resources created during migration for rollback capability."""

    def __init__(self, manifest_dir: str = "manifests"):
        """
        Initialize migration manifest.

        Args:
            manifest_dir: Directory to store manifest files
        """
        self.manifest_dir = Path(manifest_dir)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.resources: List[Dict[str, Any]] = []
        self.migration_start: str = datetime.utcnow().isoformat()

    def add_resource(
        self,
        resource_type: str,
        resource_id: str,
        arn: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a created resource.

        Args:
            resource_type: Type of resource (s3_object, dynamodb_table, etc.)
            resource_id: Identifier for the resource
            arn: AWS ARN or key
            metadata: Additional resource metadata
        """
        entry = {
            "type": resource_type,
            "id": resource_id,
            "arn": arn,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        self.resources.append(entry)

    def save(self, migration_name: str) -> Path:
        """
        Save manifest to file.

        Args:
            migration_name: Name of the migration

        Returns:
            Path to saved manifest file
        """
        manifest_data = {
            "migration_name": migration_name,
            "migration_start": self.migration_start,
            "migration_end": datetime.utcnow().isoformat(),
            "resource_count": len(self.resources),
            "resources": self.resources,
        }

        manifest_path = self.manifest_dir / f"{migration_name}-manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)

        return manifest_path

    @staticmethod
    def load(manifest_path: str) -> Dict[str, Any]:
        """
        Load manifest from file.

        Args:
            manifest_path: Path to manifest file

        Returns:
            Parsed manifest data
        """
        with open(manifest_path, "r") as f:
            return json.load(f)

    @staticmethod
    def list_manifests(manifest_dir: str = "manifests") -> List[Path]:
        """
        List all available manifests.

        Args:
            manifest_dir: Directory containing manifest files

        Returns:
            List of manifest file paths
        """
        return sorted(Path(manifest_dir).glob("*-manifest.json"))
