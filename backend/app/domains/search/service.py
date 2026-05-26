"""Search orchestration service with caching, authorization, and telemetry."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.search.engine import HybridRetrievalEngine, RetrievedChunk, RetrievalResult
from app.domains.search.repository import SearchRepository
from app.domains.search.schemas import SearchRequest, SearchResponse, SearchResultItem
from app.kernel.security.auth import UserContext

logger = logging.getLogger(__name__)


@dataclass
class SearchService:
    """Enterprise search service with caching, authorization, and analytics."""

    session: AsyncSession
    tenant_id: str
    user: Optional[UserContext] = None

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute search with caching, authorization, and analytics logging."""
        start = time.monotonic()
        repo = SearchRepository(self.session, tenant_id=self.tenant_id)
        engine = HybridRetrievalEngine(self.session, self.tenant_id, self.user)

        # Check semantic cache
        cache_key = self._cache_key(request)
        cached = await repo.cache_get(self.tenant_id, cache_key)
        if cached:
            latency_ms = int((time.monotonic() - start) * 1000)
            results = [SearchResultItem(**item) for item in cached]
            return SearchResponse(
                results=results, total=len(results),
                page=request.page, page_size=request.page_size,
                query=request.query, strategy=request.strategy,
                latency_ms=latency_ms,
            )

        # Execute retrieval
        result = await engine.search(
            query=request.query,
            strategy=request.strategy,
            filters=request.filters,
            clause_type=request.clause_type,
            contract_id=request.contract_id,
            page=request.page,
            page_size=request.page_size,
        )

        # Build response items with citations
        items = []
        for chunk in result.results:
            snippet = HybridRetrievalEngine.generate_snippet(chunk.text, request.query)
            items.append(SearchResultItem(
                chunk_id=chunk.chunk_id,
                upload_id=chunk.upload_id,
                contract_id=chunk.contract_id,
                contract_name=chunk.contract_name,
                page_numbers=chunk.page_numbers,
                section_heading=chunk.section_heading,
                clause_type=chunk.clause_type,
                snippet=snippet,
                score=round(chunk.score, 4),
                strategy=chunk.strategy,
                token_count=chunk.token_count,
            ))

        # Cache results (only for hybrid searches with results)
        if request.strategy == "hybrid" and items:
            cache_data = [item.model_dump() for item in items]
            await repo.cache_set(self.tenant_id, cache_key, request.query, cache_data, ttl=300)

        return SearchResponse(
            results=items,
            total=result.total,
            page=request.page,
            page_size=request.page_size,
            query=request.query,
            strategy=request.strategy,
            latency_ms=result.latency_ms,
        )

    async def log_click(
        self, query_id: str, result_position: int,
        entity_type: str, entity_id: str,
        chunk_id: Optional[str] = None, score: Optional[float] = None,
    ) -> None:
        """Log a search click for ranking model training."""
        repo = SearchRepository(self.session, tenant_id=self.tenant_id)
        await repo.log_click(
            query_id=query_id, tenant_id=self.tenant_id,
            result_position=result_position, entity_type=entity_type,
            entity_id=entity_id, chunk_id=chunk_id, score=score,
        )

    async def get_popular_queries(self, limit: int = 20) -> list[dict]:
        """Get popular search queries for this tenant."""
        repo = SearchRepository(self.session, tenant_id=self.tenant_id)
        rows = await repo.get_popular_queries(self.tenant_id, limit)
        return [{"query": r[0], "frequency": r[1]} for r in rows]

    async def get_zero_result_queries(self, limit: int = 20) -> list[dict]:
        """Get queries that returned zero results (quality signal)."""
        repo = SearchRepository(self.session, tenant_id=self.tenant_id)
        queries = await repo.get_zero_result_queries(self.tenant_id, limit)
        return [{"query": q.query_text, "created_at": q.created_at.isoformat()} for q in queries]

    async def search_findings(
        self, query: str, severity: Optional[str] = None,
        clause_type: Optional[str] = None, resolution: Optional[str] = None,
        review_id: Optional[str] = None, page: int = 1, page_size: int = 20,
    ) -> dict:
        """Search across AI findings (titles, descriptions, recommendations)."""
        from sqlalchemy import text as sa_text

        conditions = ["f.tenant_id = :tenant_id"]
        bind = {"tenant_id": self.tenant_id, "query": f"%{query}%"}

        if severity:
            conditions.append("f.severity = :severity")
            bind["severity"] = severity
        if clause_type:
            conditions.append("f.clause_type = :clause_type")
            bind["clause_type"] = clause_type
        if resolution:
            conditions.append("f.resolution = :resolution")
            bind["resolution"] = resolution
        if review_id:
            conditions.append("f.review_id = :review_id")
            bind["review_id"] = review_id

        where = " AND ".join(conditions)

        # Count
        count_sql = sa_text(f"""
            SELECT COUNT(*)::int FROM review_findings f
            WHERE {where}
              AND (f.title ILIKE :query OR f.description ILIKE :query OR f.recommendation ILIKE :query)
        """)
        result = await self.session.execute(count_sql, bind)
        total = result.scalar() or 0

        # Fetch
        offset = (page - 1) * page_size
        data_sql = sa_text(f"""
            SELECT f.finding_id, f.review_id, f.severity, f.clause_type,
                   f.title, f.description, f.recommendation, f.confidence,
                   f.resolution, f.page_numbers, f.created_at
            FROM review_findings f
            WHERE {where}
              AND (f.title ILIKE :query OR f.description ILIKE :query OR f.recommendation ILIKE :query)
            ORDER BY
                CASE f.severity
                    WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5
                END,
                f.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        bind["limit"] = page_size
        bind["offset"] = offset
        result = await self.session.execute(data_sql, bind)

        findings = []
        for row in result.fetchall():
            findings.append({
                "finding_id": str(row.finding_id),
                "review_id": str(row.review_id) if row.review_id else None,
                "severity": row.severity,
                "clause_type": row.clause_type,
                "title": row.title,
                "description": row.description[:300] + ("..." if len(row.description or "") > 300 else ""),
                "recommendation": row.recommendation,
                "confidence": row.confidence,
                "resolution": row.resolution,
                "page_numbers": row.page_numbers,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })

        return {
            "findings": findings,
            "total": total,
            "page": page,
            "page_size": page_size,
            "query": query,
        }

    async def search_clauses(
        self, query: str, clause_type: Optional[str] = None,
        contract_id: Optional[str] = None, page: int = 1, page_size: int = 20,
    ) -> dict:
        """Search across contract clause text using hybrid search."""
        from app.domains.search.schemas import SearchRequest

        req = SearchRequest(
            query=query,
            strategy="hybrid",
            clause_type=clause_type,
            contract_id=contract_id,
            page=page,
            page_size=page_size,
        )
        result = await self.search(req)
        return {
            "results": [r.model_dump() for r in result.results],
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
            "query": query,
            "latency_ms": result.latency_ms,
        }

    async def get_pulse(self) -> dict:
        """Get portfolio-level search intelligence for the discovery panel.

        Returns total indexed chunks/contracts, today's query count,
        popular queries, dynamic suggestions from findings DB,
        and portfolio insights.
        """
        from sqlalchemy import text as sa_text

        # Total indexed chunks
        chunk_count = await self.session.execute(
            sa_text("SELECT COUNT(*)::int FROM chunks WHERE tenant_id = :tid AND is_active = TRUE AND is_duplicate = FALSE"),
            {"tid": self.tenant_id},
        )
        total_chunks = chunk_count.scalar() or 0

        # Total contracts (unique uploads with chunks)
        contract_count = await self.session.execute(
            sa_text("SELECT COUNT(DISTINCT upload_id)::int FROM chunks WHERE tenant_id = :tid AND is_active = TRUE"),
            {"tid": self.tenant_id},
        )
        total_contracts = contract_count.scalar() or 0

        # Total findings
        finding_count = await self.session.execute(
            sa_text("SELECT COUNT(*)::int FROM review_findings WHERE tenant_id = :tid"),
            {"tid": self.tenant_id},
        )
        total_findings = finding_count.scalar() or 0

        # Average risk score from reviews
        avg_risk = await self.session.execute(
            sa_text("""
                SELECT AVG((metadata->>'risk_score')::numeric)::float
                FROM contract_reviews
                WHERE tenant_id = :tid AND metadata->>'risk_score' IS NOT NULL
            """),
            {"tid": self.tenant_id},
        )
        avg_risk_score = avg_risk.scalar()

        # Queries today
        queries_today = await self.session.execute(
            sa_text("SELECT COUNT(*)::int FROM search_queries WHERE tenant_id = :tid AND created_at >= NOW() - INTERVAL '24 hours'"),
            {"tid": self.tenant_id},
        )
        queries_today_count = queries_today.scalar() or 0

        # Popular queries
        popular = await self.session.execute(
            sa_text("""
                SELECT query_text, COUNT(*)::int AS freq
                FROM search_queries
                WHERE tenant_id = :tid
                GROUP BY query_text
                ORDER BY freq DESC
                LIMIT 10
            """),
            {"tid": self.tenant_id},
        )
        popular_queries = [{"query": r.query_text, "frequency": r.freq} for r in popular.fetchall()]

        # ── Dynamic suggestions from findings ─────────────────────
        suggestions = []

        # Helper to run a count query once and return the value
        async def _count(query: str) -> int:
            result = await self.session.execute(sa_text(query), {"tid": self.tenant_id})
            return result.scalar() or 0

        # Missing indemnification
        c = await _count("SELECT COUNT(*)::int FROM review_findings WHERE tenant_id = :tid AND clause_type = 'indemnification' AND severity IN ('critical','high')")
        if c > 0:
            suggestions.append({
                "query": "missing indemnification clause",
                "description": f"Contracts with missing or inadequate indemnification provisions",
                "category": "missing_clause",
                "result_count": c,
                "severity": "critical",
            })

        # Unlimited liability
        c = await _count("SELECT COUNT(*)::int FROM review_findings WHERE tenant_id = :tid AND clause_type = 'liability' AND severity IN ('critical','high')")
        if c > 0:
            suggestions.append({
                "query": "unlimited liability",
                "description": "Contracts with uncapped or unlimited liability clauses",
                "category": "risk",
                "result_count": c,
                "severity": "critical",
            })

        # Auto renewal risk
        c = await _count("SELECT COUNT(*)::int FROM review_findings WHERE tenant_id = :tid AND clause_type = 'term_and_termination' AND severity IN ('critical','high')")
        if c > 0:
            suggestions.append({
                "query": "auto renewal risk",
                "description": "Contracts with auto-renewal clauses and short notice periods",
                "category": "renewal",
                "result_count": c,
                "severity": "warning",
            })

        # GDPR / data privacy
        c = await _count("SELECT COUNT(*)::int FROM review_findings WHERE tenant_id = :tid AND clause_type = 'data_privacy' AND severity IN ('critical','high')")
        if c > 0:
            suggestions.append({
                "query": "GDPR compliance gaps",
                "description": "Contracts missing data processing addendums or GDPR provisions",
                "category": "compliance",
                "result_count": c,
                "severity": "critical",
            })

        # Force majeure
        c = await _count("SELECT COUNT(*)::int FROM review_findings WHERE tenant_id = :tid AND clause_type = 'force_majeure' AND severity IN ('critical','high')")
        if c > 0:
            suggestions.append({
                "query": "missing force majeure",
                "description": "Contracts lacking force majeure clauses",
                "category": "missing_clause",
                "result_count": c,
                "severity": "warning",
            })

        # High-risk contracts
        high_risk_count = await _count("SELECT COUNT(*)::int FROM contract_reviews WHERE tenant_id = :tid AND (metadata->>'risk_score')::numeric >= 0.7")
        if high_risk_count > 0:
            suggestions.append({
                "query": "high risk contracts",
                "description": f"{high_risk_count} contracts with risk score ≥ 70%",
                "category": "portfolio",
                "result_count": high_risk_count,
                "severity": "critical",
            })

        # ── Portfolio insights ────────────────────────────────────
        insights = []

        if total_findings > 0:
            sev_counts = await self.session.execute(
                sa_text("""
                    SELECT severity, COUNT(*)::int AS cnt
                    FROM review_findings WHERE tenant_id = :tid
                    GROUP BY severity ORDER BY cnt DESC LIMIT 3
                """),
                {"tid": self.tenant_id},
            )
            top_severities = [{"severity": r.severity, "count": r.cnt} for r in sev_counts.fetchall()]
            if top_severities:
                sev_str = ", ".join(f"{s['count']} {s['severity']}" for s in top_severities)
                insights.append({
                    "type": "pattern",
                    "title": "Finding Severity Distribution",
                    "description": f"Top findings by severity: {sev_str}",
                    "severity": "info",
                    "confidence": 95,
                    "impact": "medium",
                    "entities": [s["severity"] for s in top_severities],
                    "suggested_query": "high risk findings",
                    "finding_count": total_findings,
                })

        if avg_risk_score is not None:
            insights.append({
                "type": "risk",
                "title": "Portfolio Risk Overview",
                "description": f"Average risk score across {total_contracts} contracts is {(avg_risk_score * 100):.0f}%. {high_risk_count} contracts exceed 70% risk threshold.",
                "severity": "warning" if avg_risk_score >= 0.5 else "info",
                "confidence": 90,
                "impact": "high",
                "entities": [f"{(avg_risk_score * 100):.0f}% avg risk"],
                "suggested_query": "high risk contracts",
                "finding_count": high_risk_count,
            })

        return {
            "total_chunks": total_chunks,
            "total_contracts": total_contracts,
            "total_findings": total_findings,
            "avg_risk_score": avg_risk_score,
            "queries_today": queries_today_count,
            "popular_queries": popular_queries,
            "suggestions": suggestions,
            "insights": insights,
        }

    @staticmethod
    def _cache_key(request: SearchRequest) -> str:
        """Generate deterministic cache key from request."""
        raw = f"{request.query}|{request.strategy}|{json.dumps(request.filters or {})}|{request.clause_type}|{request.contract_id}|{request.page}|{request.page_size}"
        return hashlib.sha256(raw.encode()).hexdigest()
