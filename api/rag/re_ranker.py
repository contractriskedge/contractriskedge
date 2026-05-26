"""Cross-encoder re-ranking for precision improvement.

Provides cross-encoder based re-ranking to improve retrieval precision
by scoring query-document pairs with a more powerful model than the
initial embedding similarity.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .models import RetrievedChunk, SearchQuery

logger = logging.getLogger(__name__)


class CrossEncoderReRanker:
    """Cross-encoder re-ranker for improving retrieval precision.

    Uses a cross-encoder model to re-score query-document pairs,
    providing more accurate relevance judgments than embedding
    similarity alone. Supports both local and API-based models.

    Usage:
        reranker = CrossEncoderReRanker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        results = await reranker.rerank(query_text, candidates, top_k=5)
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_api: bool = False,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        batch_size: int = 32,
    ) -> None:
        """Initialize the cross-encoder re-ranker.

        Args:
            model_name: Cross-encoder model name or API endpoint.
            use_api: If True, use an API-based model instead of local.
            api_key: API key for API-based model.
            api_url: URL for API-based model.
            batch_size: Batch size for processing.
        """
        self._model_name = model_name
        self._use_api = use_api
        self._api_key = api_key
        self._api_url = api_url
        self._batch_size = batch_size
        self._model = None
        self._tokenizer = None

        if not use_api:
            self._load_local_model()

    def _load_local_model(self) -> None:
        """Load the cross-encoder model locally."""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self._model_name
            )
            logger.info(
                "Loaded cross-encoder model: %s", self._model_name
            )
        except ImportError:
            logger.warning(
                "transformers not installed. Install with: pip install transformers"
            )
        except Exception as exc:
            logger.warning(
                "Failed to load cross-encoder model '%s': %s",
                self._model_name,
                exc,
            )

    async def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        """Re-rank candidates using cross-encoder scoring.

        Args:
            query: The original search query.
            candidates: Initial retrieval candidates.
            top_k: Number of results to return (default: all).

        Returns:
            Re-ranked list of retrieved chunks.
        """
        if not candidates:
            return []

        if top_k is None:
            top_k = len(candidates)

        if self._use_api:
            scores = await self._score_via_api(query, candidates)
        elif self._model is not None and self._tokenizer is not None:
            scores = self._score_via_local_model(query, candidates)
        else:
            # Fall back to original scores if no model available
            logger.warning("No cross-encoder model available, using original scores")
            return sorted(candidates, key=lambda x: x.score, reverse=True)[:top_k]

        # Assign re-rank scores
        for chunk, score in zip(candidates, scores):
            chunk.rerank_score = score

        # Sort by re-rank score
        reranked = sorted(
            candidates,
            key=lambda x: x.rerank_score or 0.0,
            reverse=True,
        )

        return reranked[:top_k]

    def _score_via_local_model(
        self, query: str, candidates: List[RetrievedChunk]
    ) -> List[float]:
        """Score candidates using a local cross-encoder model.

        Args:
            query: The search query.
            candidates: Candidates to score.

        Returns:
            List of relevance scores.
        """
        import torch

        scores: list[float] = []

        for i in range(0, len(candidates), self._batch_size):
            batch = candidates[i:i + self._batch_size]
            pairs = [(query, c.text) for c in batch]

            inputs = self._tokenizer(
                pairs,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )

            with torch.no_grad():
                outputs = self._model(**inputs)
                logits = outputs.logits

            # Convert logits to probabilities
            batch_scores = torch.sigmoid(logits).squeeze(-1).tolist()
            if isinstance(batch_scores, float):
                batch_scores = [batch_scores]
            scores.extend(batch_scores)

        return scores

    async def _score_via_api(
        self, query: str, candidates: List[RetrievedChunk]
    ) -> List[float]:
        """Score candidates using an API-based cross-encoder.

        Args:
            query: The search query.
            candidates: Candidates to score.

        Returns:
            List of relevance scores.
        """
        import httpx
        import json

        if not self._api_url:
            logger.warning("No API URL configured for re-ranker")
            return [c.score for c in candidates]

        scores: list[float] = []

        for i in range(0, len(candidates), self._batch_size):
            batch = candidates[i:i + self._batch_size]
            pairs = [{"query": query, "text": c.text} for c in batch]

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self._api_url,
                        json={"pairs": pairs},
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    batch_scores = data.get("scores", [])
                    scores.extend(batch_scores)

            except Exception as exc:
                logger.error("Re-ranker API call failed: %s", exc)
                # Fall back to original scores for this batch
                scores.extend([c.score for c in batch])

        return scores

    async def rerank_batch(
        self,
        queries_and_candidates: List[Tuple[str, List[RetrievedChunk]]],
        top_k: Optional[int] = None,
    ) -> List[List[RetrievedChunk]]:
        """Re-rank multiple query-candidate pairs.

        Args:
            queries_and_candidates: List of (query, candidates) pairs.
            top_k: Number of results per query.

        Returns:
            List of re-ranked result lists.
        """
        results: list[list[RetrievedChunk]] = []
        for query, candidates in queries_and_candidates:
            reranked = await self.rerank(query, candidates, top_k)
            results.append(reranked)
        return results

    @property
    def is_available(self) -> bool:
        """Check if the re-ranker model is available.

        Returns:
            True if the model is loaded or API is configured.
        """
        if self._use_api:
            return self._api_url is not None
        return self._model is not None and self._tokenizer is not None
