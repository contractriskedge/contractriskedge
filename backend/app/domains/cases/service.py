"""Task/Case management service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.domains.cases.models import Case, Task, CaseComment
from app.domains.cases.repository import CaseRepository
from app.domains.cases.schemas import (
    CaseCreate, CaseUpdate, CaseResponse,
    TaskCreate, TaskUpdate, TaskResponse,
    CaseCommentCreate, CaseCommentResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class CaseService:
    repo: CaseRepository
    tenant_id: str
    user_id: str

    # ── Cases ─────────────────────────────────────────────────────

    async def create_case(self, body: CaseCreate) -> CaseResponse:
        case = await self.repo.create_case(
            tenant_id=self.tenant_id, created_by=self.user_id,
            **body.model_dump(exclude_none=True),
        )
        logger.info("Case created: %s — %s", case.case_id, body.title)
        return await self.get_case(str(case.case_id))

    async def get_case(self, case_id: str) -> Optional[CaseResponse]:
        case = await self.repo.get_case(case_id, self.tenant_id)
        if not case:
            return None
        tasks = await self.repo.list_tasks(case_id, self.tenant_id)
        return self._case_to_response(case, len(tasks))

    async def list_cases(self, status: Optional[str] = None,
                          assignee_id: Optional[str] = None) -> list[CaseResponse]:
        cases = await self.repo.list_cases(self.tenant_id, status, assignee_id)
        result = []
        for case in cases:
            tasks = await self.repo.list_tasks(str(case.case_id), self.tenant_id)
            result.append(self._case_to_response(case, len(tasks)))
        return result

    async def update_case(self, case_id: str, body: CaseUpdate) -> Optional[CaseResponse]:
        kwargs = {k: v for k, v in body.model_dump(exclude_none=True).items()}
        case = await self.repo.update_case(case_id, self.tenant_id, **kwargs)
        if not case:
            return None
        return await self.get_case(case_id)

    async def delete_case(self, case_id: str) -> bool:
        return await self.repo.delete_case(case_id, self.tenant_id)

    async def get_case_counts(self) -> dict[str, int]:
        return await self.repo.count_by_status(self.tenant_id)

    # ── Tasks ─────────────────────────────────────────────────────

    async def create_task(self, body: TaskCreate) -> TaskResponse:
        task = await self.repo.create_task(
            tenant_id=self.tenant_id, created_by=self.user_id,
            **body.model_dump(exclude_none=True),
        )
        return self._task_to_response(task)

    async def list_tasks(self, case_id: str) -> list[TaskResponse]:
        tasks = await self.repo.list_tasks(case_id, self.tenant_id)
        return [self._task_to_response(t) for t in tasks]

    async def update_task(self, task_id: str, body: TaskUpdate) -> Optional[TaskResponse]:
        kwargs = {k: v for k, v in body.model_dump(exclude_none=True).items()}
        task = await self.repo.update_task(task_id, self.tenant_id, **kwargs)
        return self._task_to_response(task) if task else None

    # ── Comments ──────────────────────────────────────────────────

    async def create_comment(self, body: CaseCommentCreate) -> CaseCommentResponse:
        comment = await self.repo.create_comment(
            tenant_id=self.tenant_id,
            case_id=body.case_id, author_id=self.user_id,
            body=body.body, mentions=body.mentions,
        )
        return self._comment_to_response(comment)

    async def list_comments(self, case_id: str) -> list[CaseCommentResponse]:
        comments = await self.repo.list_comments(case_id, self.tenant_id)
        return [self._comment_to_response(c) for c in comments]

    # ── Response Builders ─────────────────────────────────────────

    def _case_to_response(self, case: Case, task_count: int = 0) -> CaseResponse:
        return CaseResponse(
            case_id=str(case.case_id),
            title=case.title,
            description=case.description,
            status=case.status,
            priority=case.priority,
            severity=case.severity,
            contract_id=case.contract_id,
            review_id=str(case.review_id) if case.review_id else None,
            upload_id=str(case.upload_id) if case.upload_id else None,
            assignee_id=case.assignee_id,
            created_by=case.created_by,
            finding_ids=case.finding_ids or [],
            tags=case.tags or [],
            due_at=case.due_at,
            resolved_at=case.resolved_at,
            created_at=case.created_at,
            updated_at=case.updated_at,
            task_count=task_count,
        )

    @staticmethod
    def _task_to_response(task: Task) -> TaskResponse:
        return TaskResponse(
            task_id=str(task.task_id),
            case_id=str(task.case_id),
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            assignee_id=task.assignee_id,
            created_by=task.created_by,
            due_at=task.due_at,
            completed_at=task.completed_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    @staticmethod
    def _comment_to_response(comment: CaseComment) -> CaseCommentResponse:
        return CaseCommentResponse(
            comment_id=str(comment.comment_id),
            case_id=str(comment.case_id),
            author_id=comment.author_id,
            body=comment.body,
            mentions=comment.mentions or [],
            created_at=comment.created_at,
        )
