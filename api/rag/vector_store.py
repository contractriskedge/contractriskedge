"""Pinecone vector store client with namespace isolation per tenant.

Provides a Pinecone client for vector storage and similarity search
with tenant-level namespace isolation, metadata filtering, and
comprehensive error handling.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from .models import RetrievedChunk, SearchQuery

logger = logging.getLogger(__name__)

# Conditional import for Pinecone
try:
    from pinecone import Pinecone, ServerlessSpec

    _HAS_PINECONE = True
except ImportError:
    _HAS_PINECONE = False


class PineconeVectorStore:
    """Pinecone vector store with tenant namespace isolation.

    Provides vector storage and similarity search with automatic
    namespace isolation per tenant, metadata filtering, and
    configurable index management.

    Usage:
        store = PineconeVectorStore(
            api_key="pc-...",
            environment="us-east-1-aws",
            index_name="contract-chunks",
            dimension=1536,
        )
        await store.upsert_vectors(
            vectors=[("id1", [0.1, ...], {"text": "..."})],
            tenant_id="tenant-123",
        )
        results = await store.search(
            query_vector=[0.1, ...],
            top_k=5,
            tenant_id="tenant-123",
        )
    """

    def __init__(
        self,
        api_key: str,
        environment: str,
        index_name: str,
        dimension: int = 1536,
        metric: str = "cosine",
        cloud: str = "aws",
    ) -> None:
        """Initialize the Pinecone vector store.

        Args:
            api_key: Pinecone API key.
            environment: Pinecone environment (e.g., 'us-east-1-aws').
            index_name: Name of the Pinecone index.
            dimension: Vector dimension (must match index config).
            metric: Distance metric ('cosine', 'euclidean', 'dotproduct').
            cloud: Cloud provider for serverless index.
        """
        self._api_key = api_key
        self._environment = environment
        self._index_name = index_name
        self._dimension = dimension
        self._metric = metric
        self._cloud = cloud
        self._index: Optional[Any] = None
        self._pinecone: Optional[Any] = None

        if not _HAS_PINECONE:
            logger.warning(
                "Pinecone SDK not installed. Install with: pip install pinecone"
            )

    def _ensure_initialized(self) -> None:
        """Ensure Pinecone client and index are initialized.

        Raises:
            RuntimeError: If Pinecone SDK is not installed.
        """
        if not _HAS_PINECONE:
            raise RuntimeError(
                "Pinecone SDK is not installed. Install with: pip install pinecone"
            )

        if self._pinecone is None:
            self._pinecone = Pinecone(api_key=self._api_key)

        if self._index is None:
            self._ensure_index_exists()
            self._index = self._pinecone.Index(self._index_name)

    def _ensure_index_exists(self) -> None:
        """Create the index if it doesn't exist."""
        if self._pinecone is None:
            return

        existing_indexes = self._pinecone.list_indexes()
        index_names = [idx.name for idx in existing_indexes]

        if self._index_name not in index_names:
            logger.info(
                "Creating Pinecone index '%s' (dimension=%d, metric=%s)",
                self._index_name,
                self._dimension,
                self._metric,
            )
            self._pinecone.create_index(
                name=self._index_name,
                dimension=self._dimension,
                metric=self._metric,
                spec=ServerlessSpec(
                    cloud=self._cloud,
                    region=self._environment,
                ),
            )
            # Wait for index to be ready
            import time as t
            t.sleep(5)

    def _get_namespace(self, tenant_id: Optional[str]) -> str:
        """Get the Pinecone namespace for a tenant.

        Args:
            tenant_id: Tenant identifier. If None, uses 'default'.

        Returns:
            Namespace string.
        """
        return f"tenant_{tenant_id}" if tenant_id else "default"

    async def upsert_vectors(
        self,
        vectors: List[Tuple[str, List[float], Dict[str, Any]]],
        tenant_id: Optional[str] = None,
        batch_size: int = 100,
    ) -> int:
        """Upsert vectors into the index.

        Args:
            vectors: List of (id, embedding, metadata) tuples.
            tenant_id: Tenant for namespace isolation.
            batch_size: Number of vectors per upsert batch.

        Returns:
            Number of vectors upserted.
        """
        self._ensure_initialized()
        namespace = self._get_namespace(tenant_id)
        total = 0

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            pinecone_vectors = [
                {
                    "id": vec_id,
                    "values": embedding,
                    "metadata": metadata,
                }
                for vec_id, embedding, metadata in batch
            ]

            try:
                self._index.upsert(
                    vectors=pinecone_vectors,
                    namespace=namespace,
                )
                total += len(batch)
            except Exception as exc:
                logger.error(
                    "Failed to upsert batch %d-%d: %s",
                    i,
                    i + len(batch),
                    exc,
                )
                raise

            logger.debug(
                "Upserted %d vectors to namespace '%s'",
                len(batch),
                namespace,
            )

        return total

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        tenant_id: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
        include_metadata: bool = True,
    ) -> List[RetrievedChunk]:
        """Search for similar vectors in the index.

        Args:
            query_vector: The query embedding vector.
            top_k: Number of results to return.
            tenant_id: Tenant for namespace isolation.
            filter_dict: Optional metadata filter.
            min_score: Minimum similarity score threshold.
            include_metadata: Whether to include metadata in results.

        Returns:
            List of retrieved chunks with scores.
        """
        self._ensure_initialized()
        namespace = self._get_namespace(tenant_id)

        try:
            response = self._index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter_dict,
                include_metadata=include_metadata,
            )

            results: list[RetrievedChunk] = []
            for match in response.matches:
                score = match.score or 0.0
                if score < min_score:
                    continue

                metadata = match.metadata or {}
                results.append(
                    RetrievedChunk(
                        chunk_id=match.id,
                        text=metadata.get("text", ""),
                        score=score,
                        metadata=metadata,
                        contract_id=metadata.get("contract_id"),
                        clause_id=metadata.get("clause_id"),
                        page_number=metadata.get("page_number"),
                        section=metadata.get("section"),
                        risk_category=metadata.get("risk_category"),
                    )
                )

            return results

        except Exception as exc:
            logger.error("Pinecone search failed: %s", exc)
            raise

    async def delete_vectors(
        self,
        ids: Optional[List[str]] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        delete_all: bool = False,
    ) -> int:
        """Delete vectors from the index.

        Args:
            ids: Specific vector IDs to delete.
            filter_dict: Delete vectors matching this filter.
            tenant_id: Tenant namespace.
            delete_all: Delete all vectors in the namespace.

        Returns:
            Number of vectors deleted.
        """
        self._ensure_initialized()
        namespace = self._get_namespace(tenant_id)

        try:
            if delete_all:
                self._index.delete(delete_all=True, namespace=namespace)
                logger.info("Deleted all vectors in namespace '%s'", namespace)
                return -1  # Exact count unknown

            if ids:
                self._index.delete(ids=ids, namespace=namespace)
                return len(ids)

            if filter_dict:
                self._index.delete(filter=filter_dict, namespace=namespace)
                return -1  # Exact count unknown

            return 0

        except Exception as exc:
            logger.error("Failed to delete vectors: %s", exc)
            raise

    async def describe_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index.

        Returns:
            Dict with index statistics.
        """
        self._ensure_initialized()

        try:
            stats = self._index.describe_index_stats()
            return {
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "total_vector_count": stats.total_vector_count,
                "namespaces": {
                    ns: {"vector_count": ns_stats.vector_count}
                    for ns, ns_stats in (stats.namespaces or {}).items()
                },
            }
        except Exception as exc:
            logger.error("Failed to get index stats: %s", exc)
            raise

    async def health_check(self) -> bool:
        """Check if the Pinecone index is accessible.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            if not _HAS_PINECONE:
                return False
            self._ensure_initialized()
            stats = self._index.describe_index_stats()
            return stats is not None
        except Exception as exc:
            logger.warning("Pinecone health check failed: %s", exc)
            return False
