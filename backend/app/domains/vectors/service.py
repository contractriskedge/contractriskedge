"""Vector ingestion orchestration service — chunking, embedding, and state management."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.config import settings
from app.domains.vectors.models import EmbeddingStatus
from app.domains.vectors.chunking import chunking_service, ChunkData
from app.domains.vectors.embeddings import (
    OpenAIEmbeddingProvider,
    EmbeddingRequest,
    embedding_registry,
)
from app.domains.vectors.repository import VectorRepository
from app.domains.ingestion.models import IngestionState
from app.domains.ingestion.repository import IngestionRepository
from app.domains.extraction.repository import ExtractionRepository
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext

logger = logging.getLogger(__name__)


@dataclass
class VectorIngestionService:
    """Orchestrates chunking, embedding generation, and vector storage."""

    vector_repo: VectorRepository
    extraction_repo: ExtractionRepository
    ingestion_repo: IngestionRepository
    event_bus: EventBus
    user: UserContext
    tenant_id: str

    async def chunk_document(self, upload_id: str) -> list[ChunkData]:
        """Chunk extracted pages into semantic chunks."""
        pages = await self.extraction_repo.get_pages_by_upload(upload_id, self.tenant_id)
        if not pages:
            raise ValueError(f"No extracted pages found for upload {upload_id}")

        page_dicts = [
            {"page_number": p.page_number, "text": p.text}
            for p in pages
        ]

        chunks = chunking_service.chunk_pages(page_dicts, strategy="semantic")
        logger.info("Chunked upload %s into %d chunks", upload_id, len(chunks))

        return chunks

    async def generate_embeddings(self, upload_id: str, chunks: list[ChunkData]) -> dict:
        """Generate embeddings for all chunks using the configured provider."""
        provider = embedding_registry.get_default()
        if not isinstance(provider, OpenAIEmbeddingProvider):
            provider = OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
            embedding_registry.register(provider)

        # Create embedding run
        run = await self.vector_repo.create_run(
            upload_id=upload_id,
            tenant_id=self.tenant_id,
            model="text-embedding-3-large",
            dimension=1536,
        )

        # Prepare requests
        requests = [
            EmbeddingRequest(text=c.text, model="text-embedding-3-large", dimensions=1536)
            for c in chunks
        ]

        # Generate embeddings in batches
        all_responses = []
        total_tokens = 0
        total_cost = 0.0
        total_latency = 0
        chunks_embedded = 0

        for i in range(0, len(requests), provider.MAX_BATCH_SIZE):
            batch = requests[i:i + provider.MAX_BATCH_SIZE]
            try:
                responses = await provider.embed_batch(batch)
                all_responses.extend(responses)

                for j, response in enumerate(responses):
                    chunk_idx = i + j
                    if chunk_idx < len(chunks):
                        await self.vector_repo.update_embedding(
                            chunk_id=chunks[chunk_idx].checksum,  # Will be real chunk_id after store
                            tenant_id=self.tenant_id,
                            embedding=response.embedding,
                            model=response.model,
                            dimension=1536,
                            token_count=response.token_count,
                        )
                        chunks_embedded += 1
                        total_tokens += response.token_count
                        total_cost += response.cost_usd
                        total_latency += response.latency_ms

            except Exception as exc:
                logger.error("Embedding batch failed for upload %s: %s", upload_id, exc)
                await self.vector_repo.record_failure(
                    upload_id=upload_id, tenant_id=self.tenant_id,
                    failure_type="batch_failed", error_message=str(exc),
                    model="text-embedding-3-large",
                )
                raise

        avg_latency = total_latency // max(len(all_responses), 1)

        # Complete run
        await self.vector_repo.complete_run(
            run_id=run.run_id,
            total_chunks=len(chunks),
            chunks_embedded=chunks_embedded,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            avg_latency_ms=avg_latency,
        )

        logger.info(
            "Embeddings generated for upload %s: %d chunks, %d tokens, $%.6f cost",
            upload_id, chunks_embedded, total_tokens, total_cost,
        )

        return {
            "total_chunks": len(chunks),
            "chunks_embedded": chunks_embedded,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "avg_latency_ms": avg_latency,
        }
