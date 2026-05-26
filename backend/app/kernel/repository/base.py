"""Base repository with tenant-safe query patterns.

CRITICAL: Every query MUST include tenant_id filter.
If tenant_id is missing, the repository returns 0 rows (fail-closed).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class BaseRepository:
    """Abstract base repository with common query patterns and tenant enforcement.

    All domain repositories should extend this class.
    tenant_id is injected by the dependency injection layer.
    """

    session: AsyncSession
    tenant_id: str

    async def execute(self, stmt):
        return await self.session.execute(stmt)

    async def scalar(self, stmt):
        result = await self.session.execute(stmt)
        return result.scalar()

    def filter_tenant(self, stmt, model) -> Any:
        """Add tenant_id filter to any query.

        FAIL-SAFE: If tenant_id is empty, returns a WHERE 1=0 clause
        instead of returning all rows.
        """
        if not self.tenant_id:
            return stmt.where(text("1=0"))
        return stmt.where(model.tenant_id == self.tenant_id)

    async def paginate(self, query, page: int = 1, page_size: int = 20):
        """Offset-based pagination with total count."""
        total = await self.scalar(
            select(func.count()).select_from(query.subquery())
        )
        result = await self.session.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total or 0

    async def paginate_keyset(self, query, cursor: Optional[str], limit: int = 20):
        """Keyset pagination for large datasets."""
        result = await self.session.execute(query.limit(limit))
        items = result.scalars().all()
        next_cursor = str(items[-1].id) if items else None
        return items, next_cursor
