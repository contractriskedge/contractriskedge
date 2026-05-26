"""Real-time search index pipeline (V2-026).

Provides async re-indexing of contract clauses into the search index
on every ingest event. Supports incremental indexing and full rebuilds.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SearchIndexPipeline:
    """Async search index pipeline for real-time indexing.

    Automatically re-indexes contract clauses into the search index
    whenever a contract is ingested or updated. Supports incremental
    updates and full index rebuilds.

    Usage:
        pipeline = SearchIndexPipeline(pinecone_index, embedding_fn)
        await pipeline.index_contract(contract_id, clauses)
        await pipeline.rebuild_index(tenant_id)
    """

    def __init__(
        self,
        pinecone_index: Optional[Any] = None,
        embedding_fn: Optional[Callable] = None,
        db_repo: Optional[Any] = None,
        batch_size: int = 100,
    ) -> None:
        """Initialize the search index pipeline.

        Args:
            pinecone_index: Pinecone index for vector storage.
            embedding_fn: Function to generate embeddings.
            db_repo: Database repository for metadata.
            batch_size: Number of vectors to upsert at once.
        """
        self._pinecone_index = pinecone_index
        self._embedding_fn = embedding_fn or self._default_embedding
        self._db_repo = db_repo
        self._batch_size = batch_size
        self._indexing_queue: asyncio.Queue = asyncio.Queue()
        self._is_running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._index_stats: Dict[str, Any] = {
            "total_indexed": 0,
            "total_failed": 0,
            "last_index_time": None,
            "queue_depth": 0,
        }

    async def start(self) -> None:
        """Start the background indexing worker."""
        if self._is_running:
            return
        self._is_running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("Search index pipeline worker started")

    async def stop(self) -> None:
        """Stop the background indexing worker."""
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Search index pipeline worker stopped")

    async def index_contract(
        self,
        contract_id: str,
        tenant_id: str,
        clauses: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Index all clauses of a contract into the search index.

        Args:
            contract_id: The contract identifier.
            tenant_id: The tenant identifier.
            clauses: List of clause dicts with text and metadata.

        Returns:
            Dict with indexing results.
        """
        # Queue for background processing
        await self._indexing_queue.put({
            "action": "index_contract",
            "contract_id": contract_id,
            "tenant_id": tenant_id,
            "clauses": clauses,
            "timestamp": datetime.utcnow().isoformat(),
        })

        self._index_stats["queue_depth"] = self._indexing_queue.qsize()

        return {
            "contract_id": contract_id,
            "clauses_count": len(clauses),
            "queued": True,
            "queue_depth": self._indexing_queue.qsize(),
        }

    async def remove_contract(self, contract_id: str, tenant_id: str) -> Dict[str, Any]:
        """Remove a contract's clauses from the search index.

        Args:
            contract_id: The contract identifier.
            tenant_id: The tenant identifier.

        Returns:
            Dict with removal result.
        """
        await self._indexing_queue.put({
            "action": "remove_contract",
            "contract_id": contract_id,
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return {"contract_id": contract_id, "queued": True}

    async def rebuild_index(self, tenant_id: str) -> Dict[str, Any]:
        """Rebuild the entire search index for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with rebuild status.
        """
        await self._indexing_queue.put({
            "action": "rebuild",
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return {"tenant_id": tenant_id, "rebuild_queued": True}

    async def _process_queue(self) -> None:
        """Background worker that processes the indexing queue."""
        while self._is_running:
            try:
                task = await asyncio.wait_for(self._indexing_queue.get(), timeout=1.0)
                self._index_stats["queue_depth"] = self._indexing_queue.qsize()

                action = task.get("action")

                if action == "index_contract":
                    await self._index_clauses(task)
                elif action == "remove_contract":
                    await self._remove_from_index(task)
                elif action == "rebuild":
                    await self._rebuild_tenant_index(task)

                self._indexing_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Index pipeline worker error: %s", exc)
                self._index_stats["total_failed"] += 1

    async def _index_clauses(self, task: Dict[str, Any]) -> None:
        """Index clauses into the vector store.

        Args:
            task: The indexing task dict.
        """
        contract_id = task["contract_id"]
        tenant_id = task["tenant_id"]
        clauses = task["clauses"]
        namespace = f"tenant_{tenant_id}"

        if not self._pinecone_index:
            logger.warning("No Pinecone index available, skipping indexing")
            return

        vectors = []
        for clause in clauses:
            clause_text = clause.get("text", "") or clause.get("clause_text", "")
            if not clause_text:
                continue

            try:
                embedding = await self._embedding_fn(clause_text)
                clause_id = clause.get("clause_id", f"{contract_id}_{len(vectors)}")

                vectors.append({
                    "id": clause_id,
                    "values": embedding,
                    "metadata": {
                        "clause_id": clause_id,
                        "contract_id": contract_id,
                        "tenant_id": tenant_id,
                        "clause_text": clause_text[:2000],
                        "section": clause.get("section", ""),
                        "page_number": clause.get("page_number", 0),
                        "risk_category": clause.get("risk_category", ""),
                        "risk_score": clause.get("risk_score", 0.0),
                        "contract_type": clause.get("contract_type", ""),
                        "counterparty": clause.get("counterparty", ""),
                        "jurisdiction": clause.get("jurisdiction", ""),
                        "indexed_at": datetime.utcnow().isoformat(),
                    },
                })
            except Exception as exc:
                logger.warning("Failed to embed clause %s: %s", clause.get("clause_id"), exc)
                self._index_stats["total_failed"] += 1

        # Upsert in batches
        for i in range(0, len(vectors), self._batch_size):
            batch = vectors[i:i + self._batch_size]
            try:
                self._pinecone_index.upsert(
                    vectors=batch,
                    namespace=namespace,
                )
                self._index_stats["total_indexed"] += len(batch)
            except Exception as exc:
                logger.error("Failed to upsert batch %d-%d: %s", i, i + len(batch), exc)
                self._index_stats["total_failed"] += len(batch)

        self._index_stats["last_index_time"] = datetime.utcnow().isoformat()
        logger.info("Indexed %d clauses for contract %s", len(vectors), contract_id)

    async def _remove_from_index(self, task: Dict[str, Any]) -> None:
        """Remove a contract's vectors from the index.

        Args:
            task: The removal task dict.
        """
        if not self._pinecone_index:
            return

        contract_id = task["contract_id"]
        tenant_id = task["tenant_id"]
        namespace = f"tenant_{tenant_id}"

        try:
            # Delete by metadata filter
            self._pinecone_index.delete(
                filter={"contract_id": {"$eq": contract_id}},
                namespace=namespace,
            )
            logger.info("Removed contract %s from search index", contract_id)
        except Exception as exc:
            logger.error("Failed to remove contract %s from index: %s", contract_id, exc)

    async def _rebuild_tenant_index(self, task: Dict[str, Any]) -> None:
        """Rebuild the entire index for a tenant.

        Args:
            task: The rebuild task dict.
        """
        tenant_id = task["tenant_id"]
        namespace = f"tenant_{tenant_id}"

        if not self._pinecone_index or not self._db_repo:
            logger.warning("Cannot rebuild index: missing Pinecone or DB repo")
            return

        try:
            # Delete existing namespace
            try:
                self._pinecone_index.delete(delete_all=True, namespace=namespace)
            except Exception:
                pass

            # Fetch all contracts for tenant
            async with self._db_repo.get_connection() as conn:
                from sqlalchemy import text
                rows = await conn.execute(
                    text("""
                        SELECT c.contract_id, c.tenant_id, c.filename, c.contract_type,
                               cl.clause_id, cl.clause_text, cl.section, cl.page_number,
                               cl.risk_category, cl.risk_score
                        FROM contracts c
                        JOIN clauses cl ON c.contract_id = cl.contract_id
                        WHERE c.tenant_id = :tenant_id
                    """),
                    {"tenant_id": tenant_id},
                )
                rows = rows.fetchall() if hasattr(rows, 'fetchall') else rows

            # Group by contract
            contracts: Dict[str, List[Dict]] = {}
            for row in rows:
                cid = row.contract_id
                if cid not in contracts:
                    contracts[cid] = []
                contracts[cid].append({
                    "clause_id": row.clause_id,
                    "clause_text": row.clause_text,
                    "section": row.section,
                    "page_number": row.page_number,
                    "risk_category": row.risk_category,
                    "risk_score": row.risk_score,
                    "contract_type": row.contract_type,
                })

            # Re-index each contract
            total_clauses = 0
            for contract_id, clauses in contracts.items():
                await self._index_clauses({
                    "contract_id": contract_id,
                    "tenant_id": tenant_id,
                    "clauses": clauses,
                })
                total_clauses += len(clauses)

            logger.info("Rebuilt index for tenant %s: %d contracts, %d clauses",
                         tenant_id, len(contracts), total_clauses)

        except Exception as exc:
            logger.error("Failed to rebuild index for tenant %s: %s", tenant_id, exc)

    async def _default_embedding(self, text: str) -> List[float]:
        """Default embedding function.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.
        """
        try:
            import openai
            response = openai.embeddings.create(
                model="text-embedding-3-large",
                input=text,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.warning("Default embedding failed: %s", exc)
            return [0.0] * 1536

    def get_stats(self) -> Dict[str, Any]:
        """Get indexing pipeline statistics.

        Returns:
            Dict with index stats.
        """
        return {
            **self._index_stats,
            "is_running": self._is_running,
            "queue_depth": self._indexing_queue.qsize(),
        }

    async def get_index_status(self, tenant_id: str) -> Dict[str, Any]:
        """Get index status for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with index status.
        """
        return {
            "tenant_id": tenant_id,
            "pipeline_running": self._is_running,
            "stats": self.get_stats(),
        }
