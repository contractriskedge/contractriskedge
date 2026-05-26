"""LlamaIndex RAG retriever with top_k=5 and MMR diversity.

Provides a semantic retriever that combines embedding similarity search
with MMR (Maximum Marginal Relevance) diversity to ensure diverse and
relevant results for contract risk analysis.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from .models import RAGResult, RetrievedChunk, SearchQuery
from .vector_store import PineconeVectorStore
from .embedding import EmbeddingPipeline

logger = logging.getLogger(__name__)


class RAGRetriever:
    """LlamaIndex-style RAG retriever with MMR diversity.

    Retrieves relevant contract clauses using embedding similarity
    with MMR diversity to balance relevance and variety. Supports
    metadata filtering, namespace isolation, and configurable
    retrieval parameters.

    Usage:
        vector_store = PineconeVectorStore(...)
        embedding = EmbeddingPipeline(api_key="sk-...")
        retriever = RAGRetriever(vector_store, embedding)
        result = await retriever.retrieve(SearchQuery(query_text="..."))
    """

    def __init__(
        self,
        vector_store: PineconeVectorStore,
        embedding_pipeline: EmbeddingPipeline,
        default_top_k: int = 5,
        default_diversity: float = 0.3,
    ) -> None:
        """Initialize the RAG retriever.

        Args:
            vector_store: Pinecone vector store instance.
            embedding_pipeline: Embedding pipeline for query encoding.
            default_top_k: Default number of results to return.
            default_diversity: Default MMR diversity factor.
        """
        self._vector_store = vector_store
        self._embedding = embedding_pipeline
        self._default_top_k = default_top_k
        self._default_diversity = default_diversity

    async def retrieve(self, query: SearchQuery) -> RAGResult:
        """Retrieve relevant chunks for a search query.

        Embeds the query, searches the vector store, and optionally
        applies MMR diversity re-ranking.

        Args:
            query: The search query with parameters.

        Returns:
            RAGResult with retrieved and ranked chunks.
        """
        top_k = query.top_k or self._default_top_k
        start_time = time.monotonic()

        # Generate query embedding
        embed_start = time.monotonic()
        query_vector = await self._embedding.embed_text(query.query_text)
        embed_time = (time.monotonic() - embed_start) * 1000

        # Search vector store (fetch more for MMR diversity)
        fetch_k = top_k * 3 if query.diversity_factor > 0 else top_k
        search_start = time.monotonic()
        results = await self._vector_store.search(
            query_vector=query_vector,
            top_k=fetch_k,
            tenant_id=query.tenant_id,
            filter_dict=query.metadata_filter,
            min_score=query.min_score,
        )
        search_time = (time.monotonic() - search_start) * 1000

        # Apply MMR diversity if configured
        if query.diversity_factor > 0 and len(results) > top_k:
            results = self._apply_mmr(
                query_vector=query_vector,
                candidates=results,
                top_k=top_k,
                diversity_lambda=query.diversity_factor,
            )
        else:
            results = results[:top_k]

        total_time = (time.monotonic() - start_time) * 1000

        return RAGResult(
            query=query,
            results=results,
            total_found=len(results),
            retrieval_time_ms=search_time + (total_time - search_time - embed_time),
            embedding_time_ms=embed_time,
            query_embedding_model=self._embedding.MODEL_NAME,
            created_at=__import__("datetime").datetime.utcnow(),
        )

    def _apply_mmr(
        self,
        query_vector: List[float],
        candidates: List[RetrievedChunk],
        top_k: int,
        diversity_lambda: float = 0.3,
    ) -> List[RetrievedChunk]:
        """Apply Maximum Marginal Relevance for diverse results.

        Balances relevance to the query with diversity among results
        to avoid redundant retrievals.

        Args:
            query_vector: The query embedding.
            candidates: Initial retrieval candidates.
            top_k: Number of results to return.
            diversity_lambda: Balance parameter (0=only relevance,
                             1=only diversity).

        Returns:
            Diverse subset of candidates.
        """
        if not candidates:
            return []

        selected: list[RetrievedChunk] = []
        remaining = list(candidates)

        # Select the first by relevance
        selected.append(remaining.pop(0))

        while len(selected) < top_k and remaining:
            best_score = -float("inf")
            best_idx = 0

            for i, candidate in enumerate(remaining):
                # Relevance score
                relevance = candidate.score

                # Diversity penalty: max similarity to any selected
                max_sim_to_selected = max(
                    self._cosine_similarity(
                        candidate.metadata.get("_embedding", query_vector),
                        sel.metadata.get("_embedding", query_vector),
                    )
                    for sel in selected
                )

                # MMR score
                mmr_score = (
                    diversity_lambda * relevance
                    - (1 - diversity_lambda) * max_sim_to_selected
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    def _cosine_similarity(
        self, vec_a: List[float], vec_b: List[float]
    ) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec_a: First vector.
            vec_b: Second vector.

        Returns:
            Cosine similarity score (0-1).
        """
        if not vec_a or not vec_b:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    async def batch_retrieve(
        self, queries: List[SearchQuery]
    ) -> List[RAGResult]:
        """Retrieve results for multiple queries.

        Args:
            queries: List of search queries.

        Returns:
            List of RAG results.
        """
        return [await self.retrieve(q) for q in queries]

    async def retrieve_by_category(
        self,
        query_text: str,
        category: str,
        tenant_id: Optional[str] = None,
        top_k: int = 5,
    ) -> RAGResult:
        """Retrieve results filtered by risk category.

        Args:
            query_text: The search query.
            category: Risk category to filter by.
            tenant_id: Optional tenant filter.
            top_k: Number of results.

        Returns:
            RAGResult filtered by category.
        """
        query = SearchQuery(
            query_text=query_text,
            top_k=top_k,
            tenant_id=tenant_id,
            metadata_filter={"risk_category": category},
        )
        return await self.retrieve(query)
