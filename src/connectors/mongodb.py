"""MongoDB data connector."""

from typing import List, Dict, Any, Optional, Iterator
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MongoDBConnector:
    """Connector for MongoDB databases."""

    def __init__(self, uri: str = "mongodb://localhost:27017"):
        """
        Initialize MongoDB connector.

        Args:
            uri: MongoDB connection URI
        """
        self.uri = uri
        self.client: Optional[MongoClient] = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # Verify connection
            self.client.admin.command("ping")
            logger.info(f"Connected to MongoDB: {self._mask_uri()}")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _mask_uri(self) -> str:
        """Mask credentials in URI for logging."""
        if "://" in self.uri:
            scheme, rest = self.uri.split("://", 1)
            if "@" in rest:
                auth, host = rest.rsplit("@", 1)
                return f"{scheme}://***@{host}"
        return self.uri

    def list_databases(self) -> List[str]:
        """
        List all databases.

        Returns:
            List of database names
        """
        if not self.client:
            raise RuntimeError("Not connected to MongoDB")
        return self.client.list_database_names()

    def list_collections(self, database: str) -> List[str]:
        """
        List collections in a database.

        Args:
            database: Database name

        Returns:
            List of collection names
        """
        if not self.client:
            raise RuntimeError("Not connected to MongoDB")
        db = self.client[database]
        return db.list_collection_names()

    def sample_documents(self, database: str, collection: str, sample_size: int = 10) -> List[Dict[str, Any]]:
        """
        Sample documents from a collection.

        Args:
            database: Database name
            collection: Collection name
            sample_size: Number of documents to sample

        Returns:
            List of sampled documents
        """
        if not self.client:
            raise RuntimeError("Not connected to MongoDB")

        db = self.client[database]
        coll = db[collection]

        # Use aggregation pipeline for sampling
        pipeline = [{"$sample": {"size": min(sample_size, coll.count_documents({}))}}]
        documents = list(coll.aggregate(pipeline))

        logger.info(f"Sampled {len(documents)} documents from {database}.{collection}")
        return documents

    def stream_documents(
        self, database: str, collection: str, batch_size: int = 1000
    ) -> Iterator[List[Dict[str, Any]]]:
        """
        Stream all documents from a collection in batches.

        Args:
            database: Database name
            collection: Collection name
            batch_size: Documents per batch

        Yields:
            Batches of documents
        """
        if not self.client:
            raise RuntimeError("Not connected to MongoDB")

        db = self.client[database]
        coll = db[collection]

        batch = []
        for doc in coll.find():
            batch.append(doc)
            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    def get_collection_stats(self, database: str, collection: str) -> Dict[str, Any]:
        """
        Get collection statistics.

        Args:
            database: Database name
            collection: Collection name

        Returns:
            Statistics dictionary
        """
        if not self.client:
            raise RuntimeError("Not connected to MongoDB")

        db = self.client[database]
        coll = db[collection]

        count = coll.count_documents({})
        if count == 0:
            avg_size = 0
        else:
            # Estimate average document size
            sample = list(coll.find().limit(1))
            import json

            avg_size = len(json.dumps(sample[0])) if sample else 0

        return {
            "database": database,
            "collection": collection,
            "document_count": count,
            "avg_document_size_bytes": avg_size,
            "estimated_total_size_bytes": count * avg_size,
        }

    def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection")
