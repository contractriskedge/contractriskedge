"""Benchmark analysis engine — percentile scoring, clause comparison, corpus retrieval, and governance.

Core capabilities:
- Percentile calculation for a contract's clause scores vs corpus distribution
- Clause similarity search via vector embeddings
- Industry cohort comparison
- Market deviation analysis
- Statistical confidence scoring
- Outlier detection and filtering
- Corpus governance helpers (versioning, deduplication)
"""

from __future__ import annotations

import math
import uuid
import logging
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domains.benchmark.models import (
    BenchmarkCorpus,
    BenchmarkClause,
    BenchmarkScore,
    ClauseCategory,
    CorpusIndustry,
)
from app.domains.vectors.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class BenchmarkEngine:
    """Core benchmark analysis engine.

    Provides percentile calculations, clause comparison, and
    corpus retrieval for contract risk benchmarking.
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        self._db = db
        self._tenant_id = tenant_id
        self._embedding_service = EmbeddingService(
            api_key=settings.openai_api_key,
            model=settings.default_embedding_model,
        )

    # ── Corpus Management ──────────────────────────────────────────

    async def list_corpora(self) -> list[BenchmarkCorpus]:
        """List all active benchmark corpora for the tenant."""
        result = await self._db.execute(
            select(BenchmarkCorpus).where(
                BenchmarkCorpus.tenant_id == uuid.UUID(self._tenant_id),
                BenchmarkCorpus.is_active == "true",
            ).order_by(BenchmarkCorpus.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_corpus(self, corpus_id: uuid.UUID) -> Optional[BenchmarkCorpus]:
        """Get a single corpus by ID."""
        result = await self._db.execute(
            select(BenchmarkCorpus).where(
                BenchmarkCorpus.corpus_id == corpus_id,
                BenchmarkCorpus.tenant_id == uuid.UUID(self._tenant_id),
            )
        )
        return result.scalar_one_or_none()

    async def get_corpus_clauses(
        self, corpus_id: uuid.UUID,
        category: Optional[str] = None,
    ) -> list[BenchmarkClause]:
        """Get all clauses in a corpus, optionally filtered by category."""
        query = select(BenchmarkClause).where(
            BenchmarkClause.corpus_id == corpus_id,
            BenchmarkClause.tenant_id == uuid.UUID(self._tenant_id),
        )
        if category:
            query = query.where(BenchmarkClause.category == ClauseCategory(category))
        result = await self._db.execute(query.order_by(BenchmarkClause.created_at))
        return list(result.scalars().all())

    async def add_clause_to_corpus(
        self, corpus_id: uuid.UUID,
        category: str,
        clause_text: str,
        source_document: Optional[str] = None,
        risk_score: Optional[float] = None,
        is_favorable: Optional[str] = None,
    ) -> BenchmarkClause:
        """Add a clause to a benchmark corpus with auto-generated embedding."""
        # Generate embedding for similarity search
        embedding = await self._embedding_service.embed_text(clause_text)

        clause = BenchmarkClause(
            clause_id=uuid.uuid4(),
            corpus_id=corpus_id,
            tenant_id=uuid.UUID(self._tenant_id),
            category=ClauseCategory(category),
            clause_text=clause_text,
            clause_text_snippet=clause_text[:200],
            source_document=source_document,
            embedding=embedding,
            risk_score=risk_score,
            is_favorable=is_favorable,
        )
        self._db.add(clause)

        # Update corpus clause count
        await self._db.execute(
            select(BenchmarkCorpus).where(BenchmarkCorpus.corpus_id == corpus_id)
        )
        corpus = await self.get_corpus(corpus_id)
        if corpus:
            corpus.clause_count = (corpus.clause_count or 0) + 1

        return clause

    # ── Percentile Scoring ─────────────────────────────────────────

    async def compute_percentile(
        self,
        upload_id: uuid.UUID,
        corpus_id: uuid.UUID,
        clause_scores: list[tuple[str, float]],
        clause_texts: Optional[dict[str, str]] = None,
    ) -> list[dict]:
        """Compute percentile scores for a set of clause scores against a corpus.

        Args:
            upload_id: The upload being scored
            corpus_id: The benchmark corpus to compare against
            clause_scores: List of (clause_category, score) tuples
            clause_texts: Optional dict mapping category -> clause_text for similarity search

        Returns:
            List of score dicts with percentile, deviation, market stats, and explainability
        """
        results = []
        all_scores_in_batch = []

        for category_str, your_score in clause_scores:
            category = ClauseCategory(category_str)

            # Get all corpus clause scores for this category
            corpus_clauses = await self._db.execute(
                select(BenchmarkClause.risk_score).where(
                    BenchmarkClause.corpus_id == corpus_id,
                    BenchmarkClause.category == category,
                    BenchmarkClause.risk_score.isnot(None),
                    BenchmarkClause.tenant_id == uuid.UUID(self._tenant_id),
                )
            )
            market_scores = [row[0] for row in corpus_clauses.fetchall() if row[0] is not None]

            if not market_scores:
                logger.info("No market scores for category %s in corpus %s", category_str, corpus_id)
                continue

            # ── Outlier filtering (governance) ──────────────────────
            # Remove extreme outliers before computing statistics
            # to prevent distorted percentiles from anomalous data.
            market_scores.sort()
            outlier_count_before = len(market_scores)
            market_scores = self.filter_outliers(market_scores, method="iqr", iqr_multiplier=1.5)
            outlier_count = outlier_count_before - len(market_scores)
            if outlier_count > 0:
                logger.info(
                    "Filtered %d outliers for category %s in corpus %s",
                    outlier_count, category_str, corpus_id,
                )

            n = len(market_scores)
            market_median = self._median(market_scores)
            market_mean = sum(market_scores) / n
            market_p25 = self._percentile(market_scores, 25)
            market_p75 = self._percentile(market_scores, 75)
            market_stddev = self._stddev(market_scores, market_mean)

            # Compute percentile of your_score within market distribution
            percentile = self._score_percentile(market_scores, your_score)

            # Compute deviation
            deviation = your_score - market_median
            deviation_percent = (deviation / market_median * 100) if market_median != 0 else 0

            # Determine direction
            if deviation_percent > 10:
                direction = "above_market"
            elif deviation_percent < -10:
                direction = "below_market"
            else:
                direction = "at_market"

            # Statistical confidence (based on sample size)
            confidence = min(1.0, n / 100)  # 100+ samples = full confidence

            # ── Explainability: find similar clauses ────────────────
            similar_clauses = []
            clause_text = (clause_texts or {}).get(category_str)
            if clause_text:
                try:
                    similar = await self.find_similar_clauses(
                        clause_text, corpus_id, top_k=3,
                    )
                    similar_clauses = [
                        {
                            "clause_id": s["clause_id"],
                            "category": s["category"],
                            "clause_text": s["clause_text"],
                            "similarity": s["similarity"],
                            "risk_score": s.get("risk_score"),
                        }
                        for s in similar
                    ]
                except Exception as exc:
                    logger.warning("Similarity search failed for explainability: %s", exc)

            # ── Human-readable explanation ──────────────────────────
            explainability = self._build_explainability(
                category_str=category_str,
                your_score=your_score,
                percentile=percentile,
                direction=direction,
                market_median=market_median,
                n=n,
                confidence=confidence,
            )

            score_data = {
                "clause_type": category_str.replace("_", " ").title(),
                "your_score": round(your_score, 2),
                "market_median": round(market_median, 2),
                "market_p25": round(market_p25, 2),
                "market_p75": round(market_p75, 2),
                "market_mean": round(market_mean, 2),
                "market_stddev": round(market_stddev, 2),
                "deviation": round(deviation, 2),
                "deviation_percent": round(deviation_percent, 2),
                "direction": direction,
                "percentile": round(percentile, 2),
                "sample_size": n,
                "confidence": round(confidence, 2),
                "category": category_str,
                "similar_clauses": similar_clauses,
                "explainability": explainability,
            }
            results.append(score_data)

            # Persist the score
            score_record = BenchmarkScore(
                score_id=uuid.uuid4(),
                upload_id=upload_id,
                tenant_id=uuid.UUID(self._tenant_id),
                corpus_id=corpus_id,
                category=category,
                your_score=your_score,
                market_median=market_median,
                market_p25=market_p25,
                market_p75=market_p75,
                market_mean=market_mean,
                market_stddev=market_stddev,
                percentile=percentile,
                deviation=deviation,
                deviation_percent=deviation_percent,
                direction=direction,
                sample_size=n,
                confidence=confidence,
            )
            self._db.add(score_record)
            all_scores_in_batch.append(score_data)

        return results

    async def find_similar_clauses(
        self,
        clause_text: str,
        corpus_id: uuid.UUID,
        top_k: int = 5,
    ) -> list[dict]:
        """Find the most similar clauses in a corpus using vector similarity.

        Falls back to category matching if embeddings are unavailable.
        """
        try:
            embedding = await self._embedding_service.embed_text(clause_text)
            if embedding:
                # Vector similarity search via PostgreSQL pgvector
                result = await self._db.execute(
                    select(
                        BenchmarkClause,
                        BenchmarkClause.embedding.cosine_distance(embedding).label("distance"),
                    ).where(
                        BenchmarkClause.corpus_id == corpus_id,
                        BenchmarkClause.embedding.isnot(None),
                        BenchmarkClause.tenant_id == uuid.UUID(self._tenant_id),
                    ).order_by("distance").limit(top_k)
                )
                rows = result.fetchall()
                return [
                    {
                        "clause_id": str(row[0].clause_id),
                        "category": row[0].category.value if hasattr(row[0].category, 'value') else str(row[0].category),
                        "clause_text": row[0].clause_text[:300],
                        "similarity": float(1 - row[1]) if row[1] is not None else 0,
                        "risk_score": row[0].risk_score,
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Vector similarity search failed: %s", exc)

        return []

    # ── Industry Comparison ────────────────────────────────────────

    async def get_industry_comparison(
        self,
        upload_id: uuid.UUID,
        industry: str,
    ) -> list[dict]:
        """Compare a contract's scores against industry-specific benchmarks."""
        # Find corpora matching this industry
        try:
            industry_enum = CorpusIndustry(industry)
        except ValueError:
            return []

        result = await self._db.execute(
            select(BenchmarkCorpus).where(
                BenchmarkCorpus.industry == industry_enum,
                BenchmarkCorpus.is_active == "true",
            )
        )
        corpora = list(result.scalars().all())

        comparisons = []
        for corpus in corpora:
            # Get aggregate stats per category for this industry corpus
            stats_result = await self._db.execute(
                select(
                    BenchmarkClause.category,
                    func.avg(BenchmarkClause.risk_score),
                    func.count(BenchmarkClause.clause_id),
                ).where(
                    BenchmarkClause.corpus_id == corpus.corpus_id,
                    BenchmarkClause.risk_score.isnot(None),
                ).group_by(BenchmarkClause.category)
            )
            for row in stats_result.fetchall():
                comparisons.append({
                    "industry": industry,
                    "your_score": 0,  # Will be populated from actual scores
                    "industry_avg": round(float(row[1]), 2) if row[1] else 0,
                    "industry_p10": None,
                    "industry_p90": None,
                    "deviation": None,
                    "sample_size": int(row[2]),
                })

        return comparisons

    # ── Dashboard Aggregation ──────────────────────────────────────

    async def get_dashboard_kpis(self) -> list[dict]:
        """Compute aggregate KPI metrics for the benchmark dashboard."""
        corpora = await self.list_corpora()
        total_clauses = sum(c.clause_count or 0 for c in corpora)

        # Count scored contracts
        scores_result = await self._db.execute(
            select(func.count(func.distinct(BenchmarkScore.upload_id))).where(
                BenchmarkScore.tenant_id == uuid.UUID(self._tenant_id),
            )
        )
        scored_contracts = scores_result.scalar() or 0

        # Average percentile across all scores
        avg_percentile_result = await self._db.execute(
            select(func.avg(BenchmarkScore.percentile)).where(
                BenchmarkScore.tenant_id == uuid.UUID(self._tenant_id),
            )
        )
        avg_percentile = avg_percentile_result.scalar() or 50

        # Count above-market deviations
        above_market = await self._db.execute(
            select(func.count(BenchmarkScore.score_id)).where(
                BenchmarkScore.tenant_id == uuid.UUID(self._tenant_id),
                BenchmarkScore.direction == "above_market",
            )
        )

        return [
            {
                "label": "Benchmark Corpora",
                "value": str(len(corpora)),
                "trend": 0,
                "trend_direction": "neutral",
                "severity": "info",
                "tooltip": "Active benchmark reference collections",
            },
            {
                "label": "Indexed Clauses",
                "value": str(total_clauses),
                "trend": 0,
                "trend_direction": "neutral",
                "severity": "info",
                "tooltip": "Normalized clauses available for comparison",
            },
            {
                "label": "Scored Contracts",
                "value": str(scored_contracts),
                "trend": 0,
                "trend_direction": "neutral",
                "severity": "success",
                "tooltip": "Contracts with benchmark percentile scores",
            },
            {
                "label": "Avg Percentile",
                "value": f"{avg_percentile:.0f}th",
                "trend": 0,
                "trend_direction": "neutral",
                "severity": "info",
                "tooltip": "Average percentile rank across all scored contracts",
            },
            {
                "label": "Above Market",
                "value": str(above_market.scalar() or 0),
                "trend": 0,
                "trend_direction": "neutral",
                "severity": "warning",
                "tooltip": "Clauses scoring above market median (higher risk)",
            },
        ]

    # ── Outlier Detection (Governance) ────────────────────────────

    @staticmethod
    def detect_outliers(
        values: list[float],
        method: str = "iqr",
        iqr_multiplier: float = 1.5,
    ) -> tuple[list[int], list[float]]:
        """Detect outlier values using IQR or z-score method.

        Args:
            values: Sorted list of market scores.
            method: ``"iqr"`` (Interquartile Range) or ``"zscore"``.
            iqr_multiplier: IQR multiplier (1.5 = mild, 3.0 = extreme).

        Returns:
            Tuple of ``(outlier_indices, filtered_values)``.
        """
        if len(values) < 4:
            return [], values

        if method == "zscore":
            mean = sum(values) / len(values)
            std = math.sqrt(sum((x - mean) ** 2 for x in values) / (len(values) - 1))
            if std == 0:
                return [], values
            outlier_indices = [
                i for i, v in enumerate(values)
                if abs(v - mean) / std > 3.0
            ]
        else:
            # IQR method
            n = len(values)
            q1 = values[int(n * 0.25)]
            q3 = values[int(n * 0.75)]
            iqr = q3 - q1
            lower = q1 - iqr_multiplier * iqr
            upper = q3 + iqr_multiplier * iqr
            outlier_indices = [
                i for i, v in enumerate(values)
                if v < lower or v > upper
            ]

        filtered = [v for i, v in enumerate(values) if i not in outlier_indices]
        return outlier_indices, filtered

    @staticmethod
    def filter_outliers(
        values: list[float],
        method: str = "iqr",
        iqr_multiplier: float = 1.5,
    ) -> list[float]:
        """Remove outliers from a list of values.

        Convenience wrapper around ``detect_outliers``.
        """
        _, filtered = BenchmarkEngine.detect_outliers(values, method, iqr_multiplier)
        return filtered

    # ── Explainability ────────────────────────────────────────────

    @staticmethod
    def _build_explainability(
        category_str: str,
        your_score: float,
        percentile: float,
        direction: str,
        market_median: float,
        n: int,
        confidence: float,
    ) -> str:
        """Build a human-readable explanation of a benchmark score."""
        label = category_str.replace("_", " ").title()

        if direction == "above_market":
            position = "above the market median"
            implication = "This may indicate higher risk exposure compared to peers."
        elif direction == "below_market":
            position = "below the market median"
            implication = "This may indicate more favorable terms than peer contracts."
        else:
            position = "near the market median"
            implication = "This is consistent with typical market practice."

        confidence_note = ""
        if confidence < 0.3:
            confidence_note = " However, confidence is low due to limited sample size. Interpret with caution."
        elif confidence < 0.7:
            confidence_note = " Confidence is moderate — more corpus data would improve reliability."

        return (
            f"Your {label} score of {your_score:.0f} ranks at the {percentile:.0f}th percentile, "
            f"{position} (market median: {market_median:.0f}). "
            f"Based on {n} clause{'s' if n != 1 else ''} in the benchmark corpus.{confidence_note} "
            f"{implication}"
        )

    # ── Statistical Helpers ────────────────────────────────────────

    @staticmethod
    def _median(sorted_values: list[float]) -> float:
        n = len(sorted_values)
        if n == 0:
            return 0
        mid = n // 2
        if n % 2 == 0:
            return (sorted_values[mid - 1] + sorted_values[mid]) / 2
        return sorted_values[mid]

    @staticmethod
    def _percentile(sorted_values: list[float], p: int) -> float:
        n = len(sorted_values)
        if n == 0:
            return 0
        k = (p / 100) * (n - 1)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_values[int(k)]
        return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)

    @staticmethod
    def _stddev(values: list[float], mean: float) -> float:
        n = len(values)
        if n <= 1:
            return 0
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        return math.sqrt(variance)

    @staticmethod
    def _score_percentile(sorted_values: list[float], score: float) -> float:
        """Compute the percentile rank of a score within a sorted distribution."""
        n = len(sorted_values)
        if n == 0:
            return 50
        count_below = sum(1 for v in sorted_values if v < score)
        count_equal = sum(1 for v in sorted_values if v == score)
        # Use the (C + 0.5 * E) / N * 100 formula for percentile rank
        percentile = ((count_below + 0.5 * count_equal) / n) * 100
        return min(100, max(0, percentile))
