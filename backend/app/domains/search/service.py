"""Search orchestration service with caching, authorization, and telemetry."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.search.engine import HybridRetrievalEngine, RetrievedChunk, RetrievalResult
from app.domains.search.repository import SearchRepository
from app.domains.search.schemas import SearchRequest, SearchResponse, SearchResultItem, SearchClickRequest
from app.kernel.security.auth import UserContext

logger = logging.getLogger(__name__)

_ENTITY_ID_PREFIX_RE = re.compile(r"^(ilike-|finding-|obligation-)")


def _normalize_entity_id(raw: str) -> str:
    """Strip synthetic search result prefixes before persisting click IDs."""
    return _ENTITY_ID_PREFIX_RE.sub("", raw)


def _parse_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
    if not value:
        return None
    try:
        return uuid.UUID(_normalize_entity_id(value))
    except ValueError:
        return None


@dataclass
class SearchService:
    """Enterprise search service with caching, authorization, and analytics."""

    session: AsyncSession
    tenant_id: str
    user: Optional[UserContext] = None

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute search with caching, authorization, and analytics logging.
        
        Searches across multiple entity types:
        - chunks (contract text via hybrid vector/keyword search)
        - findings (AI findings)
        - obligations (if entity_types includes 'obligation')
        """
        start = time.monotonic()
        repo = SearchRepository(self.session, tenant_id=self.tenant_id)
        engine = HybridRetrievalEngine(self.session, self.tenant_id, self.user)
        entity_types = request.entity_types or ["chunk"]

        all_results: list[SearchResultItem] = []
        total = 0
        entity_totals: dict[str, int] = {}

        # ── 1. Chunk search (full-text + vector) ──────────────────
        if "chunk" in entity_types:
            result = await engine.search(
                query=request.query,
                strategy=request.strategy,
                filters=request.filters,
                clause_type=request.clause_type,
                contract_id=request.contract_id,
                page=request.page,
                page_size=request.page_size,
            )
            chunk_total = result.total
            results = []
            # Pre-fetch contract numbers for all upload IDs in results
            # to include them in search results (contract_number is stored
            # in review metadata, not in the chunks table).
            upload_ids = [c.upload_id for c in result.results if c.upload_id]
            contract_numbers: dict[str, str] = {}
            review_ids: dict[str, str] = {}
            if upload_ids:
                try:
                    from sqlalchemy import text as sa_text
                    ids_list = [f"'{uid}'" for uid in set(upload_ids)]
                    cn_result = await self.session.execute(
                        sa_text(f"""
                            SELECT DISTINCT ON (cr.upload_id)
                                cr.upload_id::text,
                                cr.review_id::text,
                                cr.metadata->>'contract_number' AS contract_number
                            FROM contract_reviews cr
                            WHERE cr.upload_id IN ({','.join(ids_list)})
                              AND cr.tenant_id = :tid
                        """),
                        {"tid": self.tenant_id},
                    )
                    for row in cn_result.fetchall():
                        upload_key = str(row.upload_id)
                        review_ids[upload_key] = str(row.review_id)
                        if row.contract_number:
                            contract_numbers[upload_key] = row.contract_number
                except Exception:
                    pass

            for chunk in result.results:
                snippet = HybridRetrievalEngine.generate_snippet(chunk.text, request.query)
                upload_key = chunk.upload_id or ""
                review_id = review_ids.get(upload_key)
                cn = chunk.contract_number or contract_numbers.get(upload_key) if upload_key else None
                results.append(SearchResultItem(
                    chunk_id=chunk.chunk_id,
                    entity_type="chunk",
                    upload_id=chunk.upload_id,
                    review_id=review_id,
                    contract_id=review_id or chunk.contract_id,
                    contract_name=chunk.contract_name,
                    contract_number=cn,
                    page_numbers=chunk.page_numbers,
                    section_heading=chunk.section_heading,
                    clause_type=chunk.clause_type,
                    snippet=snippet,
                    score=round(chunk.score, 4),
                    strategy=chunk.strategy,
                    token_count=chunk.token_count,
                ))

            all_results.extend(results)
            total += chunk_total
            entity_totals["chunk"] = chunk_total

        # ── 2. Finding search ─────────────────────────────────────
        if "finding" in entity_types:
            from sqlalchemy import text as sa_text
            bind = {"tenant_id": self.tenant_id, "query": f"%{request.query}%"}
            conditions = ["f.tenant_id = :tenant_id"]
            if request.contract_id:
                conditions.append("f.review_id = :contract_id")
                bind["contract_id"] = request.contract_id

            where = " AND ".join(conditions)
            f_sql = sa_text(f"""
                SELECT f.finding_id, f.review_id, f.severity, f.clause_type,
                       f.title, f.description, f.recommendation, f.confidence,
                       f.resolution, f.page_numbers, f.created_at,
                       cr.metadata->>'name' as contract_name,
                       cr.metadata->>'contract_number' as contract_number
                FROM review_findings f
                JOIN contract_reviews cr ON cr.review_id = f.review_id AND cr.tenant_id = f.tenant_id
                WHERE {where}
                  AND (f.title ILIKE :query OR f.description ILIKE :query OR f.recommendation ILIKE :query)
                ORDER BY
                    CASE f.severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                    f.created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            offset = (request.page - 1) * request.page_size
            bind["limit"] = request.page_size
            bind["offset"] = offset

            # Count
            count_sql = sa_text(f"""
                SELECT COUNT(*)::int FROM review_findings f
                WHERE {where}
                  AND (f.title ILIKE :query OR f.description ILIKE :query OR f.recommendation ILIKE :query)
            """)
            count_result = await self.session.execute(count_sql, {k: v for k, v in bind.items() if k != "limit" and k != "offset"})
            finding_total = count_result.scalar() or 0

            f_result = await self.session.execute(f_sql, bind)
            for row in f_result.fetchall():
                all_results.append(SearchResultItem(
                    chunk_id=f"finding-{row.finding_id}",
                    entity_type="finding",
                    entity_id=str(row.finding_id),
                    review_id=str(row.review_id) if row.review_id else None,
                    contract_id=str(row.review_id) if row.review_id else None,
                    contract_name=row.contract_name,
                    contract_number=row.contract_number,
                    clause_type=row.clause_type,
                    snippet=(row.title or "") + ": " + (row.description or "")[:200],
                    score=round((row.confidence or 0) * 10, 4),
                    strategy="keyword",
                    status=row.resolution,
                ))
            total += finding_total
            entity_totals["finding"] = finding_total

        # ── 3. Obligation search ──────────────────────────────────
        if "obligation" in entity_types:
            from sqlalchemy import text as sa_text
            bind = {"tenant_id": self.tenant_id, "query": f"%{request.query}%"}
            o_conditions = ["o.tenant_id = :tenant_id"]
            if request.contract_id:
                try:
                    uuid.UUID(request.contract_id)
                    o_conditions.append("o.contract_uuid_id = :contract_id")
                    bind["contract_id"] = request.contract_id
                except ValueError:
                    o_conditions.append("o.contract_id = :contract_id")
                    bind["contract_id"] = request.contract_id

            o_where = " AND ".join(o_conditions)
            offset = (request.page - 1) * request.page_size

            o_count_sql = sa_text(f"""
                SELECT COUNT(*)::int FROM obligations o
                LEFT JOIN contract_reviews cr ON cr.review_id = o.contract_uuid_id
                WHERE {o_where}
                  AND (o.name ILIKE :query OR o.description ILIKE :query
                       OR o.vendor ILIKE :query OR o.contract_name ILIKE :query
                       OR cr.metadata->>'contract_number' ILIKE :query)
            """)
            o_count = await self.session.execute(o_count_sql, {k: v for k, v in bind.items() if k != "limit" and k != "offset"})
            ob_total = o_count.scalar() or 0

            o_sql = sa_text(f"""
                SELECT o.id, o.name, o.description, o.obligation_type, o.status,
                       o.contract_uuid_id, o.contract_name, o.vendor,
                       o.owner, o.due_date, o.risk_level, o.risk_score,
                       cr.metadata->>'contract_number' as contract_number
                FROM obligations o
                LEFT JOIN contract_reviews cr ON cr.review_id = o.contract_uuid_id
                WHERE {o_where}
                  AND (o.name ILIKE :query OR o.description ILIKE :query
                       OR o.vendor ILIKE :query OR o.contract_name ILIKE :query
                       OR cr.metadata->>'contract_number' ILIKE :query)
                ORDER BY
                    CASE WHEN o.name ILIKE :query THEN 0
                         WHEN cr.metadata->>'contract_number' ILIKE :query THEN 1
                         ELSE 2 END,
                    o.created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            bind["limit"] = request.page_size
            bind["offset"] = offset

            o_result = await self.session.execute(o_sql, bind)
            for row in o_result.fetchall():
                all_results.append(SearchResultItem(
                    chunk_id=f"obligation-{row.id}",
                    entity_type="obligation",
                    entity_id=str(row.id),
                    review_id=str(row.contract_uuid_id) if row.contract_uuid_id else None,
                    contract_id=str(row.contract_uuid_id) if row.contract_uuid_id else None,
                    contract_name=row.contract_name,
                    contract_number=row.contract_number,
                    snippet=f"{row.name}: {row.description or ''}"[:300],
                    score=10.0 - (row.risk_score or 0),
                    strategy="keyword",
                    status=row.status,
                    owner=row.owner,
                    due_date=str(row.due_date) if row.due_date else None,
                ))
            total += ob_total
            entity_totals["obligation"] = ob_total

        # ── 4. Contract search (by name/number) ───────────────────
        if "contract" in entity_types:
            from sqlalchemy import text as sa_text
            bind = {"tenant_id": self.tenant_id, "query": f"%{request.query}%"}
            offset = (request.page - 1) * request.page_size

            c_count = await self.session.execute(
                sa_text("""
                    SELECT COUNT(*)::int FROM contract_reviews cr
                    LEFT JOIN upload_sessions us ON us.upload_id = cr.upload_id
                    WHERE cr.tenant_id = :tenant_id
                      AND (cr.review_number ILIKE :query
                           OR cr.metadata->>'name' ILIKE :query
                           OR cr.metadata->>'contract_number' ILIKE :query
                           OR cr.metadata->>'vendor' ILIKE :query
                           OR us.filename ILIKE :query)
                """),
                {"tenant_id": self.tenant_id, "query": f"%{request.query}%"},
            )
            c_total = c_count.scalar() or 0

            if c_total > 0:
                c_sql = sa_text(f"""
                    SELECT cr.review_id, cr.status, cr.review_number,
                           COALESCE(cr.metadata->>'name', us.filename) as contract_name,
                           cr.metadata->>'contract_number' as contract_number,
                           cr.metadata->>'vendor' as vendor,
                           cr.created_at
                    FROM contract_reviews cr
                    LEFT JOIN upload_sessions us ON us.upload_id = cr.upload_id
                    WHERE cr.tenant_id = :tenant_id
                      AND (cr.review_number ILIKE :query
                           OR cr.metadata->>'name' ILIKE :query
                           OR cr.metadata->>'contract_number' ILIKE :query
                           OR cr.metadata->>'vendor' ILIKE :query
                           OR us.filename ILIKE :query)
                    ORDER BY
                        CASE
                            WHEN cr.review_number ILIKE :query THEN 0
                            WHEN us.filename ILIKE :query THEN 1
                            WHEN cr.metadata->>'name' ILIKE :query THEN 2
                            ELSE 3
                        END,
                        cr.created_at DESC
                    LIMIT :limit OFFSET :offset
                """)
                c_result = await self.session.execute(c_sql, {
                    "tenant_id": self.tenant_id,
                    "query": f"%{request.query}%",
                    "limit": request.page_size,
                    "offset": offset,
                })
                for row in c_result.fetchall():
                    all_results.append(SearchResultItem(
                        chunk_id=f"contract-{row.review_id}",
                        entity_type="contract",
                        entity_id=str(row.review_id),
                        review_id=str(row.review_id),
                        contract_id=str(row.review_id),
                        contract_name=row.contract_name,
                        contract_number=row.contract_number,
                        snippet=f"{row.contract_name or row.review_number} ({row.status})",
                        score=9.0,
                        strategy="keyword",
                        status=row.status,
                    ))
                total += c_total
                entity_totals["contract"] = c_total

        # ── 5. Signature request search ───────────────────────────
        if "signature" in entity_types:
            from sqlalchemy import text as sa_text
            s_count = await self.session.execute(
                sa_text("""
                    SELECT COUNT(*)::int FROM signature_requests
                    WHERE tenant_id = :tenant_id
                      AND (title ILIKE :query OR provider_reference ILIKE :query)
                """),
                {"tenant_id": self.tenant_id, "query": f"%{request.query}%"},
            )
            s_total = s_count.scalar() or 0

            if s_total > 0:
                offset = (request.page - 1) * request.page_size
                s_sql = sa_text(f"""
                    SELECT id, title, status, provider, provider_reference,
                           contract_id, created_at
                    FROM signature_requests
                    WHERE tenant_id = :tenant_id
                      AND (title ILIKE :query OR provider_reference ILIKE :query)
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """)
                s_result = await self.session.execute(s_sql, {
                    "tenant_id": self.tenant_id,
                    "query": f"%{request.query}%",
                    "limit": request.page_size,
                    "offset": offset,
                })
                for row in s_result.fetchall():
                    all_results.append(SearchResultItem(
                        chunk_id=f"signature-{row.id}",
                        entity_type="signature",
                        entity_id=str(row.id),
                        contract_id=str(row.contract_id) if row.contract_id else None,
                        contract_name=row.title,
                        snippet=f"Signature: {row.title} ({row.status})",
                        score=8.0,
                        strategy="keyword",
                        status=row.status,
                    ))
                total += s_total
                entity_totals["signature"] = s_total

        # Sort combined results by score descending with entity type boosting.
        # Entity results (contract, finding, obligation, signature) are boosted
        # above chunk text matches so users see the most relevant entities first.
        _ENTITY_BOOST = {
            "contract": 20.0,
            "finding": 15.0,
            "obligation": 15.0,
            "signature": 15.0,
        }
        all_results.sort(
            key=lambda r: r.score + _ENTITY_BOOST.get(r.entity_type, 0.0),
            reverse=True,
        )

        # Paginate combined results
        page = request.page
        page_size = request.page_size
        start_idx = (page - 1) * page_size
        paginated = all_results[start_idx:start_idx + page_size]

        latency_ms = int((time.monotonic() - start) * 1000)
        return SearchResponse(
            results=paginated,
            total=total,
            page=page,
            page_size=page_size,
            query=request.query,
            strategy=request.strategy,
            latency_ms=latency_ms,
            entity_totals=entity_totals,
        )

    async def log_click_from_request(self, request: SearchClickRequest) -> None:
        """Log a search click using the frontend JSON payload."""
        repo = SearchRepository(self.session, tenant_id=self.tenant_id)
        sq = await repo.log_query(
            tenant_id=self.tenant_id,
            user_id=self.user.id if self.user else None,
            query_text=request.query,
            result_count=0,
            latency_ms=0,
            strategy="click",
        )
        entity_uuid = _parse_uuid(request.entity_id)
        if entity_uuid is None:
            logger.warning("Skipping search click with non-UUID entity_id: %s", request.entity_id)
            return

        chunk_uuid = None
        if request.entity_type == "chunk":
            chunk_uuid = _parse_uuid(request.chunk_id or request.entity_id)

        try:
            await repo.log_click(
                query_id=str(sq.query_id),
                tenant_id=self.tenant_id,
                result_position=request.result_position,
                entity_type=request.entity_type,
                entity_id=str(entity_uuid),
                chunk_id=str(chunk_uuid) if chunk_uuid else None,
                score=request.score,
            )
        except IntegrityError:
            # Best-effort analytics — don't fail the UI if FK constraints reject stale IDs.
            logger.warning(
                "Search click not persisted (entity_type=%s entity_id=%s chunk_id=%s)",
                request.entity_type,
                entity_uuid,
                chunk_uuid,
                exc_info=True,
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

    async def search_obligations(
        self, query: str, status: Optional[str] = None,
        contract_id: Optional[str] = None, page: int = 1, page_size: int = 20,
    ) -> dict:
        """Search across obligations by name, description, vendor, and contract name."""
        from sqlalchemy import text as sa_text

        conditions = ["o.tenant_id = :tenant_id"]
        bind = {"tenant_id": self.tenant_id, "query": f"%{query}%"}

        if status:
            conditions.append("o.status = :status")
            bind["status"] = status
        if contract_id:
            try:
                uuid.UUID(contract_id)
                conditions.append("o.contract_uuid_id = :contract_id")
                bind["contract_id"] = contract_id
            except ValueError:
                conditions.append("o.contract_id = :contract_id")
                bind["contract_id"] = contract_id

        where = " AND ".join(conditions)

        # Count
        count_sql = sa_text(f"""
            SELECT COUNT(*)::int FROM obligations o
            LEFT JOIN contract_reviews cr ON cr.review_id = o.contract_uuid_id
            WHERE {where}
              AND (o.name ILIKE :query OR o.description ILIKE :query
                   OR o.vendor ILIKE :query OR o.contract_name ILIKE :query
                   OR cr.metadata->>'contract_number' ILIKE :query)
        """)
        result = await self.session.execute(count_sql, bind)
        total = result.scalar() or 0

        # Fetch
        offset = (page - 1) * page_size
        data_sql = sa_text(f"""
            SELECT o.id, o.name, o.description, o.obligation_type, o.status,
                   o.contract_id, o.contract_uuid_id, o.contract_name, o.vendor,
                   o.owner, o.due_date, o.risk_level, o.risk_score,
                   o.created_at,
                   cr.metadata->>'contract_number' as contract_number
            FROM obligations o
            LEFT JOIN contract_reviews cr ON cr.review_id = o.contract_uuid_id
            WHERE {where}
              AND (o.name ILIKE :query OR o.description ILIKE :query
                   OR o.vendor ILIKE :query OR o.contract_name ILIKE :query
                   OR cr.metadata->>'contract_number' ILIKE :query)
            ORDER BY
                CASE WHEN o.name ILIKE :query THEN 0
                     WHEN cr.metadata->>'contract_number' ILIKE :query THEN 1
                     ELSE 2 END,
                o.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        bind["limit"] = page_size
        bind["offset"] = offset
        result = await self.session.execute(data_sql, bind)

        obligations = []
        for row in result.fetchall():
            obligations.append({
                "id": str(row.id),
                "name": row.name,
                "description": (row.description or "")[:200] + ("..." if row.description and len(row.description) > 200 else ""),
                "obligation_type": row.obligation_type,
                "status": row.status,
                "contract_id": row.contract_id,
                "contract_uuid_id": str(row.contract_uuid_id) if row.contract_uuid_id else None,
                "contract_name": row.contract_name,
                "vendor": row.vendor,
                "owner": row.owner,
                "due_date": row.due_date.isoformat() if row.due_date else None,
                "risk_level": row.risk_level,
                "risk_score": row.risk_score,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })

        return {
            "obligations": obligations,
            "total": total,
            "page": page,
            "page_size": page_size,
            "query": query,
        }

    @staticmethod
    def _cache_key(request: SearchRequest) -> str:
        """Generate deterministic cache key from request."""
        raw = f"{request.query}|{request.strategy}|{json.dumps(request.filters or {})}|{request.clause_type}|{request.contract_id}|{request.page}|{request.page_size}"
        return hashlib.sha256(raw.encode()).hexdigest()
