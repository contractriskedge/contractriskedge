"""Task/Case management repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, delete, func

from app.kernel.repository.base import BaseRepository
from app.domains.cases.models import Case, Task, CaseComment


@dataclass
class CaseRepository(BaseRepository):

    # ── Cases ─────────────────────────────────────────────────────

    async def create_case(self, tenant_id: str, created_by: str, **kwargs) -> Case:
        case = Case(tenant_id=tenant_id, created_by=created_by, **kwargs)
        self.session.add(case)
        await self.session.flush()
        return case

    async def get_case(self, case_id: str, tenant_id: str) -> Optional[Case]:
        stmt = select(Case).where(Case.case_id == case_id, Case.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_cases(self, tenant_id: str, status: Optional[str] = None,
                          assignee_id: Optional[str] = None, limit: int = 50) -> list[Case]:
        stmt = select(Case).where(Case.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Case.status == status)
        if assignee_id:
            stmt = stmt.where(Case.assignee_id == assignee_id)
        stmt = stmt.order_by(Case.updated_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_case(self, case_id: str, tenant_id: str, **kwargs) -> Optional[Case]:
        if "status" in kwargs and kwargs["status"] in ("resolved", "closed"):
            kwargs["resolved_at"] = func.now()
        stmt = (
            update(Case)
            .where(Case.case_id == case_id, Case.tenant_id == tenant_id)
            .values(**kwargs, updated_at=func.now())
        )
        await self.session.execute(stmt)
        return await self.get_case(case_id, tenant_id)

    async def delete_case(self, case_id: str, tenant_id: str) -> bool:
        stmt = delete(Case).where(Case.case_id == case_id, Case.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def count_by_status(self, tenant_id: str) -> dict[str, int]:
        stmt = select(Case.status, func.count().label("cnt")).where(
            Case.tenant_id == tenant_id
        ).group_by(Case.status)
        result = await self.session.execute(stmt)
        return {row.status: row.cnt for row in result.fetchall()}

    # ── Tasks ─────────────────────────────────────────────────────

    async def create_task(self, tenant_id: str, created_by: str, **kwargs) -> Task:
        task = Task(tenant_id=tenant_id, created_by=created_by, **kwargs)
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_task(self, task_id: str, tenant_id: str) -> Optional[Task]:
        stmt = select(Task).where(Task.task_id == task_id, Task.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tasks(self, case_id: str, tenant_id: str) -> list[Task]:
        stmt = (
            select(Task)
            .where(Task.case_id == case_id, Task.tenant_id == tenant_id)
            .order_by(Task.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_task(self, task_id: str, tenant_id: str, **kwargs) -> Optional[Task]:
        if "status" in kwargs and kwargs["status"] == "done":
            kwargs["completed_at"] = func.now()
        stmt = (
            update(Task)
            .where(Task.task_id == task_id, Task.tenant_id == tenant_id)
            .values(**kwargs, updated_at=func.now())
        )
        await self.session.execute(stmt)
        return await self.get_task(task_id, tenant_id)

    # ── Comments ──────────────────────────────────────────────────

    async def create_comment(self, tenant_id: str, **kwargs) -> CaseComment:
        comment = CaseComment(tenant_id=tenant_id, **kwargs)
        self.session.add(comment)
        await self.session.flush()
        return comment

    async def list_comments(self, case_id: str, tenant_id: str) -> list[CaseComment]:
        stmt = (
            select(CaseComment)
            .where(CaseComment.case_id == case_id, CaseComment.tenant_id == tenant_id)
            .order_by(CaseComment.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
