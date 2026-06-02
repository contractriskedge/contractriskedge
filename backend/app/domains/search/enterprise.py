"""Enterprise Search Layer — semantic, keyword, clause, obligation, cross-contract, entity search.

Extends the existing HybridRetrievalEngine with:
- Clause similarity search — find similar clauses across contracts
- Obligation search — find obligations by type, party, status
- Cross-contract search — search across multiple contracts
- Legal entity search — find contracts by counterparty
- Renewal search — find upcoming renewals
- Metadata faceting — filter by contract type, jurisdiction, risk level
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.search.engine import HybridRetrievalEngine, RetrievedChunk, RetrievalResult

logger = logging.getLogger(__name__)


@dataclass
class SearchFilter:
    """Structured search filters for enterprise search."""
    contract_types: list[str] = field(default_factory=list)
    jurisdictions: list[str] = field(default_factory=list)
    risk_levels: list[str] = field(default_factory=list)
    clause_types: list[str] = field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None
    upload_ids: list[str] = field(default_factory=list)
    counterparty: str | None = None
    tags: list[str] = field(default_factory=list)
    only_active: bool = True


@dataclass
class FacetCount:
    """A facet value with count."""
    value: str
    count: int


@dataclass
class SearchFacets:
    """Faceted search results."""
    contract_types: list[FacetCount] = field(default_factory=list)
    clause_types: list[FacetCount] = field(default_factory=list)
    risk_levels: list[FacetCount] = field(default_factory=list)
    jurisdictions: list[FacetCount] = field(default_factory=list)
    counterparties: list[FacetCount] = field(default_factory=list)


@dataclass
class EnterpriseSearchResult:
    """Complete enterprise search result with facets."""
    results: list[RetrievedChunk]
    total: int
    query: str
    facets: SearchFacets = field(default_factory=SearchFacets)
    latency_ms: int = 0
    strategy: str = "hybrid"


@dataclass
class ClauseMatch:
    """A matched clause across contracts."""
    clause_id: str
    clause_type: str
    text: str
    contract_id: str
    contract_name: str
    upload_id: str
    similarity_score: float = 0.0
    page_numbers: list[int] = field(default_factory=list)


@dataclass
class ObligationMatch:
    """A matched obligation."""
    obligation_id: str
    description: str
    obligation_type: str
    party: str
    contract_id: str
    contract_name: str
    due_date: str | None = None
    status: str = "open"
    confidence: float = 0.0


@dataclass
class EntityMatch:
    """A matched legal entity or counterparty."""
    entity_id: str
    name: str
    entity_type: str
    contract_count: int = 0
    total_risk_score: float = 0.0
    active_obligations: int = 0
    upcoming_renewals: int = 0


@dataclass
class EnterpriseSearchService:
    """Enterprise search service building on HybridRetrievalEngine.

    Adds clause similarity, obligation search, cross-contract search,
    legal entity search, renewal search, and metadata faceting.
    """

    session: AsyncSession
    tenant_id: str

    async def search(
        self,
        query: str,
        filters: SearchFilter | None = None,
        page: int = 1,
        page_size: int = 20,
        include_facets: bool = True,
    ) -> EnterpriseSearchResult:
        """Execute an enterprise search with faceting."""
        engine = HybridRetrievalEngine(self.session, self.tenant_id)

        filter_dict = {}
        if filters:
            if filters.clause_types:
                filter_dict["clause_type"] = filters.clause_types
            if filters.contract_types:
                filter_dict["contract_type"] = filters.contract_types
            if filters.upload_ids:
                filter_dict["upload_ids"] = filters.upload_ids

        result = await engine.search(
            query=query,
            filters=filter_dict or None,
            clause_type=filters.clause_types[0] if filters and filters.clause_types else None,
            page=page,
            page_size=page_size,
        )

        facets = SearchFacets()
        if include_facets:
            facets = await self._compute_facets(query, filters)

        return EnterpriseSearchResult(
            results=result.results,
            total=result.total,
            query=query,
            facets=facets,
            latency_ms=result.latency_ms,
        )

    async def search_clauses(
        self,
        clause_type: str,
        query: str = "",
        limit: int = 20,
    ) -> list[ClauseMatch]:
        """Search for clauses by type across contracts."""
        sql = sa_text("""
            SELECT c.chunk_id, c.clause_type, c.text,
                   u.upload_id, u.filename as contract_name,
                   c.page_numbers
            FROM chunks c
            JOIN upload_sessions u ON u.upload_id = c.upload_id
            WHERE c.tenant_id = :tid
              AND c.clause_type = :ctype
              AND c.is_active = true
              AND (:q = '' OR c.text ILIKE :q_like)
            ORDER BY c.chunk_index
            LIMIT :lim
        """)
        result = await self.session.execute(sql, {
            "tid": self.tenant_id,
            "ctype": clause_type,
            "q": query,
            "q_like": f"%{query}%",
            "lim": limit,
        })
        return [
            ClauseMatch(
                clause_id=str(row.chunk_id),
                clause_type=row.clause_type,
                text=row.text[:500],
                contract_id=str(row.upload_id),
                contract_name=row.contract_name or "",
                upload_id=str(row.upload_id),
                page_numbers=row.page_numbers or [],
            )
            for row in result.fetchall()
        ]

    async def search_obligations(
        self,
        query: str = "",
        obligation_type: str | None = None,
        party: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[ObligationMatch]:
        """Search for obligations across contracts."""
        conditions = ["f.tenant_id = :tid", "f.finding_type = 'obligation'"]
        params: dict[str, Any] = {"tid": self.tenant_id, "q_like": f"%{query}%"}

        if query:
            conditions.append("(f.title ILIKE :q_like OR f.description ILIKE :q_like)")
        if obligation_type:
            conditions.append("f.clause_type = :otype")
            params["otype"] = obligation_type
        if status:
            conditions.append("f.status = :status")
            params["status"] = status

        where_clause = " AND ".join(conditions)

        sql = sa_text(f"""
            SELECT f.finding_id, f.title, f.description, f.clause_type,
                   f.risk_score, f.confidence, f.status,
                   u.upload_id, u.filename as contract_name
            FROM ai_findings f
            JOIN upload_sessions u ON u.upload_id = f.upload_id
            WHERE {where_clause}
            ORDER BY f.created_at DESC
            LIMIT :lim
        """)
        params["lim"] = limit
        result = await self.session.execute(sql, params)
        return [
            ObligationMatch(
                obligation_id=str(row.finding_id),
                description=row.description or "",
                obligation_type=row.clause_type or "",
                party="",
                contract_id=str(row.upload_id),
                contract_name=row.contract_name or "",
                status=row.status or "open",
                confidence=row.confidence or 0.0,
            )
            for row in result.fetchall()
        ]

    async def search_entities(
        self,
        query: str,
        limit: int = 20,
    ) -> list[EntityMatch]:
        """Search for legal entities/counterparties."""
        sql = sa_text("""
            SELECT
                u.upload_id as entity_id,
                u.filename as name,
                COUNT(*) as contract_count,
                AVG(COALESCE(ar.risk_score, 0)) as avg_risk_score,
                COUNT(*) FILTER (WHERE af.status = 'open') as active_obligations
            FROM upload_sessions u
            LEFT JOIN ai_execution_runs ar ON ar.upload_id = u.upload_id
            LEFT JOIN ai_findings af ON af.upload_id = u.upload_id AND af.finding_type = 'obligation'
            WHERE u.tenant_id = :tid
              AND (u.filename ILIKE :q OR (u.metadata->>'counterparty') ILIKE :q)
            GROUP BY u.upload_id, u.filename
            ORDER BY contract_count DESC
            LIMIT :lim
        """)
        result = await self.session.execute(sql, {
            "tid": self.tenant_id,
            "q": f"%{query}%",
            "lim": limit,
        })
        return [
            EntityMatch(
                entity_id=str(row.entity_id),
                name=row.name,
                entity_type="counterparty",
                contract_count=row.contract_count or 0,
                total_risk_score=round(float(row.avg_risk_score or 0.0), 2),
                active_obligations=row.active_obligations or 0,
            )
            for row in result.fetchall()
        ]

    async def search_renewals(
        self,
        days_ahead: int = 90,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for upcoming contract renewals."""
        conditions = ["tenant_id = :tid"]
        params: dict[str, Any] = {"tid": self.tenant_id, "days": days_ahead}

        if status:
            conditions.append("status = :status")
            params["status"] = status

        where = " AND ".join(conditions)
        sql = sa_text(f"""
            SELECT upload_id, filename, created_at,
                   metadata->>'renewal_date' as renewal_date,
                   metadata->>'contract_type' as contract_type,
                   metadata->>'counterparty' as counterparty,
                   status
            FROM upload_sessions
            WHERE {where}
              AND (metadata->>'renewal_date')::date BETWEEN CURRENT_DATE AND CURRENT_DATE + :days
            ORDER BY (metadata->>'renewal_date')::date ASC
            LIMIT :lim
        """)
        params["lim"] = limit
        result = await self.session.execute(sql, params)
        return [
            {
                "upload_id": str(row.upload_id),
                "contract_name": row.filename,
                "contract_type": row.contract_type,
                "counterparty": row.counterparty,
                "renewal_date": row.renewal_date,
                "status": row.status,
                "days_until_renewal": (
                    (datetime.strptime(row.renewal_date, "%Y-%m-%d") - datetime.utcnow()).days
                    if row.renewal_date else None
                ),
            }
            for row in result.fetchall()
        ]

    async def _compute_facets(
        self, query: str, filters: SearchFilter | None
    ) -> SearchFacets:
        """Compute search facets for the current query."""
        facets = SearchFacets()

        # Clause type facets
        sql = sa_text("""
            SELECT clause_type, COUNT(*) as count
            FROM chunks
            WHERE tenant_id = :tid AND is_active = true AND clause_type IS NOT NULL
            GROUP BY clause_type
            ORDER BY count DESC
            LIMIT 20
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        facets.clause_types = [
            FacetCount(value=str(row.clause_type), count=row.count)
            for row in result.fetchall()
        ]

        # Contract type facets
        sql = sa_text("""
            SELECT metadata->>'contract_type' as contract_type, COUNT(*) as count
            FROM upload_sessions
            WHERE tenant_id = :tid AND is_active = true
              AND metadata->>'contract_type' IS NOT NULL
            GROUP BY metadata->>'contract_type'
            ORDER BY count DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        facets.contract_types = [
            FacetCount(value=str(row.contract_type), count=row.count)
            for row in result.fetchall()
        ]

        return facets


from datetime import datetime
