"""AI Execution Explorer — execution traceability, retrieval inspection, replay comparison, audit visualization.

One of the most valuable enterprise tools for:
- Debugging AI behavior
- Building trust with reviewers
- Supporting audits
- Customer support investigations
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ExecutionTraceEvent:
    """A single event in an execution trace timeline."""
    timestamp: str
    event_type: str
    component: str
    duration_ms: int = 0
    status: str = "success"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionTrace:
    """Complete execution trace with timeline and metadata."""
    execution_id: str
    tenant_id: str
    operation_type: str
    status: str
    trace_events: list[ExecutionTraceEvent] = field(default_factory=list)
    total_duration_ms: int = 0
    prompt_version: str = ""
    provider: str = ""
    model: str = ""
    total_tokens: int = 0
    cost_usd: float = 0.0
    confidence: float = 0.0
    error_message: str | None = None
    retrieval_chunks: list[dict[str, Any]] = field(default_factory=list)
    guardrail_decisions: list[dict[str, Any]] = field(default_factory=list)
    replay_comparison: dict[str, Any] | None = None


@dataclass
class AIExecutionExplorer:
    """Explorer for AI execution traces — provides full visibility into AI decisions.

    Capabilities:
    - Trace execution timeline (policy → retrieval → guardrails → provider → validation)
    - View retrieval chunks with scores
    - Compare replay results side-by-side
    - Inspect guardrail decisions
    - Inspect provider routing decisions
    - Show prompt version and template
    - Show token/cost metrics
    - Visualize event chain
    """

    session: AsyncSession

    async def get_execution_trace(self, execution_id: str, tenant_id: str) -> ExecutionTrace:
        """Get a complete execution trace for an AI execution.

        Args:
            execution_id: The AI execution run ID.
            tenant_id: Tenant context for isolation.

        Returns:
            ExecutionTrace with full timeline and metadata.
        """
        # Load execution run
        sql = sa_text("""
            SELECT run_id, upload_id, tenant_id, analysis_type, status,
                   model, provider, prompt_version, analysis_prompt_version,
                   execution_context, total_tokens, cost_usd,
                   latency_ms, risk_score, findings_count,
                   error_message, started_at, completed_at
            FROM ai_execution_runs
            WHERE run_id = :eid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"eid": execution_id, "tid": tenant_id})
        row = result.fetchone()

        if not row:
            raise ValueError(f"Execution {execution_id} not found for tenant {tenant_id[:8]}")

        exec_context = row.execution_context or {}
        trace = ExecutionTrace(
            execution_id=str(row.run_id),
            tenant_id=str(row.tenant_id),
            operation_type=row.analysis_type,
            status=row.status,
            prompt_version=str(row.prompt_version or "") if row.prompt_version else "",
            provider=row.provider,
            model=row.model,
            total_tokens=row.total_tokens or 0,
            cost_usd=row.cost_usd or 0.0,
            confidence=row.risk_score or 0.0,
            error_message=row.error_message,
            total_duration_ms=row.latency_ms or 0,
        )

        # Build timeline from execution context
        trace.trace_events = self._build_timeline(exec_context, row)

        # Load retrieval chunks
        trace.retrieval_chunks = await self._get_retrieval_chunks(execution_id, tenant_id)

        # Load guardrail decisions
        trace.guardrail_decisions = await self._get_guardrail_decisions(execution_id, tenant_id)

        # Load execution steps
        steps = await self._get_execution_steps(execution_id, tenant_id)
        for step in steps:
            trace.trace_events.append(ExecutionTraceEvent(
                timestamp=str(step.get("created_at", "")),
                event_type=f"step:{step.get('step_type', 'unknown')}",
                component="execution_step",
                duration_ms=step.get("latency_ms", 0) or 0,
                status=step.get("status", "unknown"),
                details={
                    "step_type": step.get("step_type"),
                    "confidence": step.get("confidence"),
                    "tokens": (step.get("prompt_tokens", 0) or 0) + (step.get("completion_tokens", 0) or 0),
                },
            ))

        return trace

    def _build_timeline(self, exec_context: dict, run_row) -> list[ExecutionTraceEvent]:
        """Build execution timeline from context metadata."""
        events = []

        # Policy check
        events.append(ExecutionTraceEvent(
            timestamp=str(run_row.started_at) if run_row.started_at else "",
            event_type="policy_check",
            component="policy_engine",
            status="completed",
            details={
                "rules_applied": exec_context.get("policy_rules", []),
                "tenant_tier": exec_context.get("tenant_tier", ""),
            },
        ))

        # Retrieval
        events.append(ExecutionTraceEvent(
            timestamp=str(run_row.started_at) if run_row.started_at else "",
            event_type="retrieval",
            component="hybrid_retrieval_engine",
            status="completed",
            details={
                "strategy": exec_context.get("retrieval_strategy", "hybrid"),
                "chunks_retrieved": exec_context.get("chunks_retrieved", 0),
            },
        ))

        # Guardrail check
        events.append(ExecutionTraceEvent(
            timestamp=str(run_row.started_at) if run_row.started_at else "",
            event_type="guardrail_check",
            component="guardrail_engine",
            status="completed",
            details={
                "rules_evaluated": exec_context.get("guardrail_rules", []),
                "violations": exec_context.get("guardrail_violations", 0),
            },
        ))

        # Provider execution
        events.append(ExecutionTraceEvent(
            timestamp=str(run_row.started_at) if run_row.started_at else "",
            event_type="provider_execution",
            component=f"provider:{run_row.provider}",
            duration_ms=run_row.latency_ms or 0,
            status="completed" if run_row.status == "completed" else "failed",
            details={
                "model": run_row.model,
                "prompt_tokens": exec_context.get("prompt_tokens", 0),
                "completion_tokens": exec_context.get("completion_tokens", 0),
            },
        ))

        # Validation
        if run_row.status == "completed":
            events.append(ExecutionTraceEvent(
                timestamp=str(run_row.completed_at) if run_row.completed_at else "",
                event_type="validation",
                component="llm_response_validator",
                status="completed",
                details={
                    "risk_score": run_row.risk_score,
                    "findings_count": run_row.findings_count,
                },
            ))

        return events

    async def _get_retrieval_chunks(self, execution_id: str, tenant_id: str) -> list[dict[str, Any]]:
        """Get retrieval chunks used in an execution."""
        sql = sa_text("""
            SELECT c.chunk_id, c.chunk_index, c.text, c.page_numbers,
                   c.section_heading, c.clause_type, c.token_count,
                   rsc.rank, rsc.similarity_score, rsc.rerank_score
            FROM retrieval_snapshot_chunks rsc
            JOIN retrieval_snapshots rs ON rs.snapshot_id = rsc.snapshot_id
            JOIN chunks c ON c.chunk_id = rsc.chunk_id
            WHERE rs.execution_id = :eid AND rs.tenant_id = :tid
            ORDER BY rsc.rank ASC
            LIMIT 20
        """)
        try:
            result = await self.session.execute(sql, {"eid": execution_id, "tid": tenant_id})
            return [
                {
                    "chunk_id": str(row.chunk_id)[:8],
                    "rank": row.rank,
                    "text_preview": (row.text or "")[:200],
                    "page_numbers": row.page_numbers or [],
                    "section_heading": row.section_heading,
                    "clause_type": row.clause_type,
                    "token_count": row.token_count or 0,
                    "similarity_score": row.similarity_score,
                    "rerank_score": row.rerank_score,
                }
                for row in result.fetchall()
            ]
        except Exception:
            return []

    async def _get_guardrail_decisions(self, execution_id: str, tenant_id: str) -> list[dict[str, Any]]:
        """Get guardrail decisions for an execution."""
        sql = sa_text("""
            SELECT rule_id, message, severity, created_at
            FROM ai_guardrail_violations
            WHERE run_id = :eid AND tenant_id = :tid
            ORDER BY created_at ASC
        """)
        try:
            result = await self.session.execute(sql, {"eid": execution_id, "tid": tenant_id})
            return [
                {
                    "rule_id": row.rule_id,
                    "message": row.message,
                    "severity": row.severity,
                    "timestamp": str(row.created_at),
                }
                for row in result.fetchall()
            ]
        except Exception:
            return []

    async def _get_execution_steps(self, execution_id: str, tenant_id: str) -> list[dict[str, Any]]:
        """Get execution steps for an AI run."""
        sql = sa_text("""
            SELECT step_type, status, confidence, latency_ms,
                   prompt_tokens, completion_tokens, error_message, created_at
            FROM ai_execution_steps
            WHERE run_id = :eid AND tenant_id = :tid
            ORDER BY step_order ASC
        """)
        try:
            result = await self.session.execute(sql, {"eid": execution_id, "tid": tenant_id})
            return [
                {
                    "step_type": row.step_type,
                    "status": row.status,
                    "confidence": row.confidence,
                    "latency_ms": row.latency_ms,
                    "prompt_tokens": row.prompt_tokens,
                    "completion_tokens": row.completion_tokens,
                    "error_message": row.error_message,
                    "created_at": str(row.created_at),
                }
                for row in result.fetchall()
            ]
        except Exception:
            return []

    async def compare_with_replay(
        self,
        execution_id: str,
        tenant_id: str,
        replay_run_id: str | None = None,
    ) -> dict[str, Any]:
        """Compare an execution with its replay."""
        from app.domains.ai.replay import ReplayAIExecutionService

        service = ReplayAIExecutionService(self.session, tenant_id)

        if replay_run_id:
            comparison = await service.compare_versions(execution_id, replay_run_id)
        else:
            comparison = await service.detect_drift(execution_id)

        if not comparison:
            return {"error": "No replay comparison available"}

        return comparison.to_dict()

    async def get_execution_summary(self, execution_id: str, tenant_id: str) -> dict[str, Any]:
        """Get a concise execution summary for the explorer UI."""
        trace = await self.get_execution_trace(execution_id, tenant_id)

        return {
            "execution_id": trace.execution_id,
            "operation_type": trace.operation_type,
            "status": trace.status,
            "provider": trace.provider,
            "model": trace.model,
            "prompt_version": trace.prompt_version,
            "total_duration_ms": trace.total_duration_ms,
            "total_tokens": trace.total_tokens,
            "cost_usd": round(trace.cost_usd, 6),
            "confidence": trace.confidence,
            "error": trace.error_message,
            "timeline_events": [
                {
                    "event_type": e.event_type,
                    "component": e.component,
                    "duration_ms": e.duration_ms,
                    "status": e.status,
                }
                for e in trace.trace_events
            ],
            "retrieval_chunks_count": len(trace.retrieval_chunks),
            "guardrail_decisions_count": len(trace.guardrail_decisions),
            "has_replay": trace.replay_comparison is not None,
        }
