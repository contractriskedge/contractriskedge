"""AI analysis repository — execution tracking, findings, redlines, cache persistence."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.repository.base import BaseRepository
from app.domains.ai.models import (
    AIExecutionRun, AIExecutionStep, AIFinding, AIRedline,
    ExecutionStatus, FindingSeverity, FindingType,
)
from app.domains.ai.schemas import AnalysisResult, RiskFinding, RedlineSuggestion


def _resolve_chunk_ids(chunks: Sequence, indices: list[int]) -> list[uuid.UUID]:
    """Map LLM chunk indices to persisted chunk UUIDs."""
    if not chunks:
        return []
    resolved: list[uuid.UUID] = []
    for idx in indices:
        if isinstance(idx, int) and 0 <= idx < len(chunks):
            chunk_id = chunks[idx].chunk_id
            resolved.append(chunk_id if isinstance(chunk_id, uuid.UUID) else uuid.UUID(str(chunk_id)))
    if not resolved and len(chunks) == 1:
        chunk_id = chunks[0].chunk_id
        resolved.append(chunk_id if isinstance(chunk_id, uuid.UUID) else uuid.UUID(str(chunk_id)))
    return resolved


def _resolve_page_numbers(chunks: Sequence, indices: list[int]) -> list[int]:
    pages: list[int] = []
    for idx in indices:
        if isinstance(idx, int) and 0 <= idx < len(chunks):
            for page in chunks[idx].page_numbers or []:
                if page not in pages:
                    pages.append(page)
    return pages


@dataclass
class AIRepository(BaseRepository):

    async def create_run(self, upload_id: str, tenant_id: str, analysis_type: str,
                          model: str, provider: str, user_id: Optional[str] = None) -> AIExecutionRun:
        run = AIExecutionRun(
            upload_id=upload_id, tenant_id=tenant_id, user_id=user_id,
            analysis_type=analysis_type, status=ExecutionStatus.PROCESSING,
            model=model, provider=provider, started_at=datetime.utcnow(),
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def complete_run(self, run_id: str, result: AnalysisResult,
                            tokens: dict, cost_usd: float, latency_ms: int) -> None:
        stmt = (
            update(AIExecutionRun).where(AIExecutionRun.run_id == run_id).values(
                status=ExecutionStatus.COMPLETED,
                risk_score=result.risk_score,
                findings_count=len(result.findings),
                redlines_count=len(result.redlines),
                prompt_tokens=tokens.get("prompt", 0),
                completion_tokens=tokens.get("completion", 0),
                total_tokens=tokens.get("total", 0),
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                completed_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)

    async def fail_run(self, run_id: str, error: str) -> None:
        stmt = (
            update(AIExecutionRun).where(AIExecutionRun.run_id == run_id).values(
                status=ExecutionStatus.FAILED, error_message=error,
            )
        )
        await self.session.execute(stmt)

    async def store_findings(
        self,
        run_id: str,
        upload_id: str,
        tenant_id: str,
        findings: list[RiskFinding],
        chunks: Sequence,
    ) -> list[AIFinding]:
        db_findings = []
        for f in findings:
            chunk_ids = _resolve_chunk_ids(chunks, f.chunk_indices)
            db = AIFinding(
                run_id=run_id, upload_id=upload_id, tenant_id=tenant_id,
                finding_type=FindingType.RISK,
                severity=f.severity, clause_type=f.clause_type,
                title=f.title, description=f.description,
                recommendation=f.recommendation,
                confidence=f.confidence, risk_score=f.risk_score,
                chunk_ids=chunk_ids,
                page_numbers=_resolve_page_numbers(chunks, f.chunk_indices),
            )
            self.session.add(db)
            db_findings.append(db)
        await self.session.flush()
        return db_findings

    async def store_redlines(
        self,
        run_id: str,
        upload_id: str,
        tenant_id: str,
        redlines: list[RedlineSuggestion],
        chunks: Sequence,
    ) -> list[AIRedline]:
        db_redlines = []
        for r in redlines:
            chunk_ids = _resolve_chunk_ids(chunks, r.chunk_indices)
            # Build metadata from traceability if present
            redline_metadata = None
            traceability = getattr(r, "traceability", None)
            if traceability:
                redline_metadata = {
                    "traceability": traceability.model_dump() if hasattr(traceability, "model_dump") else traceability,
                    "legal_domain": getattr(traceability, "legal_domain", None),
                    "risk_type": getattr(traceability, "risk_type", None),
                }
            db = AIRedline(
                run_id=run_id, upload_id=upload_id, tenant_id=tenant_id,
                clause_type=r.clause_type, original_text=r.original_text,
                proposed_text=r.proposed_text,
                operation=getattr(r, "operation", None),
                anchor_text=getattr(r, "anchor_text", None) or None,
                rationale=r.rationale,
                risk_level=r.risk_level, confidence=r.confidence,
                chunk_ids=chunk_ids,
                page_numbers=_resolve_page_numbers(chunks, r.chunk_indices),
                ai_metadata=redline_metadata,
            )
            self.session.add(db)
            db_redlines.append(db)
        await self.session.flush()
        return db_redlines

    async def get_run(self, run_id: str, tenant_id: str) -> Optional[AIExecutionRun]:
        stmt = select(AIExecutionRun).where(
            AIExecutionRun.run_id == run_id, AIExecutionRun.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_run_for_upload(self, upload_id: str, tenant_id: Optional[str] = None) -> Optional[AIExecutionRun]:
        """Get the most recent AI execution run for an upload."""
        stmt = select(AIExecutionRun).where(
            AIExecutionRun.upload_id == upload_id,
        )
        if tenant_id:
            stmt = stmt.where(AIExecutionRun.tenant_id == tenant_id)
        stmt = stmt.order_by(AIExecutionRun.created_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_runs_by_upload(self, upload_id: str, tenant_id: str) -> list[AIExecutionRun]:
        """List all AI execution runs for an upload, ordered by recency."""
        stmt = select(AIExecutionRun).where(
            AIExecutionRun.upload_id == upload_id,
            AIExecutionRun.tenant_id == tenant_id,
        ).order_by(AIExecutionRun.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_findings_by_run(self, run_id: str, tenant_id: str):
        stmt = select(AIFinding).where(
            AIFinding.run_id == run_id, AIFinding.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_redlines_by_run(self, run_id: str, tenant_id: str):
        stmt = select(AIRedline).where(
            AIRedline.run_id == run_id, AIRedline.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_tenant(self, tenant_id: str) -> int:
        stmt = select(func.count()).select_from(AIExecutionRun).where(
            AIExecutionRun.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
