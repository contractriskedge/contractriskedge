"""Workspace repository — dashboard views, action jobs, recommendation feedback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, delete, func

from app.kernel.repository.base import BaseRepository
from app.domains.workspace.models import DashboardView, ActionJob, RecommendationFeedback


@dataclass
class WorkspaceRepository(BaseRepository):

    # ── Dashboard Views ───────────────────────────────────────────

    async def create_view(
        self, tenant_id: str, user_id: str,
        name: str, description: Optional[str],
        layout_json: dict, filters_json: dict,
        template_id: Optional[str] = None,
    ) -> DashboardView:
        view = DashboardView(
            tenant_id=tenant_id, user_id=user_id,
            name=name, description=description,
            layout_json=layout_json, filters_json=filters_json,
            template_id=template_id,
        )
        self.session.add(view)
        await self.session.flush()
        return view

    async def get_view(self, view_id: str, tenant_id: str) -> Optional[DashboardView]:
        stmt = select(DashboardView).where(
            DashboardView.view_id == view_id,
            DashboardView.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_views(self, tenant_id: str, user_id: str) -> list[DashboardView]:
        stmt = (
            select(DashboardView)
            .where(
                DashboardView.tenant_id == tenant_id,
                DashboardView.user_id == user_id,
            )
            .order_by(DashboardView.updated_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_view(self, view_id: str, tenant_id: str, **kwargs) -> Optional[DashboardView]:
        stmt = (
            update(DashboardView)
            .where(DashboardView.view_id == view_id, DashboardView.tenant_id == tenant_id)
            .values(**kwargs, updated_at=func.now())
        )
        await self.session.execute(stmt)
        return await self.get_view(view_id, tenant_id)

    async def delete_view(self, view_id: str, tenant_id: str) -> bool:
        stmt = delete(DashboardView).where(
            DashboardView.view_id == view_id,
            DashboardView.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    # ── Action Jobs ───────────────────────────────────────────────

    async def create_job(
        self, tenant_id: str, user_id: str,
        action_type: str, target_type: str,
        target_ids: list[str], metadata_json: Optional[dict] = None,
    ) -> ActionJob:
        job = ActionJob(
            tenant_id=tenant_id, user_id=user_id,
            action_type=action_type, target_type=target_type,
            target_ids=target_ids, metadata_json=metadata_json,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_job(self, job_id: str, tenant_id: str) -> Optional[ActionJob]:
        stmt = select(ActionJob).where(
            ActionJob.job_id == job_id,
            ActionJob.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_jobs(self, tenant_id: str, user_id: str, limit: int = 50) -> list[ActionJob]:
        stmt = (
            select(ActionJob)
            .where(ActionJob.tenant_id == tenant_id, ActionJob.user_id == user_id)
            .order_by(ActionJob.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_job_status(
        self, job_id: str, tenant_id: str,
        status: str, progress: Optional[int] = None,
        result_message: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[ActionJob]:
        values = {"status": status}
        if progress is not None:
            values["progress"] = progress
        if result_message is not None:
            values["result_message"] = result_message
        if error_message is not None:
            values["error_message"] = error_message
        if status in ("running",):
            values["started_at"] = func.now()
        if status in ("completed", "failed"):
            values["completed_at"] = func.now()

        stmt = (
            update(ActionJob)
            .where(ActionJob.job_id == job_id, ActionJob.tenant_id == tenant_id)
            .values(**values)
        )
        await self.session.execute(stmt)
        return await self.get_job(job_id, tenant_id)

    # ── Recommendation Feedback ───────────────────────────────────

    async def create_feedback(
        self, tenant_id: str, user_id: str,
        recommendation_id: str, status: str,
        snoozed_until: Optional[datetime] = None,
        note: Optional[str] = None,
    ) -> RecommendationFeedback:
        fb = RecommendationFeedback(
            tenant_id=tenant_id, user_id=user_id,
            recommendation_id=recommendation_id, status=status,
            snoozed_until=snoozed_until, note=note,
        )
        self.session.add(fb)
        await self.session.flush()
        return fb

    async def get_feedback(
        self, recommendation_id: str, tenant_id: str, user_id: str,
    ) -> Optional[RecommendationFeedback]:
        stmt = select(RecommendationFeedback).where(
            RecommendationFeedback.recommendation_id == recommendation_id,
            RecommendationFeedback.tenant_id == tenant_id,
            RecommendationFeedback.user_id == user_id,
        ).order_by(RecommendationFeedback.created_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_feedback(self, tenant_id: str, user_id: str) -> list[RecommendationFeedback]:
        stmt = (
            select(RecommendationFeedback)
            .where(
                RecommendationFeedback.tenant_id == tenant_id,
                RecommendationFeedback.user_id == user_id,
            )
            .order_by(RecommendationFeedback.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
