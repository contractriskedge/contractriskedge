"""Repository for clause recommendation rules — tenant-scoped CRUD."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.templates.recommendation_models import ClauseRecommendationRule

logger = logging.getLogger(__name__)


class RecommendationRuleRepository:
    """Data access for clause recommendation rules."""

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def create(self, rule: ClauseRecommendationRule) -> ClauseRecommendationRule:
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def get(self, rule_id: str) -> Optional[ClauseRecommendationRule]:
        result = await self.session.execute(
            select(ClauseRecommendationRule).where(
                ClauseRecommendationRule.id == rule_id,
                ClauseRecommendationRule.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
        variable_key: Optional[str] = None,
        clause_id: Optional[str] = None,
        template_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[list[ClauseRecommendationRule], int]:
        query = select(ClauseRecommendationRule).where(
            ClauseRecommendationRule.tenant_id == self.tenant_id,
        )

        if is_active is not None:
            query = query.where(ClauseRecommendationRule.is_active == is_active)
        if variable_key:
            query = query.where(ClauseRecommendationRule.variable_key == variable_key)
        if clause_id:
            query = query.where(ClauseRecommendationRule.clause_id == clause_id)
        if template_id:
            query = query.where(ClauseRecommendationRule.template_id == template_id)
        if search:
            like = f"%{search}%"
            query = query.where(
                ClauseRecommendationRule.name.ilike(like) |
                ClauseRecommendationRule.variable_key.ilike(like) |
                ClauseRecommendationRule.description.ilike(like)
            )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(
            ClauseRecommendationRule.priority.desc(),
            ClauseRecommendationRule.created_at.desc(),
        )
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def update(
        self,
        rule_id: str,
        updates: dict,
    ) -> Optional[ClauseRecommendationRule]:
        updates["updated_at"] = datetime.now(timezone.utc)
        stmt = (
            update(ClauseRecommendationRule)
            .where(
                ClauseRecommendationRule.id == rule_id,
                ClauseRecommendationRule.tenant_id == self.tenant_id,
            )
            .values(**updates)
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.get(rule_id)

    async def delete(self, rule_id: str) -> bool:
        stmt = delete(ClauseRecommendationRule).where(
            ClauseRecommendationRule.id == rule_id,
            ClauseRecommendationRule.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
