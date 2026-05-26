"""Workspace service — orchestrates dashboard views, action jobs, and recommendation feedback."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.domains.workspace.models import DashboardView, ActionJob, RecommendationFeedback
from app.domains.workspace.repository import WorkspaceRepository
from app.domains.workspace.schemas import (
    DashboardViewCreate, DashboardViewUpdate, DashboardViewResponse,
    ActionJobCreate, ActionJobResponse, ActionJobListResponse,
    RecommendationFeedbackCreate, RecommendationFeedbackResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceService:
    """Orchestrates workspace operations: views, jobs, feedback."""

    repo: WorkspaceRepository
    tenant_id: str
    user_id: str

    # ── Dashboard Views ───────────────────────────────────────────

    async def create_view(self, body: DashboardViewCreate) -> DashboardViewResponse:
        view = await self.repo.create_view(
            tenant_id=self.tenant_id, user_id=self.user_id,
            name=body.name, description=body.description,
            layout_json=body.layout_json, filters_json=body.filters_json,
            template_id=body.template_id,
        )
        return self._view_to_response(view)

    async def get_view(self, view_id: str) -> Optional[DashboardViewResponse]:
        view = await self.repo.get_view(view_id, self.tenant_id)
        return self._view_to_response(view) if view else None

    async def list_views(self) -> list[DashboardViewResponse]:
        views = await self.repo.list_views(self.tenant_id, self.user_id)
        return [self._view_to_response(v) for v in views]

    async def update_view(self, view_id: str, body: DashboardViewUpdate) -> Optional[DashboardViewResponse]:
        kwargs = {k: v for k, v in body.model_dump(exclude_none=True).items()}
        view = await self.repo.update_view(view_id, self.tenant_id, **kwargs)
        return self._view_to_response(view) if view else None

    async def delete_view(self, view_id: str) -> bool:
        return await self.repo.delete_view(view_id, self.tenant_id)

    # ── Action Jobs ───────────────────────────────────────────────

    async def create_job(self, body: ActionJobCreate) -> ActionJobResponse:
        job = await self.repo.create_job(
            tenant_id=self.tenant_id, user_id=self.user_id,
            action_type=body.action_type, target_type=body.target_type,
            target_ids=body.target_ids, metadata_json=body.metadata_json,
        )
        # In production, this would dispatch to a Celery worker
        logger.info("Action job created: %s (%s) for %d targets", job.action_type, job.target_type, len(job.target_ids))
        return self._job_to_response(job)

    async def get_job(self, job_id: str) -> Optional[ActionJobResponse]:
        job = await self.repo.get_job(job_id, self.tenant_id)
        return self._job_to_response(job) if job else None

    async def list_jobs(self) -> ActionJobListResponse:
        jobs = await self.repo.list_jobs(self.tenant_id, self.user_id)
        return ActionJobListResponse(
            jobs=[self._job_to_response(j) for j in jobs],
            total=len(jobs),
        )

    # ── Recommendation Feedback ───────────────────────────────────

    async def create_feedback(self, body: RecommendationFeedbackCreate) -> RecommendationFeedbackResponse:
        fb = await self.repo.create_feedback(
            tenant_id=self.tenant_id, user_id=self.user_id,
            recommendation_id=body.recommendation_id, status=body.status,
            snoozed_until=body.snoozed_until, note=body.note,
        )
        logger.info("Recommendation %s: %s", body.recommendation_id, body.status)
        return self._feedback_to_response(fb)

    async def get_feedback(self, recommendation_id: str) -> Optional[RecommendationFeedbackResponse]:
        fb = await self.repo.get_feedback(recommendation_id, self.tenant_id, self.user_id)
        return self._feedback_to_response(fb) if fb else None

    async def list_feedback(self) -> list[RecommendationFeedbackResponse]:
        items = await self.repo.list_feedback(self.tenant_id, self.user_id)
        return [self._feedback_to_response(fb) for fb in items]

    # ── Response Builders ─────────────────────────────────────────

    @staticmethod
    def _view_to_response(view: DashboardView) -> DashboardViewResponse:
        return DashboardViewResponse(
            view_id=str(view.view_id),
            name=view.name,
            description=view.description,
            layout_json=view.layout_json or {},
            filters_json=view.filters_json or {},
            template_id=view.template_id,
            created_at=view.created_at,
            updated_at=view.updated_at,
        )

    @staticmethod
    def _job_to_response(job: ActionJob) -> ActionJobResponse:
        return ActionJobResponse(
            job_id=str(job.job_id),
            action_type=job.action_type,
            status=job.status,
            target_type=job.target_type,
            target_ids=job.target_ids or [],
            progress=job.progress or 0,
            result_message=job.result_message,
            error_message=job.error_message,
            retry_count=job.retry_count or 0,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )

    @staticmethod
    def _feedback_to_response(fb: RecommendationFeedback) -> RecommendationFeedbackResponse:
        return RecommendationFeedbackResponse(
            feedback_id=str(fb.feedback_id),
            recommendation_id=fb.recommendation_id,
            status=fb.status,
            snoozed_until=fb.snoozed_until,
            note=fb.note,
            created_at=fb.created_at,
            updated_at=fb.updated_at,
        )
