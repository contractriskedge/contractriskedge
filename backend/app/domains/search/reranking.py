"""Reranking preparation — interfaces and placeholders for future cross-encoder reranking."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class RerankCandidate:
    """A candidate for reranking with its initial score and features."""
    chunk_id: str
    text: str
    initial_score: float
    page_numbers: list[int]
    section_heading: Optional[str] = None
    clause_type: Optional[str] = None
    token_count: int = 0
    has_text_layer: bool = True


@dataclass
class RerankResult:
    """Result after reranking with updated score."""
    chunk_id: str
    reranked_score: float
    score_delta: float  # Change from initial score


class Reranker(ABC):
    """Abstract reranker interface.

    V1: No-op (identity reranker — returns candidates unchanged).
    V2: Cross-encoder reranker (e.g., Cohere rerank, BGE reranker).
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        top_k: int = 20,
    ) -> list[RerankResult]:
        """Re-rank candidates by query-document relevance."""
        ...


class IdentityReranker(Reranker):
    """V1 identity reranker — passes through initial scores unchanged.

    Used until cross-encoder reranking is deployed.
    """

    async def rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        top_k: int = 20,
    ) -> list[RerankResult]:
        return [
            RerankResult(
                chunk_id=c.chunk_id,
                reranked_score=c.initial_score,
                score_delta=0.0,
            )
            for c in candidates[:top_k]
        ]


class RerankingPipeline:
    """Reranking pipeline with fallback chain.

    V1: IdentityReranker (no-op).
    V2: CrossEncoderReranker (model-based).
    V3: EnsembleReranker (multiple models).
    """

    def __init__(self, reranker: Optional[Reranker] = None):
        self._reranker = reranker or IdentityReranker()

    async def rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        top_k: int = 20,
    ) -> list[RerankResult]:
        return await self._reranker.rerank(query, candidates, top_k)


# Singleton for V1
reranking_pipeline = RerankingPipeline()
