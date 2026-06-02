"""Deterministic replay engine for AI execution reproducibility and audit.

This module enables:
- Replaying historical AI runs with identical context
- Comparing old vs new outputs for drift detection
- Reproducing audit history for compliance
- Debugging prompt/retrieval changes
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from enum import Enum
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.models import AIExecutionRun, AIExecutionStep, ExecutionStatus
from app.domains.ai.repository import AIRepository
from app.domains.ai.snapshots.service import RetrievalSnapshotService
from app.domains.ai.snapshots.models import RetrievalSnapshot
from app.domains.ai.prompts import PromptRegistry, PromptTemplate
from app.domains.ai.orchestration.envelope import AIRequestEnvelope
from app.domains.ai.orchestration.orchestrator import AIExecutionOrchestrator
from app.domains.ai.orchestration.plan import AIExecutionPlan
from app.domains.ai.types import AIExecutionOutcome

logger = logging.getLogger(__name__)


class DriftSeverity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ReplayComparison:
    """Result of comparing original vs replayed execution outputs."""
    execution_id: str
    original_run_id: str
    replay_run_id: str

    # Overall drift assessment
    drift_detected: bool = False
    drift_severity: DriftSeverity = DriftSeverity.NONE
    drift_score: float = 0.0  # 0.0 = identical, 1.0 = completely different

    # Finding-level comparison
    original_findings_count: int = 0
    replay_findings_count: int = 0
    findings_overlap: float = 0.0  # Jaccard similarity
    new_findings: list[dict[str, Any]] = field(default_factory=list)
    missing_findings: list[dict[str, Any]] = field(default_factory=list)
    changed_findings: list[dict[str, Any]] = field(default_factory=list)

    # Score comparison
    original_risk_score: float | None = None
    replay_risk_score: float | None = None
    risk_score_delta: float = 0.0

    # Performance comparison
    original_latency_ms: int = 0
    replay_latency_ms: int = 0
    latency_delta_ms: int = 0

    original_tokens: int = 0
    replay_tokens: int = 0
    token_delta: int = 0

    original_cost: float = 0.0
    replay_cost: float = 0.0
    cost_delta: float = 0.0

    # Metadata
    replayed_at: str = ""
    prompt_version_changed: bool = False
    retrieval_snapshot_matched: bool = False
    provider_changed: bool = False
    model_changed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "original_run_id": self.original_run_id,
            "replay_run_id": self.replay_run_id,
            "drift_detected": self.drift_detected,
            "drift_severity": self.drift_severity.value,
            "drift_score": round(self.drift_score, 4),
            "original_findings_count": self.original_findings_count,
            "replay_findings_count": self.replay_findings_count,
            "findings_overlap": round(self.findings_overlap, 4),
            "new_findings_count": len(self.new_findings),
            "missing_findings_count": len(self.missing_findings),
            "changed_findings_count": len(self.changed_findings),
            "original_risk_score": self.original_risk_score,
            "replay_risk_score": self.replay_risk_score,
            "risk_score_delta": round(self.risk_score_delta, 4),
            "original_latency_ms": self.original_latency_ms,
            "replay_latency_ms": self.replay_latency_ms,
            "latency_delta_ms": self.latency_delta_ms,
            "original_tokens": self.original_tokens,
            "replay_tokens": self.replay_tokens,
            "token_delta": self.token_delta,
            "original_cost": round(self.original_cost, 6),
            "replay_cost": round(self.replay_cost, 6),
            "cost_delta": round(self.cost_delta, 6),
            "replayed_at": self.replayed_at,
            "prompt_version_changed": self.prompt_version_changed,
            "retrieval_snapshot_matched": self.retrieval_snapshot_matched,
            "provider_changed": self.provider_changed,
            "model_changed": self.model_changed,
        }


@dataclass
class ReplayResult:
    """Result of a replay execution."""
    replay_run_id: str
    execution_id: str
    outcome: AIExecutionOutcome
    comparison: ReplayComparison | None = None
    error: str | None = None


@dataclass
class ReplayAIExecutionService:
    """Deterministic replay engine for AI execution reproducibility.

    Capabilities:
    - Replay historical AI runs with exact provider/model/prompt
    - Replay with exact retrieval snapshot chunks
    - Compare old vs new outputs with drift detection
    - Reproduce audit history for compliance
    """

    session: AsyncSession
    tenant_id: str
    ai_repository: AIRepository | None = None
    snapshot_service: RetrievalSnapshotService | None = None

    def __post_init__(self):
        if self.ai_repository is None:
            self.ai_repository = AIRepository(self.session)
        if self.snapshot_service is None:
            self.snapshot_service = RetrievalSnapshotService(self.session, self.tenant_id)

    # ── Core Replay ────────────────────────────────────────────────

    async def replay_execution(
        self,
        original_run_id: str,
        compare: bool = True,
        use_exact_snapshot: bool = True,
        provider_override: str | None = None,
        model_override: str | None = None,
        prompt_version_override: str | None = None,
    ) -> ReplayResult:
        """Replay a historical AI execution.

        Args:
            original_run_id: The run_id of the execution to replay.
            compare: Whether to compare original vs replayed outputs.
            use_exact_snapshot: Whether to use the original retrieval snapshot.
            provider_override: Override the provider used.
            model_override: Override the model used.
            prompt_version_override: Override the prompt version.

        Returns:
            ReplayResult with the replay outcome and optional comparison.
        """
        # 1. Load the original execution
        original_run = await self._load_original_run(original_run_id)
        if not original_run:
            return ReplayResult(
                replay_run_id="",
                execution_id="",
                outcome=None,  # type: ignore
                error=f"Original run {original_run_id} not found",
            )

        execution_id = str(original_run.run_id)
        logger.info(
            "Replaying execution %s (original: run=%s provider=%s model=%s)",
            execution_id, original_run_id,
            original_run.provider, original_run.model,
        )

        # 2. Resolve the execution context
        exec_context = original_run.execution_context or {}
        provider = provider_override or original_run.provider
        model = model_override or original_run.model
        prompt_version = prompt_version_override or str(original_run.prompt_version or 1)

        # 3. Load retrieval snapshot if requested
        retrieval_context: dict[str, Any] = {}
        snapshot_matched = False
        if use_exact_snapshot:
            snapshot = await self.snapshot_service.get_snapshot_by_execution(execution_id)
            if snapshot:
                snapshot_chunks = await self.snapshot_service.get_snapshot_chunks(
                    str(snapshot.snapshot_id)
                )
                retrieval_context = {
                    "snapshot_id": str(snapshot.snapshot_id),
                    "chunks": [
                        {
                            "chunk_id": str(c.chunk_id),
                            "chunk_index": c.chunk_index,
                            "text": c.text,
                            "page_numbers": c.page_numbers,
                            "section_heading": c.section_heading,
                            "clause_type": c.clause_type,
                            "token_count": c.token_count,
                            "rank": c.rank,
                            "similarity_score": c.similarity_score,
                        }
                        for c in snapshot_chunks
                    ],
                    "embedding_model": snapshot.embedding_model,
                    "embedding_model_version": snapshot.embedding_model_version,
                    "reranker_model": snapshot.reranker_model,
                    "vector_collection_version": snapshot.vector_collection_version,
                }
                snapshot_matched = True
                logger.info(
                    "Loaded retrieval snapshot %s with %d chunks for replay",
                    snapshot.snapshot_id, len(snapshot_chunks),
                )

        # 4. Build the replay envelope
        envelope = AIRequestEnvelope(
            tenant_id=self.tenant_id,
            user_id=original_run.user_id,
            contract_id=exec_context.get("contract_id"),
            upload_id=str(original_run.upload_id),
            operation_type=original_run.analysis_type,
            execution_plan=self._build_replay_plan(
                original_run, provider, model, exec_context,
            ),
            retrieval_context=retrieval_context,
            audit_context={
                "prompt_text": exec_context.get("prompt_text", ""),
                "system_prompt": exec_context.get("system_prompt"),
                "user_role": exec_context.get("user_role"),
                "source": "replay_engine",
                "original_run_id": original_run_id,
            },
            trace_id=str(uuid.uuid4()),
            execution_id=str(uuid.uuid4()),
            correlation_id=exec_context.get("correlation_id"),
            request_chain_id=exec_context.get("request_chain_id"),
            metadata={
                "replay": True,
                "original_run_id": original_run_id,
                "provider_override": provider_override is not None,
                "model_override": model_override is not None,
                "prompt_version_override": prompt_version_override is not None,
                "use_exact_snapshot": use_exact_snapshot,
            },
        )

        # 5. Execute replay
        start_time = time.monotonic()
        try:
            orchestrator = AIExecutionOrchestrator(
                self.session, self.tenant_id, original_run.user_id,
            )
            outcome = await orchestrator.execute(envelope)
            replay_latency = int((time.monotonic() - start_time) * 1000)
        except Exception as exc:
            logger.error("Replay execution failed: %s", exc)
            return ReplayResult(
                replay_run_id="",
                execution_id=execution_id,
                outcome=None,  # type: ignore
                error=str(exc),
            )

        # 6. Compare if requested
        comparison = None
        if compare:
            comparison = await self._compare_outputs(
                original_run, outcome, original_run_id,
                snapshot_matched, provider_override, model_override,
            )

        logger.info(
            "Replay complete: execution=%s drift=%s severity=%s",
            execution_id,
            comparison.drift_detected if comparison else "N/A",
            comparison.drift_severity if comparison else "N/A",
        )

        return ReplayResult(
            replay_run_id=outcome.trace_id or "",
            execution_id=execution_id,
            outcome=outcome,
            comparison=comparison,
        )

    # ── Drift Detection ────────────────────────────────────────────

    async def compare_versions(
        self,
        run_id_a: str,
        run_id_b: str,
    ) -> ReplayComparison:
        """Compare two historical AI execution runs for drift."""
        run_a = await self._load_original_run(run_id_a)
        run_b = await self._load_original_run(run_id_b)

        if not run_a or not run_b:
            raise ValueError(f"One or both runs not found: {run_id_a}, {run_id_b}")

        return self._compute_comparison(
            run_a=run_a,
            run_b=run_b,
            original_run_id=run_id_a,
            replay_run_id=run_id_b,
            snapshot_matched=False,
            provider_changed=run_a.provider != run_b.provider,
            model_changed=run_a.model != run_b.model,
        )

    async def detect_drift(
        self,
        run_id: str,
        baseline_run_id: str | None = None,
    ) -> ReplayComparison | None:
        """Detect drift between a run and its baseline.

        If no baseline is provided, uses the first completed run for the same upload.
        """
        run = await self._load_original_run(run_id)
        if not run:
            return None

        if baseline_run_id:
            baseline = await self._load_original_run(baseline_run_id)
        else:
            # Find the first completed run for this upload
            stmt = (
                select(AIExecutionRun)
                .where(
                    AIExecutionRun.upload_id == run.upload_id,
                    AIExecutionRun.tenant_id == self.tenant_id,
                    AIExecutionRun.status == ExecutionStatus.COMPLETED,
                )
                .order_by(AIExecutionRun.created_at.asc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            baseline = result.scalar_one_or_none()

        if not baseline or str(baseline.run_id) == run_id:
            return None

        return self._compute_comparison(
            run_a=baseline,
            run_b=run,
            original_run_id=str(baseline.run_id),
            replay_run_id=str(run.run_id),
            snapshot_matched=False,
            provider_changed=baseline.provider != run.provider,
            model_changed=baseline.model != run.model,
        )

    # ── Internal Helpers ───────────────────────────────────────────

    async def _load_original_run(self, run_id: str) -> AIExecutionRun | None:
        """Load an original AI execution run."""
        stmt = select(AIExecutionRun).where(
            AIExecutionRun.run_id == run_id,
            AIExecutionRun.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _build_replay_plan(
        self,
        original_run: AIExecutionRun,
        provider: str,
        model: str,
        exec_context: dict[str, Any],
    ) -> AIExecutionPlan:
        """Build an execution plan for replay from original run metadata."""
        from app.domains.ai.orchestration.plan import (
            AIExecutionPlan, RetryPolicy, TimeoutPolicy,
            GuardrailProfile, RetrievalStrategy, FallBackChain,
        )
        from app.domains.ai.providers.capabilities import ProviderCapabilities

        return AIExecutionPlan(
            provider_name=provider,
            model=model,
            temperature=exec_context.get("temperature", 0.1),
            token_budget=exec_context.get("max_tokens", 4096),
            retry_policy=RetryPolicy(
                max_attempts=exec_context.get("retry_attempts", 3),
                backoff_seconds=exec_context.get("retry_backoff", 2.0),
            ),
            timeout_policy=TimeoutPolicy(
                request_timeout_seconds=exec_context.get("request_timeout", 60),
            ),
            guardrail_profile=GuardrailProfile(
                profile_id=exec_context.get("guardrail_profile_id", "default"),
                enforcement_level=exec_context.get("guardrail_enforcement", "strict"),
            ),
            policy_pack_version=exec_context.get("policy_pack_version", "1.0.0"),
            retrieval_strategy=RetrievalStrategy(
                name=exec_context.get("retrieval_strategy", "semantic_search"),
                max_documents=exec_context.get("max_documents", 10),
                rerank=exec_context.get("rerank", True),
            ),
            fallback_chain=FallBackChain(
                providers=exec_context.get("fallback_providers", [provider]),
            ),
            provider_capabilities=ProviderCapabilities(
                provider_name=provider,
                supports_json_mode=True,
                max_context_tokens=exec_context.get("max_context_tokens", 128000),
            ),
            prompt_template_version=original_run.prompt_version or 1,
            operation_type=original_run.analysis_type,
            metadata={"replay": True, "original_run_id": str(original_run.run_id)},
        )

    async def _compare_outputs(
        self,
        original_run: AIExecutionRun,
        replay_outcome: AIExecutionOutcome,
        original_run_id: str,
        snapshot_matched: bool,
        provider_overridden: bool,
        model_overridden: bool,
    ) -> ReplayComparison:
        """Compare original and replayed outputs."""
        # Load original findings
        repo = self.ai_repository or AIRepository(self.session)
        original_findings = await repo.get_findings_by_run(
            original_run_id, self.tenant_id,
        )

        # Parse replay response
        import json as json_lib
        replay_content = replay_outcome.response.content if replay_outcome.response else "{}"
        replay_parsed = {}
        try:
            replay_parsed = json_lib.loads(replay_content)
        except (json_lib.JSONDecodeError, TypeError):
            pass

        replay_findings = replay_parsed.get("findings", [])
        replay_risk_score = replay_parsed.get("risk_score")

        # Build comparison
        comparison = ReplayComparison(
            execution_id=str(original_run.run_id),
            original_run_id=original_run_id,
            replay_run_id=replay_outcome.trace_id or "",
            original_findings_count=original_run.findings_count,
            replay_findings_count=len(replay_findings),
            original_risk_score=original_run.risk_score,
            replay_risk_score=replay_risk_score,
            original_latency_ms=original_run.latency_ms or 0,
            replay_latency_ms=replay_outcome.response.latency_ms if replay_outcome.response else 0,
            original_tokens=original_run.total_tokens,
            replay_tokens=replay_outcome.response.total_tokens if replay_outcome.response else 0,
            original_cost=original_run.cost_usd or 0.0,
            replay_cost=replay_outcome.response.cost_usd if replay_outcome.response else 0.0,
            replayed_at=datetime.utcnow().isoformat(),
            prompt_version_changed=False,
            retrieval_snapshot_matched=snapshot_matched,
            provider_changed=provider_overridden,
            model_changed=model_overridden,
        )

        # Compute deltas
        comparison.risk_score_delta = (
            (replay_risk_score or 0.0) - (original_run.risk_score or 0.0)
        )
        comparison.latency_delta_ms = comparison.replay_latency_ms - comparison.original_latency_ms
        comparison.token_delta = comparison.replay_tokens - comparison.original_tokens
        comparison.cost_delta = comparison.replay_cost - comparison.original_cost

        # Compare findings
        original_titles = {f.title for f in original_findings}
        replay_titles = {f.get("title", "") for f in replay_findings}

        comparison.new_findings = [
            f for f in replay_findings
            if f.get("title", "") not in original_titles
        ]
        comparison.missing_findings = [
            {"title": f.title, "severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity)}
            for f in original_findings if f.title not in replay_titles
        ]

        # Calculate overlap (Jaccard similarity)
        if original_titles or replay_titles:
            intersection = original_titles & replay_titles
            union = original_titles | replay_titles
            comparison.findings_overlap = len(intersection) / len(union)

        # Detect changed findings (same title, different description/severity)
        original_by_title = {f.title: f for f in original_findings}
        for rf in replay_findings:
            title = rf.get("title", "")
            if title in original_by_title:
                of = original_by_title[title]
                if (
                    rf.get("description", "") != (of.description or "")
                    or rf.get("severity", "") != (of.severity.value if hasattr(of.severity, 'value') else str(of.severity))
                ):
                    comparison.changed_findings.append({
                        "title": title,
                        "original_severity": of.severity.value if hasattr(of.severity, 'value') else str(of.severity),
                        "replay_severity": rf.get("severity"),
                        "original_description": of.description[:200],
                        "replay_description": (rf.get("description", "") or "")[:200],
                    })

        # Compute overall drift score
        comparison.drift_score = self._compute_drift_score(comparison)
        comparison.drift_detected = comparison.drift_score > 0.05
        comparison.drift_severity = self._classify_drift(comparison.drift_score)

        return comparison

    def _compute_drift_score(self, comparison: ReplayComparison) -> float:
        """Compute a composite drift score from multiple dimensions."""
        score = 0.0

        # Finding overlap (inverse: lower overlap = more drift)
        if comparison.findings_overlap < 1.0:
            score += (1.0 - comparison.findings_overlap) * 0.4

        # New/missing findings
        total_original = max(comparison.original_findings_count, 1)
        new_ratio = len(comparison.new_findings) / total_original
        missing_ratio = len(comparison.missing_findings) / total_original
        score += (new_ratio + missing_ratio) * 0.2

        # Risk score delta
        score += min(abs(comparison.risk_score_delta), 1.0) * 0.2

        # Changed findings
        if comparison.original_findings_count > 0:
            changed_ratio = len(comparison.changed_findings) / comparison.original_findings_count
            score += changed_ratio * 0.2

        return min(score, 1.0)

    def _classify_drift(self, score: float) -> DriftSeverity:
        """Classify drift severity from a drift score."""
        if score < 0.05:
            return DriftSeverity.NONE
        elif score < 0.15:
            return DriftSeverity.LOW
        elif score < 0.30:
            return DriftSeverity.MEDIUM
        elif score < 0.50:
            return DriftSeverity.HIGH
        else:
            return DriftSeverity.CRITICAL

    def _compute_comparison(
        self,
        run_a: AIExecutionRun,
        run_b: AIExecutionRun,
        original_run_id: str,
        replay_run_id: str,
        snapshot_matched: bool,
        provider_changed: bool,
        model_changed: bool,
    ) -> ReplayComparison:
        """Compute comparison between two runs."""
        return ReplayComparison(
            execution_id=str(run_a.run_id),
            original_run_id=original_run_id,
            replay_run_id=replay_run_id,
            original_findings_count=run_a.findings_count,
            replay_findings_count=run_b.findings_count,
            original_risk_score=run_a.risk_score,
            replay_risk_score=run_b.risk_score,
            original_latency_ms=run_a.latency_ms or 0,
            replay_latency_ms=run_b.latency_ms or 0,
            original_tokens=run_a.total_tokens,
            replay_tokens=run_b.total_tokens,
            original_cost=run_a.cost_usd or 0.0,
            replay_cost=run_b.cost_usd or 0.0,
            replayed_at=datetime.utcnow().isoformat(),
            retrieval_snapshot_matched=snapshot_matched,
            provider_changed=provider_changed,
            model_changed=model_changed,
            drift_detected=(
                run_a.findings_count != run_b.findings_count
                or run_a.risk_score != run_b.risk_score
            ),
        )


# ── Replay registry for tracking replay executions ────────────────

_replay_registry: dict[str, list[ReplayResult]] = {}


def register_replay(original_run_id: str, result: ReplayResult) -> None:
    """Register a replay result for audit tracking."""
    if original_run_id not in _replay_registry:
        _replay_registry[original_run_id] = []
    _replay_registry[original_run_id].append(result)


def get_replay_history(original_run_id: str) -> list[ReplayResult]:
    """Get replay history for an execution."""
    return _replay_registry.get(original_run_id, [])
