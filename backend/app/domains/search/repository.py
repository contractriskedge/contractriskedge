"""Search repository — query logging, click tracking, cache operations, and metrics."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.repository.base import BaseRepository
from app.domains.search.models import SearchQuery, SearchClick, SemanticCacheEntry


@dataclass
class SearchRepository(BaseRepository):

    async def log_query(
        self, tenant_id: str, user_id: Optional[str],
        query_text: str, result_count: int, latency_ms: int,
        strategy: str, filters: Optional[dict] = None,
    ) -> SearchQuery:
        sq = SearchQuery(
            tenant_id=tenant_id,
            user_id=user_id,
            query_text=query_text,
            normalized_query=query_text.lower().strip(),
            result_count=result_count,
            latency_ms=latency_ms,
            retrieval_strategy=strategy,
            filters=filters or {},
        )
        self.session.add(sq)
        await self.session.flush()
        return sq

    async def log_click(
        self, query_id: str, tenant_id: str,
        result_position: int, entity_type: str, entity_id: str,
        chunk_id: Optional[str] = None, score: Optional[float] = None,
    ) -> SearchClick:
        click = SearchClick(
            query_id=query_id,
            tenant_id=tenant_id,
            result_position=result_position,
            result_entity_type=entity_type,
            result_entity_id=entity_id,
            chunk_id=chunk_id,
            score=score,
        )
        self.session.add(click)
        await self.session.flush()
        return click

    # ── Semantic Cache ────────────────────────────────────────────

    async def cache_get(self, tenant_id: str, query_hash: str) -> Optional[dict]:
        stmt = select(SemanticCacheEntry).where(
            SemanticCacheEntry.tenant_id == tenant_id,
            SemanticCacheEntry.query_hash == query_hash,
            SemanticCacheEntry.expires_at > func.now(),
        )
        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry:
            entry.hit_count += 1
            entry.last_hit_at = func.now()
        return entry.results if entry else None

    async def cache_set(
        self, tenant_id: str, query_hash: str, query_text: str,
        results: list, ttl: int = 300,
    ) -> None:
        entry = SemanticCacheEntry(
            tenant_id=tenant_id,
            query_hash=query_hash,
            query_text=query_text,
            results=results,
            result_count=len(results),
            ttl_seconds=ttl,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl),
        )
        self.session.add(entry)
        await self.session.flush()

    async def cache_invalidate_tenant(self, tenant_id: str) -> None:
        stmt = text("DELETE FROM semantic_cache WHERE tenant_id = :tenant_id")
        await self.session.execute(stmt, {"tenant_id": tenant_id})

    # ── Query Analytics ───────────────────────────────────────────

    async def get_recent_queries(self, tenant_id: str, limit: int = 20):
        stmt = (
            select(SearchQuery)
            .where(SearchQuery.tenant_id == tenant_id)
            .order_by(SearchQuery.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_popular_queries(self, tenant_id: str, limit: int = 20):
        stmt = (
            select(SearchQuery.query_text, func.count().label("freq"))
            .where(SearchQuery.tenant_id == tenant_id)
            .group_by(SearchQuery.query_text)
            .order_by(func.count().desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.fetchall()

    async def get_zero_result_queries(self, tenant_id: str, limit: int = 20):
        stmt = (
            select(SearchQuery)
            .where(SearchQuery.tenant_id == tenant_id, SearchQuery.result_count == 0)
            .order_by(SearchQuery.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
