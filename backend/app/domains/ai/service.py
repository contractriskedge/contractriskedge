"""AI analysis orchestration service — executes multi-step analysis with citation injection and validation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

from app.config import settings
from app.domains.ai.models import ExecutionStatus
from app.domains.ai.schemas import (
    AIExecutionContext,
    AIGuardrailViolation,
    AnalysisRequest,
    AnalysisResult,
    AnalysisStatusResponse,
    RiskFinding,
    RedlineSuggestion,
    ClauseClassification,
    Obligation,
    RiskTraceability,
)
from app.domains.ai.guardrails import GuardrailEngine
from app.domains.ai.llm import (
    OpenAIProvider, LLMRequest, LLMResponse, RateLimitError,
    StructuredOutputParser, llm_registry,
)
from app.domains.ai.orchestration import (
    AIExecutionOrchestrator,
    AIExecutionPlanner,
    AIRequestEnvelope,
)
from app.domains.ai.prompts import prompt_registry
from app.domains.ai.repository import AIRepository
from app.domains.review.redline_ops import (
    RedlineOperation,
    infer_anchor_from_context,
    infer_operation,
    is_chunk_mistaken_as_original,
    normalize_operation,
)
from app.domains.vectors.repository import VectorRepository
from app.domains.ingestion.models import IngestionState, coerce_ingestion_state
from app.domains.ingestion.repository import IngestionRepository
from app.domains.review.models import (
    ContractReview, ReviewFinding, ReviewRedline, ReviewStatus,
)
from app.domains.tenant_config.context_provider import TenantConfigContextProvider
from app.domains.tenant_config.service import ScoringOverrideService
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext
from app.kernel.database.session_utils import release_session_before_io, safe_session_rollback

logger = logging.getLogger(__name__)


_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_REDLINE_SEVERITIES = frozenset({"critical", "high", "medium"})


def _normalize_chunk_indices(indices: list, num_chunks: int) -> list[int]:
    """Map LLM chunk indices to valid 0-based positions (handles 1-based responses)."""
    if num_chunks <= 0:
        return []
    if not indices:
        return list(range(num_chunks))

    normed: list[int] = []
    for raw in indices:
        if isinstance(raw, int):
            normed.append(raw)

    if not normed:
        return list(range(num_chunks))

    # Common LLM mistake: 1-based indices [1, 2] for two chunks → [0, 1]
    if all(i >= 1 for i in normed) and max(normed) == num_chunks:
        normed = [i - 1 for i in normed]

    valid = [i for i in normed if 0 <= i < num_chunks]
    return valid if valid else list(range(num_chunks))


def _chunk_text_for_indices(chunks: list, indices: list[int], max_chars: int = 2000) -> str:
    """Concatenate chunk text for redline prompts."""
    if not chunks:
        return ""
    selected = _normalize_chunk_indices(indices, len(chunks))
    parts: list[str] = []
    total = 0
    for idx in selected:
        text = (chunks[idx].text or "").strip()
        if not text:
            continue
        snippet = text[:1500]
        if total + len(snippet) > max_chars:
            snippet = snippet[: max_chars - total]
        parts.append(snippet)
        total += len(snippet)
        if total >= max_chars:
            break
    return "\n\n".join(parts)


def _findings_eligible_for_redlines(findings: list[RiskFinding], max_count: int = 7) -> list[RiskFinding]:
    """Pick findings that should receive negotiated redline suggestions."""
    if not findings:
        return []

    ranked = sorted(findings, key=lambda f: _SEVERITY_RANK.get(f.severity, 99))
    actionable = [f for f in ranked if f.severity in _REDLINE_SEVERITIES]
    if not actionable:
        # MediumRisk-style contracts often label issues medium/low — still suggest edits when recommended
        actionable = [f for f in ranked if (f.recommendation or "").strip()]

    return actionable[:max_count]


def _coerce_proposed_text(value: object) -> str:
    """Normalize LLM proposed_text to a plain string (models sometimes return dicts)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        lines = []
        for key, text in value.items():
            label = str(key).replace("_", " ").strip().title()
            lines.append(f"{label}: {text}".strip())
        return "\n\n".join(lines)
    if isinstance(value, list):
        return "\n\n".join(_coerce_proposed_text(item) for item in value)
    return str(value).strip()


_LEADING_SECTION_NUMBER_RE = re.compile(
    r"^(?:§\s*)?(?:\d+(?:\.\d+)*|[IVXLCDM]+)[.\s)\t]+",
    re.IGNORECASE,
)


def _strip_section_numbers(text: str) -> str:
    """Strip AI-hallucinated section numbers from the start of insert proposed_text.

    Examples stripped:
      "10. Indemnification. Provider shall..." → "Indemnification. Provider shall..."
      "3.2 Feedback Ownership. Customer retains..." → "Feedback Ownership. Customer retains..."
      "§5.1 Limitation of Liability..." → "Limitation of Liability..."
    """
    if not text:
        return text
    lines = text.splitlines()
    cleaned: list[str] = []
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line and _LEADING_SECTION_NUMBER_RE.match(stripped_line):
            cleaned.append(_LEADING_SECTION_NUMBER_RE.sub("", stripped_line).strip())
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


# ── Calibrated confidence — maps anchor quality to meaningful ranges ───────
# Replaces the LLM's raw floating-point confidence (which defaults to ~0.85)
# with values derived from what we actually know about the redline operation.

_CONFIDENCE_INSERT_EXACT_ANCHOR = 0.88    # insert with known anchor text
_CONFIDENCE_INSERT_TOPOLOGY = 0.68        # insert placed by legal topology
_CONFIDENCE_INSERT_FALLBACK = 0.45        # insert with no structural anchor
_CONFIDENCE_MODIFICATION_HIGH = 0.92     # modification of critical finding
_CONFIDENCE_MODIFICATION_MED = 0.78      # modification of medium finding
_CONFIDENCE_MODIFICATION_LOW = 0.60      # modification of low/info finding


def _calibrate_confidence(
    *,
    operation: str,
    severity: str,
    anchor_text: str,
    proposed_text: str,
    original_text: str,
) -> float:
    """Compute calibrated confidence based on operation type and quality signals."""
    op = (operation or "").lower()
    sev = (severity or "").lower()

    if op == "insert":
        has_anchor = bool(anchor_text and len(anchor_text.strip()) > 5)
        if has_anchor:
            return _CONFIDENCE_INSERT_EXACT_ANCHOR
        if proposed_text and len(proposed_text.strip()) > 50:
            return _CONFIDENCE_INSERT_TOPOLOGY
        return _CONFIDENCE_INSERT_FALLBACK
    else:
        # modification / replace / delete
        has_original = bool(original_text and len(original_text.strip()) > 10)
        if not has_original:
            return _CONFIDENCE_INSERT_TOPOLOGY
        if sev in ("critical",):
            return _CONFIDENCE_MODIFICATION_HIGH
        if sev in ("high", "medium"):
            return _CONFIDENCE_MODIFICATION_MED
        return _CONFIDENCE_MODIFICATION_LOW


@dataclass
class AIService:
    """Orchestrates AI analysis: chunk retrieval → prompt building → LLM execution → validation → persistence."""

    ai_repo: AIRepository
    vector_repo: VectorRepository
    ingest_repo: IngestionRepository
    event_bus: EventBus
    user: Optional[UserContext]
    tenant_id: str

    async def analyze(self, upload_id: str, analysis_type: str = "full",
                       force: bool = False,
                       preserve_redline_ids: Optional[list[str]] = None,
                       preserve_finding_ids: Optional[list[str]] = None) -> AnalysisResult:
        """Run full AI analysis pipeline on an upload's chunks.

        Args:
            upload_id: The upload session to analyze
            analysis_type: Type of analysis ('full', 'risk_only', 'redline_only')
            force: If True, skip duplicate prevention and force re-analysis

        Raises:
            ConflictError: If analysis is already in progress and force=False
        """
        # ── Duplicate analysis prevention ──
        if not force:
            existing_run = await self.ai_repo.get_latest_run_for_upload(upload_id, self.tenant_id)
            if existing_run:
                if existing_run.status in (ExecutionStatus.PROCESSING, ExecutionStatus.PENDING):
                    from app.kernel.web.exceptions import ConflictError
                    from app.kernel.web.error_codes import ErrorCode
                    raise ConflictError(
                        error_code=ErrorCode.CONFLICTING_STATE,
                        message=f"Analysis already in progress (run_id={existing_run.run_id})",
                    )
                if existing_run.status == ExecutionStatus.COMPLETED:
                    logger.info(
                        "Upload %s already analyzed (run_id=%s). Ensuring review handoff.",
                        upload_id, existing_run.run_id,
                    )
                    review = await self._ensure_review_from_completed_run(
                        upload_id, existing_run,
                    )
                    return AnalysisResult(
                        risk_score=existing_run.risk_score or 0.0,
                        findings=[],
                        redlines=[],
                        summary=(
                            f"Reusing existing analysis from run {existing_run.run_id}"
                            + (f"; review {review.review_id} ready" if review else "")
                        ),
                    )

        provider = OpenAIProvider(api_key=settings.openai_api_key)
        llm_registry.register(provider)

        # Register DeepSeek as fallback if API key is configured
        if settings.deepseek_api_key:
            from app.domains.ai.llm import DeepSeekProvider
            deepseek = DeepSeekProvider(api_key=settings.deepseek_api_key)
            llm_registry.register(deepseek)
            logger.info("DeepSeek provider registered for hybrid routing")

        # Determine primary provider: use fallback order first entry if hybrid routing
        fallback_order = getattr(settings, "ai_provider_fallback_order", [provider.provider_name])
        primary_name = fallback_order[0] if fallback_order else provider.provider_name
        primary = llm_registry.get(primary_name) or provider
        logger.info(
            "AI analysis primary provider: %s (fallback chain: %s)",
            primary.provider_name, fallback_order,
        )

        # 2. Retrieve chunks and render prompts for execution planning
        chunks = await self.vector_repo.get_chunks_by_upload(upload_id, self.tenant_id)
        if not chunks:
            raise ValueError(f"No chunks found for upload {upload_id}")

        prompt_text, analysis_request, prompt_version = await self._build_risk_analysis_request(chunks, primary)

        planner = AIExecutionPlanner(tenant_id=self.tenant_id)
        execution_plan = planner.build(
            operation_type="risk_review",
            model=analysis_request.model or "gpt-4o",
            provider_name=primary.provider_name,
            preferred_fallbacks=fallback_order,
            metadata={
                "prompt_version": prompt_version,
                "analysis_type": analysis_type,
            },
        )

        envelope = AIRequestEnvelope(
            tenant_id=self.tenant_id,
            user_id=self.user.id if self.user else None,
            contract_id=None,
            upload_id=upload_id,
            operation_type="risk_review",
            execution_plan=execution_plan,
            retrieval_context={"upload_id": upload_id},
            audit_context={
                "prompt_text": prompt_text,
                "system_prompt": analysis_request.system_prompt,
                "analysis_type": analysis_type,
                "user_role": getattr(self.user, "role", None),
            },
        )

        orchestrator = AIExecutionOrchestrator(self.ai_repo.session, self.tenant_id, self.user.id if self.user else None)
        await release_session_before_io(self.ai_repo.session)
        outcome = await orchestrator.execute(envelope)
        risk_result = outcome.response

        execution_context = self._build_execution_context(
            provider=provider,
            model=analysis_request.model or "gpt-4o",
            prompt_version=prompt_version,
            analysis_prompt_version=prompt_version,
            guardrail_violations=outcome.guardrail_violations or [],
            analysis_type=analysis_type,
        )

        # 3. Create execution run with execution metadata
        run = await self.ai_repo.create_run(
            upload_id=upload_id,
            tenant_id=self.tenant_id,
            analysis_type=analysis_type,
            model=analysis_request.model or "gpt-4o",
            provider=provider.provider_name,
            user_id=self.user.id if self.user else None,
            prompt_version=prompt_version,
            analysis_prompt_version=prompt_version,
            execution_context=execution_context,
        )

        try:
            total_tokens = 0
            total_cost = 0.0

            # 4. Use risk result from orchestrator (avoids duplicate GPT call)
            risk_result = outcome.response
            total_tokens += risk_result.total_tokens if hasattr(risk_result, 'total_tokens') else 0
            total_cost += risk_result.cost_usd if hasattr(risk_result, 'cost_usd') else 0.0

            # Evaluate guardrails on prompt and response
            guardrail_engine = GuardrailEngine()
            pre_violations = guardrail_engine.evaluate_prompt(prompt_text)

            # Parse and validate structured output
            parsed = StructuredOutputParser.parse_json(risk_result.content)

            # Validate parsed output against schema before processing
            validated = StructuredOutputParser.validate_model(parsed, AnalysisResult) if parsed else None
            if validated is None and parsed is not None:
                logger.warning(
                    "AI output failed schema validation, using raw parse as fallback",
                    extra={"upload_id": upload_id, "run_id": str(run.run_id)},
                )

            post_violations = guardrail_engine.evaluate_response(prompt_text, risk_result.content)
            guardrail_violations = pre_violations + post_violations

            # Load tenant scoring overrides for this analysis
            scoring_overrides: dict[str, dict] = {}
            try:
                scoring_service = ScoringOverrideService(
                    self.ai_repo.session, self.tenant_id,
                )
                overrides_list = await scoring_service.list_overrides()
                for o in overrides_list:
                    scoring_overrides[o.clause_type] = {
                        "severity": o.override_severity,
                        "weight": o.override_risk_weight,
                        "score": o.override_risk_score,
                    }
            except Exception as exc:
                logger.warning(
                    "Failed to load scoring overrides: %s — using default scoring",
                    exc,
                )

            analysis_result = self._build_analysis_result(
                validated.model_dump() if validated else parsed,
                risk_result.model,
                guardrail_violations=guardrail_violations,
                execution_context=execution_context,
                scoring_overrides=scoring_overrides,
            )

            # 5. Store findings
            if analysis_result.findings:
                try:
                    await self.ai_repo.store_findings(
                        run_id=run.run_id,
                        upload_id=upload_id,
                        tenant_id=self.tenant_id,
                        findings=analysis_result.findings,
                        chunks=chunks,
                    )
                except Exception as store_err:
                    logger.error("Failed to store findings for upload %s: %s", upload_id, store_err)
                    raise

            # 6. Generate redlines if full analysis
            if analysis_type == "full" or analysis_type == "redline_only":
                try:
                    # Hybrid routing: use GPT-4o for redlines even if risk analysis
                    # used DeepSeek, since redlines need higher quality.
                    redline_provider = primary
                    if settings.ai_hybrid_routing and primary.provider_name == "deepseek":
                        gpt_provider = OpenAIProvider(api_key=settings.openai_api_key)
                        llm_registry.register(gpt_provider)
                        redline_provider = gpt_provider
                        logger.info(
                            "Hybrid routing: risk analysis used %s, redlines use GPT-4o",
                            primary.provider_name,
                        )
                    redline_results = await self._generate_redlines(chunks, analysis_result.findings, redline_provider)
                    analysis_result.redlines = redline_results
                except Exception as redline_err:
                    logger.error("Failed to generate redlines for upload %s: %s", upload_id, redline_err)
                    analysis_result.redlines = []
                if analysis_result.redlines:
                    try:
                        await self.ai_repo.store_redlines(
                            run_id=run.run_id,
                            upload_id=upload_id,
                            tenant_id=self.tenant_id,
                            redlines=analysis_result.redlines,
                            chunks=chunks,
                        )
                    except Exception as store_err:
                        logger.error("Failed to store redlines for upload %s: %s", upload_id, store_err)
                        analysis_result.redlines = []

            # 7. Complete run
            latency = risk_result.latency_ms if hasattr(risk_result, 'latency_ms') else 0
            try:
                await self.ai_repo.complete_run(
                    run_id=run.run_id, result=analysis_result,
                    tokens={"prompt": risk_result.prompt_tokens if hasattr(risk_result, 'prompt_tokens') else 0,
                            "completion": risk_result.completion_tokens if hasattr(risk_result, 'completion_tokens') else 0,
                            "total": total_tokens},
                    cost_usd=total_cost, latency_ms=latency,
                )
            except Exception as complete_err:
                logger.error("Failed to complete run for upload %s: %s", upload_id, complete_err)
                raise

            # 7. Populate review BEFORE marking upload review-ready (workflow integrity)
            try:
                review = await self._populate_review_from_ai(
                    upload_id=upload_id,
                    run_id=str(run.run_id),
                    risk_score=analysis_result.risk_score,
                    ai_confidence=analysis_result.confidence,
                    findings_count=len(analysis_result.findings),
                    redlines_count=len(analysis_result.redlines),
                )
            except Exception as pop_err:
                logger.error("Failed to populate review for upload %s: %s", upload_id, pop_err)
                raise

            # 8. Mark ingestion review-ready only after review record exists
            await self._mark_review_ready_if_needed(upload_id)

            # 9. Notify clients that a review is available
            await self._emit_review_ready(review, upload_id)

            logger.info("AI analysis complete for upload %s: risk=%.4f, %d findings, %d redlines, review=%s",
                         upload_id, analysis_result.risk_score,
                         len(analysis_result.findings), len(analysis_result.redlines),
                         review.review_id)

            return analysis_result

        except Exception as exc:
            logger.error("AI analysis failed for upload %s: %s", upload_id, exc, exc_info=True)
            try:
                await safe_session_rollback(self.ai_repo.session)
                await self.ai_repo.fail_run(run.run_id, str(exc))
                await self.ai_repo.session.commit()
            except Exception as rollback_exc:
                logger.error(
                    "AI analysis rollback also failed for upload %s: %s",
                    upload_id, rollback_exc, exc_info=True,
                )
            raise

    async def _mark_review_ready_if_needed(self, upload_id: str) -> None:
        """Transition upload to REVIEW_READY once a review record exists."""
        upload = await self.ingest_repo.get_upload(upload_id, self.tenant_id)
        if not upload:
            return
        current = coerce_ingestion_state(upload.ingestion_state)
        if current == IngestionState.REVIEW_READY:
            return
        await self.ingest_repo.update_state(
            upload_id, self.tenant_id, IngestionState.REVIEW_READY,
        )

    async def _ensure_review_from_completed_run(
        self,
        upload_id: str,
        run,
    ) -> Optional[ContractReview]:
        """Idempotent handoff: ensure a review exists for a completed AI run.

        Also runs contract type detection on existing reviews that may still have
        a default CNTRCT prefix from initial creation before AI analysis.
        """
        from app.domains.review.repository import ReviewRepository

        review_repo = ReviewRepository(self.ai_repo.session, tenant_id=self.tenant_id)
        existing = await review_repo.get_review_by_upload(upload_id, self.tenant_id)
        if existing:
            # Run contract type detection on existing reviews that may still have
            # the default CNTRCT prefix (e.g. from recovery daemon or prior runs
            # that completed before type detection was added).
            await self._apply_contract_type_detection(existing, str(run.run_id))
            await self._mark_review_ready_if_needed(upload_id)
            return existing

        findings = await self.ai_repo.get_findings_by_run(str(run.run_id), self.tenant_id)
        redlines = await self.ai_repo.get_redlines_by_run(str(run.run_id), self.tenant_id)
        review = await self._populate_review_from_ai(
            upload_id=upload_id,
            run_id=str(run.run_id),
            risk_score=run.risk_score or 0.0,
            findings_count=len(findings),
            redlines_count=len(redlines),
        )
        await self._mark_review_ready_if_needed(upload_id)
        await self._emit_review_ready(review, upload_id)
        logger.info(
            "Repaired missing review handoff for upload %s → review %s",
            upload_id, review.review_id,
        )
        return review

    async def _apply_contract_type_detection(
        self,
        review: "ContractReview",
        run_id: str,
    ) -> None:
        """Run contract type detection on an existing review using AI findings.

        Extracted as a shared helper used by both _ensure_review_from_completed_run
        and _populate_review_from_ai to avoid duplication.
        """
        try:
            from app.domains.ai.models import AIFinding
            from sqlalchemy import select

            stmt = select(AIFinding).where(AIFinding.run_id == run_id)
            ai_findings = (await self.ai_repo.session.execute(stmt)).scalars().all()
            if not ai_findings:
                return

            old_prefix = (review.document_metadata or {}).get("contract_type_prefix", "")
            detected_type = self._detect_contract_type(ai_findings)

            if detected_type and detected_type != old_prefix:
                from app.domains.review.repository import ReviewRepository as RR
                rr = RR(self.ai_repo.session, tenant_id=self.tenant_id)
                new_cn, new_rn = await rr.update_contract_type(
                    str(review.review_id), self.tenant_id, detected_type,
                )
                if new_cn:
                    review.document_metadata["contract_number"] = new_cn
                    review.document_metadata["contract_type_prefix"] = detected_type
                    review.review_number = new_rn
                    logger.info(
                        "Contract type updated (from _ensure_review_from_completed_run): "
                        "review=%s %s → %s (%s)",
                        review.review_id, old_prefix, detected_type, new_cn,
                    )
        except Exception as ct_exc:
            logger.warning(
                "Contract type detection failed in _ensure_review_from_completed_run "
                "for review %s: %s",
                review.review_id, ct_exc,
            )

    async def _emit_review_ready(self, review: ContractReview, upload_id: str) -> None:
        """Broadcast that a review is ready for the review workspace."""
        try:
            from app.kernel.events.realtime import emit_event, EventTypes

            await emit_event(
                self.tenant_id,
                EventTypes.REVIEW_CREATED,
                {
                    "review_id": str(review.review_id),
                    "upload_id": upload_id,
                    "status": (
                        review.status.value
                        if hasattr(review.status, "value")
                        else review.status
                    ),
                    "finding_count": review.finding_count,
                    "redline_count": review.redline_count,
                },
            )
        except Exception as exc:
            logger.warning("Failed to emit review.created for %s: %s", review.review_id, exc)

    async def _populate_review_from_ai(
        self,
        upload_id: str,
        run_id: str,
        risk_score: float,
        ai_confidence: float = 0.0,
        findings_count: int = 0,
        redlines_count: int = 0,
    ) -> ContractReview:
        """Create or update a ContractReview and import AI findings/redlines.

        Runs inside the same session/transaction as the AI analysis.
        Idempotent: re-analysis replaces old findings/redlines, increments version.
        """
        from app.kernel.database.orm_registry import register_orm_models

        register_orm_models()
        from sqlalchemy import select, delete as sa_delete, func
        from app.domains.review.models import ContractReview
        from app.domains.ai.models import AIFinding, AIRedline
        from app.domains.review.repository import ReviewRepository

        review_repo = ReviewRepository(self.ai_repo.session, tenant_id=self.tenant_id)

        # Check for existing review for this upload
        review = await review_repo.get_review_by_upload(upload_id, self.tenant_id)

        if review:
            # Re-analysis: increment version, remove old findings/redlines
            review.version = (review.version or 1) + 1
            await self.ai_repo.session.execute(
                sa_delete(ReviewFinding).where(
                    ReviewFinding.review_id == review.review_id,
                    ReviewFinding.tenant_id == self.tenant_id,
                )
            )
            await self.ai_repo.session.execute(
                sa_delete(ReviewRedline).where(
                    ReviewRedline.review_id == review.review_id,
                    ReviewRedline.tenant_id == self.tenant_id,
                )
            )
            # Backfill contract_number if missing (e.g., review was created before
            # create_review() was introduced, or by recovery daemon)
            if not review.document_metadata.get("contract_number"):
                now = datetime.utcnow()
                month_year = now.strftime("%m%Y")
                count_stmt = select(func.count()).select_from(ContractReview).where(
                    ContractReview.tenant_id == self.tenant_id,
                )
                running = (await self.ai_repo.session.scalar(count_stmt)) + 1
                review.document_metadata["contract_number"] = f"C{month_year}{running:02d}"
                logger.info(
                    "Backfilled contract_number=%s for review %s",
                    review.document_metadata["contract_number"], review.review_id,
                )
            logger.info(
                "Re-analysis: reset findings/redlines for review %s (version %d)",
                review.review_id, review.version,
            )
        else:
            # First analysis: create new review via repository to ensure
            # contract_number is generated and stored in document_metadata.
            review = await review_repo.create_review(
                upload_id=upload_id,
                tenant_id=self.tenant_id,
                created_by=getattr(self.user, 'id', None) or "system",
            )
            logger.info("Created new review %s for upload %s (contract_number=%s)",
                         review.review_id, upload_id,
                         review.document_metadata.get("contract_number", "N/A"))

        # Import AI findings → review_findings
        stmt_findings = select(AIFinding).where(AIFinding.run_id == run_id)
        ai_findings = (await self.ai_repo.session.execute(stmt_findings)).scalars().all()
        ai_finding_to_review: dict[str, str] = {}
        for af in ai_findings:
            rf = ReviewFinding(
                review_id=review.review_id,
                upload_id=af.upload_id,
                tenant_id=af.tenant_id,
                ai_finding_id=af.finding_id,
                clause_type=af.clause_type,
                severity=af.severity.value if hasattr(af.severity, 'value') else af.severity,
                title=af.title,
                description=af.description,
                recommendation=af.recommendation,
                confidence=af.confidence,
                risk_score=af.risk_score,
                chunk_ids=af.chunk_ids,
                page_numbers=af.page_numbers,
            )
            self.ai_repo.session.add(rf)
            await self.ai_repo.session.flush()
            ai_finding_to_review[str(af.finding_id)] = str(rf.finding_id)

        # Import AI redlines → review_redlines
        stmt_redlines = select(AIRedline).where(AIRedline.run_id == run_id)
        ai_redlines = (await self.ai_repo.session.execute(stmt_redlines)).scalars().all()

        def _link_redline_to_review_finding(ar: AIRedline) -> Optional[str]:
            """Map AI redline → review_finding by clause category, then chunk overlap.

            Chunk-only linking caused NDA reviews to attach every insert redline to the
            first overlapping finding (often the info-level confidentiality row) even when
            clause_type was intellectual_property / liability / etc.
            """
            from app.domains.review.mapping_validation import (
                categories_compatible,
                normalize_category,
            )

            ct = ar.clause_type or "other"
            redline_cat = normalize_category(ct)
            ar_chunks = {str(c) for c in (ar.chunk_ids or [])}

            def _review_finding_id(af: AIFinding) -> Optional[str]:
                return ai_finding_to_review.get(str(af.finding_id))

            # 1. Exact clause_type string match
            same_type = [af for af in ai_findings if (af.clause_type or "other") == ct]
            if len(same_type) == 1:
                return _review_finding_id(same_type[0])

            # 2. Canonical category match (handles ip ↔ intellectual_property, etc.)
            if redline_cat:
                cat_matches = [
                    af for af in ai_findings
                    if categories_compatible(redline_cat, normalize_category(af.clause_type))
                ]
                if len(cat_matches) == 1:
                    return _review_finding_id(cat_matches[0])
                if len(cat_matches) > 1 and ar_chunks:
                    best_af: Optional[AIFinding] = None
                    best_overlap = 0
                    for af in cat_matches:
                        overlap = len(ar_chunks & {str(c) for c in (af.chunk_ids or [])})
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_af = af
                    if best_af and best_overlap > 0:
                        return _review_finding_id(best_af)

            # 3. Chunk overlap — only when categories are compatible
            best_af = None
            best_overlap = 0
            for af in ai_findings:
                finding_cat = normalize_category(af.clause_type)
                if redline_cat and finding_cat and not categories_compatible(redline_cat, finding_cat):
                    continue
                overlap = len(ar_chunks & {str(c) for c in (af.chunk_ids or [])})
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_af = af
            if best_af and best_overlap > 0:
                return _review_finding_id(best_af)

            return None

        for ar in ai_redlines:
            # Carry traceability metadata from the AI redline JSONB, if present
            # ar.ai_metadata is a JSONB column; fall back to empty dict if None
            raw_meta = getattr(ar, "ai_metadata", None)
            ai_meta = raw_meta if isinstance(raw_meta, dict) else {}

            linked_finding_id = _link_redline_to_review_finding(ar)

            rr = ReviewRedline(
                review_id=review.review_id,
                upload_id=ar.upload_id,
                tenant_id=ar.tenant_id,
                ai_redline_id=ar.redline_id,
                finding_id=linked_finding_id,
                clause_type=ar.clause_type,
                original_text=ar.original_text,
                proposed_text=ar.proposed_text,
                operation=getattr(ar, "operation", None),
                anchor_text=getattr(ar, "anchor_text", None),
                rationale=ar.rationale,
                risk_level=ar.risk_level,
                confidence=ar.confidence,
                redline_metadata={
                    "traceability": ai_meta.get("traceability", {}),
                    "legal_domain": ai_meta.get("legal_domain"),
                    "risk_type": ai_meta.get("risk_type"),
                },
            )
            self.ai_repo.session.add(rr)

        # Update aggregate counts
        review.finding_count = len(ai_findings)
        review.redline_count = len(ai_redlines)

        # Store risk_score and ai_confidence in document metadata
        current_meta = dict(review.document_metadata) if review.document_metadata else {}
        review.document_metadata = {
            **current_meta,
            "risk_score": risk_score,
            "ai_confidence": ai_confidence,
            "last_analysis_run_id": run_id,
        }

        # Transition status to AI_ANALYZED (only if currently DRAFT)
        current_status = review.status
        if isinstance(current_status, str):
            current_status = ReviewStatus(current_status)
        if current_status == ReviewStatus.DRAFT:
            review.status = ReviewStatus.AI_ANALYZED

        await self.ai_repo.session.flush()
        logger.info(
            "Review %s populated: %d findings, %d redlines, risk_score=%.4f",
            review.review_id, review.finding_count, review.redline_count, risk_score,
        )

        # Backfill mitigation redlines for findings the AI redline pass skipped
        # (unmapped NDA clause types, empty chunk text, severity cap, etc.)
        try:
            from app.domains.review.repository import ReviewRepository
            from app.domains.review.service import ReviewService
            from app.kernel.events.bus import EventBus

            review_svc = ReviewService(
                review_repo=ReviewRepository(self.ai_repo.session, tenant_id=self.tenant_id),
                ai_repo=self.ai_repo,
                event_bus=EventBus(),
                user=self.user,
                tenant_id=self.tenant_id,
            )
            backfill = await review_svc.backfill_mitigation_redlines_for_gaps(str(review.review_id))
            if isinstance(backfill, dict) and backfill.get("backfilled"):
                review.redline_count = backfill["coverage_after"]["redlines"]
                await self.ai_repo.session.flush()
                logger.info(
                    "Review %s redline backfill: +%d redlines (coverage %.1f%%)",
                    review.review_id,
                    backfill["backfilled"],
                    backfill["coverage_after"]["coverage_pct"],
                )
        except Exception as backfill_exc:
            logger.warning(
                "Mitigation redline backfill failed for review %s: %s",
                review.review_id, backfill_exc,
            )

        # ── Contract Type Detection & Number Update ────────────────────────
        # After AI analysis, detect the contract type from findings and update
        # the contract number prefix if it was a best-guess (e.g. CNTRCT → NDA).
        try:
            old_prefix = (review.document_metadata or {}).get("contract_type_prefix", "")
            detected_type = self._detect_contract_type(ai_findings)

            if detected_type and detected_type != old_prefix:
                from app.domains.review.repository import ReviewRepository as RR
                rr = RR(self.ai_repo.session, tenant_id=self.tenant_id)
                new_cn, new_rn = await rr.update_contract_type(
                    str(review.review_id), self.tenant_id, detected_type,
                )
                if new_cn:
                    review.document_metadata["contract_number"] = new_cn
                    review.document_metadata["contract_type_prefix"] = detected_type
                    review.review_number = new_rn
                    logger.info(
                        "Contract type updated: review=%s %s → %s (%s)",
                        review.review_id, old_prefix, detected_type, new_cn,
                    )
        except Exception as ct_exc:
            logger.warning("Contract type detection failed for review %s: %s", review.review_id, ct_exc)

        return review

    def _detect_contract_type(self, ai_findings: list) -> Optional[str]:
        """Detect contract type from AI analysis findings.

        Uses the clause types present in findings to infer the contract type.
        Falls back to None if detection is uncertain.
        """
        if not ai_findings:
            return None

        # Collect unique clause types from findings
        clause_types = set()
        for f in ai_findings:
            ct = getattr(f, "clause_type", None) or ""
            clause_types.add(ct.lower().strip())

        ct_str = " ".join(clause_types)

        # Scoring-based detection
        scores: dict[str, int] = {}
        for keyword, ctype in [
            ("non-disclosure", "NDA"), ("confidentiality", "NDA"),
            ("mutual", "NDA"), ("nda", "NDA"),
            ("master service", "MSA"), ("msa", "MSA"),
            ("statement of work", "SOW"), ("sow", "SOW"), ("scope of work", "SOW"),
            ("data processing", "DPA"), ("dpa", "DPA"),
            ("employment", "EMP"), ("employee", "EMP"), ("emp_", "EMP"),
            ("purchase", "PUR"), ("pur_", "PUR"), ("procurement", "PUR"),
            ("vendor", "VEN"), ("ven_", "VEN"), ("supplier", "VEN"),
            ("saas", "SaaS"), ("software as a service", "SaaS"), ("subscription", "SaaS"),
            ("lease", "LEASE"), ("lease_", "LEASE"), ("rental", "LEASE"),
            ("amendment", "AMEND"), ("amend_", "AMEND"), ("modification", "AMEND"),
            ("service agreement", "MSA"), ("professional service", "SOW"),
            ("license", "SaaS"), ("licensing", "SaaS"),
            ("construction", "PUR"), ("supply", "PUR"),
            ("non-compete", "EMP"), ("severance", "EMP"),
        ]:
            if keyword in ct_str:
                scores[ctype] = scores.get(ctype, 0) + 1

        if not scores:
            return None

        # Return the type with the highest score
        best = max(scores, key=scores.get)
        confidence = scores[best] / max(sum(scores.values()), 1)
        # Only return if confidence is reasonable
        if confidence >= 0.3 or scores[best] >= 2:
            return best
        return None

    async def _execute_risk_analysis(self, chunks: list, provider: OpenAIProvider) -> LLMResponse:
        """Execute risk analysis prompt against contract chunks."""
        chunk_data = [
            {"text": c.text[:2000], "page_numbers": c.page_numbers or [1]}
            for c in chunks[:50]  # Limit to 50 chunks for context window
        ]

        prompt = prompt_registry.render(
            "risk_analysis", version=1,
            chunks=chunk_data,
        )

        template = prompt_registry.get("risk_analysis")
        request = LLMRequest(
            prompt=prompt,
            system_prompt=template.system_prompt if template else None,
            model=template.model if template else "gpt-4o",
            temperature=template.temperature if template else 0.1,
            max_tokens=template.max_tokens if template else 4096,
            response_format={"type": "json_object"},
        )

        return await provider.complete(request)

    async def _build_risk_analysis_request(
        self,
        chunks: list,
        provider: OpenAIProvider,
    ) -> tuple[str, LLMRequest, int]:
        """Render the risk analysis prompt and request for execution.

        Injects tenant-specific policy context (Playbook + Policy Pack overrides)
        into the LLM prompt so the AI evaluates clauses against company standards.
        """
        chunk_data = [
            {"text": c.text[: settings.ai_analysis_max_chunk_chars], "page_numbers": c.page_numbers or [1]}
            for c in chunks[: settings.ai_analysis_max_chunks]
        ]

        # ── Tenant Configuration Injection ────────────────────────────
        policy_context_str = ""
        try:
            config_provider = TenantConfigContextProvider(
                self.ai_repo.session, self.tenant_id,
            )
            merged = await config_provider.get_merged_context()

            if merged.clauses or merged.rules:
                parts = ["TENANT POLICY CONTEXT:"]
                parts.append("")

                # Policy rules
                mandatory = [r for r in merged.rules if r.is_mandatory and r.is_active]
                if mandatory:
                    parts.append(f"MANDATORY RULES ({len(mandatory)}):")
                    for r in mandatory[:10]:
                        parts.append(f"  - [{r.rule_type}] {r.name}: effect={r.effect}")
                    parts.append("")

                # Clause standards with overrides applied
                approved = [c for c in merged.clauses if c.clause_type in ("approved", "preferred") and c.is_active]
                if approved:
                    parts.append(f"APPROVED CLAUSE STANDARDS ({len(approved)}):")
                    for c in approved[:10]:
                        tag = " [TENANT OVERRIDE]" if c.overridden else ""
                        parts.append(f"  - {c.category}/{c.title}{tag}: {c.body[:300]}")
                    parts.append("")

                forbidden = [c for c in merged.clauses if c.clause_type == "forbidden" and c.is_active]
                if forbidden:
                    parts.append(f"FORBIDDEN CLAUSES ({len(forbidden)}):")
                    for c in forbidden[:5]:
                        parts.append(f"  - {c.category}/{c.title}")
                    parts.append("")

                if merged.total_overrides_applied > 0:
                    parts.append(
                        f"Note: {merged.total_overrides_applied} tenant-specific "
                        f"override(s) are active for this analysis."
                    )
                    parts.append("")

                parts.append("Evaluate each clause against these standards. Flag any deviations.")
                policy_context_str = "\n".join(parts)

        except Exception as exc:
            logger.warning(
                "Failed to load tenant policy context: %s — continuing without policy injection",
                exc,
            )

        prompt = prompt_registry.render(
            "risk_analysis", version="1.0.0",
            chunks=chunk_data,
            policy_context=policy_context_str,
        )

        template = prompt_registry.get("risk_analysis")
        # Use provider-appropriate model name (DeepSeek uses deepseek-v4-flash, not gpt-4o)
        provider_model = provider.supported_models[0] if provider.supported_models else "gpt-4o"
        request = LLMRequest(
            prompt=prompt,
            system_prompt=template.system_prompt if template else None,
            model=provider_model,
            temperature=template.default_temperature if template else 0.1,
            max_tokens=template.default_max_tokens if template else 4096,
            response_format={"type": "json_object"},
        )

        prompt_version = template.version if template else 1
        return prompt, request, prompt_version

    def _build_execution_context(
        self,
        provider: OpenAIProvider,
        model: str,
        prompt_version: int,
        analysis_prompt_version: int,
        guardrail_violations: list[Any],
        analysis_type: str,
    ) -> dict[str, Any]:
        """Build execution metadata for traceability and replay."""
        rule_ids = []
        for violation in guardrail_violations:
            if hasattr(violation, "rule_id"):
                rule_ids.append(getattr(violation, "rule_id"))
            elif isinstance(violation, dict):
                rule_ids.append(violation.get("rule_id"))

        return {
            "provider": provider.provider_name,
            "model": model,
            "prompt_version": prompt_version,
            "analysis_prompt_version": analysis_prompt_version,
            "guardrail_rule_ids": [rid for rid in rule_ids if rid],
            "source": "ai_analysis_service",
            "context": {
                "user_id": self.user.id if self.user else None,
                "analysis_type": analysis_type,
            },
        }

    async def _generate_redlines(
        self, chunks: list, findings: list[RiskFinding], provider: OpenAIProvider,
    ) -> list[RedlineSuggestion]:
        """Generate redline suggestions for actionable findings (critical/high/medium).

        Uses a batched prompt — ALL eligible findings are sent in a single GPT call
        to dramatically reduce API usage and rate limit pressure.
        """
        eligible = _findings_eligible_for_redlines(findings)
        if not eligible and findings:
            logger.info(
                "No findings eligible for redlines (%d findings; severities=%s)",
                len(findings),
                sorted({f.severity for f in findings}),
            )
        if not eligible:
            return []

        # Load tenant config context for clause override injection (shared across findings)
        tenant_clause_overrides: dict[str, str] = {}
        try:
            config_provider = TenantConfigContextProvider(
                self.ai_repo.session, self.tenant_id,
            )
            merged = await config_provider.get_merged_context()
            for c in merged.clauses:
                if c.overridden and c.body:
                    tenant_clause_overrides[c.category] = c.body
        except Exception as exc:
            logger.warning(
                "Failed to load tenant clause overrides: %s — continuing without overrides",
                exc,
            )

        # Build batched finding data with playbook context per finding
        from app.domains.playbook.context_provider import PlaybookContextProvider
        playbook_provider = PlaybookContextProvider(self.ai_repo.session, self.tenant_id)

        batched_findings = []
        for finding in eligible:
            relevant_text = _chunk_text_for_indices(chunks, finding.chunk_indices)
            if not relevant_text.strip():
                logger.warning(
                    "Skipping redline for %s: no chunk text (indices=%s, chunks=%d)",
                    finding.clause_type,
                    finding.chunk_indices,
                    len(chunks),
                )
                continue

            # Fetch playbook context for this clause type
            playbook_context = ""
            try:
                pb_ctx = await playbook_provider.get_context(
                    clause_category=finding.clause_type or "general",
                )
                if pb_ctx.has_context():
                    playbook_context = pb_ctx.to_prompt_context()
            except Exception as pb_exc:
                logger.warning(
                    "Playbook context fetch failed for %s: %s — continuing without playbook guidance",
                    finding.clause_type, pb_exc,
                )

            # Inject tenant-specific clause override if available
            override_body = tenant_clause_overrides.get(finding.clause_type or "")
            if override_body:
                if playbook_context:
                    playbook_context += (
                        f"\n\nTENANT-SPECIFIC CLAUSE OVERRIDE:\n{override_body}\n\n"
                        "This tenant-specific override takes precedence over the playbook standards above."
                    )
                else:
                    playbook_context = (
                        f"TENANT-SPECIFIC CLAUSE LANGUAGE:\n{override_body}\n\n"
                        "Use this language as the primary basis for your proposed_text."
                    )

            batched_findings.append({
                "clause_type": finding.clause_type,
                "original_text": relevant_text[:2000],
                "title": finding.title,
                "description": finding.description,
                "playbook_context": playbook_context,
                "_finding": finding,
            })

        if not batched_findings:
            return []

        # Single batched GPT call for all findings
        prompt = prompt_registry.render(
            "redline_generation_batch", version=1,
            findings=[
                {
                    "clause_type": bf["clause_type"],
                    "original_text": bf["original_text"],
                    "title": bf["title"],
                    "description": bf["description"],
                    "playbook_context": bf["playbook_context"],
                }
                for bf in batched_findings
            ],
        )

        template = prompt_registry.get("redline_generation_batch", version=1)
        request = LLMRequest(
            prompt=prompt,
            system_prompt=template.system_prompt if template else None,
            model=template.default_model if template else "gpt-4o",
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        redlines: list[RedlineSuggestion] = []
        try:
            await release_session_before_io(self.ai_repo.session)
            response = await provider.complete(request)
            parsed = StructuredOutputParser.parse_json(response.content)
            if parsed and "redlines" in parsed:
                for entry in parsed["redlines"]:
                    finding_index = entry.get("finding_index", 1) - 1  # Convert 1-based to 0-based
                    if finding_index < 0 or finding_index >= len(batched_findings):
                        logger.warning("Batch redline finding_index %d out of range", finding_index + 1)
                        continue

                    bf = batched_findings[finding_index]
                    finding = bf["_finding"]

                    proposed_text = _coerce_proposed_text(entry.get("proposed_text", ""))
                    rationale = entry.get("rationale", "")
                    if not isinstance(rationale, str):
                        rationale = _coerce_proposed_text(rationale)
                    anchor_text = _coerce_proposed_text(entry.get("anchor_text", ""))
                    original_text = _coerce_proposed_text(entry.get("original_text", ""))
                    operation = normalize_operation(entry.get("operation"))
                    if not operation:
                        operation = infer_operation(
                            original_text,
                            proposed_text,
                            clause_type=finding.clause_type,
                        )

                    relevant_text = bf["original_text"]
                    if (
                        operation == RedlineOperation.INSERT
                        or is_chunk_mistaken_as_original(original_text, proposed_text)
                    ):
                        operation = RedlineOperation.INSERT
                        original_text = ""
                        if not anchor_text.strip():
                            full_corpus = _chunk_text_for_indices(
                                chunks, list(range(len(chunks))), max_chars=8000,
                            )
                            anchor_text = infer_anchor_from_context(
                                full_corpus or relevant_text[:2000], proposed_text,
                            )
                    elif not original_text.strip():
                        operation = RedlineOperation.INSERT
                        original_text = ""
                        if not anchor_text.strip():
                            full_corpus = _chunk_text_for_indices(
                                chunks, list(range(len(chunks))), max_chars=8000,
                            )
                            anchor_text = infer_anchor_from_context(
                                full_corpus or relevant_text[:2000], proposed_text,
                            )
                    if not anchor_text.strip() and original_text.strip():
                        anchor_text = original_text.strip()[:200]

                    if operation == RedlineOperation.INSERT:
                        proposed_text = _strip_section_numbers(proposed_text)

                    if not proposed_text.strip():
                        logger.warning(
                            "Batch redline returned empty proposed_text for finding %d (%s)",
                            finding_index + 1, finding.clause_type,
                        )
                        continue

                    confidence = _calibrate_confidence(
                        operation=operation.value,
                        severity=str(finding.severity.value if hasattr(finding.severity, "value") else finding.severity),
                        anchor_text=anchor_text,
                        proposed_text=proposed_text,
                        original_text=original_text,
                    )

                    traceability = RiskTraceability(
                        detected_risk=str(entry.get("detected_risk", "") or ""),
                        business_impact=str(entry.get("business_impact", "") or ""),
                        mitigation_strategy=str(entry.get("mitigation_strategy", "") or ""),
                    )

                    redlines.append(RedlineSuggestion(
                        clause_type=finding.clause_type,
                        original_text=original_text,
                        proposed_text=proposed_text,
                        operation=operation.value,
                        anchor_text=anchor_text,
                        rationale=rationale,
                        risk_level=finding.severity,
                        confidence=confidence,
                        chunk_indices=_normalize_chunk_indices(
                            finding.chunk_indices, len(chunks),
                        ),
                        traceability=traceability,
                    ))
            else:
                logger.warning(
                    "Batch redline response missing 'redlines' array: %s",
                    str(parsed)[:200] if parsed else "null",
                )
        except RateLimitError:
            # Rate-limited during redline generation — re-raise so Celery's
            # autoretry_for can re-queue the entire task, giving redlines
            # another chance instead of silently completing with 0 redlines.
            logger.warning(
                "Batch redline generation rate-limited, re-raising for task retry "
                "(%d findings eligible)",
                len(eligible),
            )
            raise
        except Exception as exc:
            logger.error("Batch redline generation failed: %s", exc, exc_info=True)

        logger.info(
            "Generated %d redlines from %d findings (%d eligible) — batched into 1 GPT call",
            len(redlines),
            len(findings),
            len(eligible),
        )
        return redlines

    def _build_analysis_result(
        self,
        parsed: Optional[dict],
        model: str,
        guardrail_violations: list[AIGuardrailViolation] | None = None,
        execution_context: Optional[dict[str, Any]] = None,
        scoring_overrides: Optional[dict[str, dict]] = None,
    ) -> AnalysisResult:
        """Build structured AnalysisResult from parsed LLM output.

        Applies tenant-specific Scoring Overrides (when available) to override
        severity, risk weight, and risk score per clause type.

        Args:
            parsed: Parsed LLM output
            model: Model name used
            guardrail_violations: Any guardrail violations
            execution_context: Execution metadata
            scoring_overrides: Optional dict of clause_type → {severity, weight, score}
        """
        scoring_overrides = scoring_overrides or {}
        default_conf_map = {"critical": 0.95, "high": 0.85, "medium": 0.65, "low": 0.40}
        if not parsed:
            return AnalysisResult(
                model_used=model,
                confidence=0.0,
                guardrail_violations=guardrail_violations or [],
                execution_context=AIExecutionContext(
                    provider=execution_context.get("provider", "") if execution_context else "",
                    model=execution_context.get("model", model) if execution_context else model,
                    prompt_version=execution_context.get("prompt_version") if execution_context else None,
                    analysis_prompt_version=execution_context.get("analysis_prompt_version") if execution_context else None,
                    guardrail_rule_ids=execution_context.get("guardrail_rule_ids", []) if execution_context else [],
                    source=execution_context.get("source", "ai_analysis_service") if execution_context else "ai_analysis_service",
                    context=execution_context.get("context", {}) if execution_context else {},
                ) if execution_context else None,
            )

        findings = []
        for f in parsed.get("findings", []):
            clause_type = f.get("clause_type", "other")
            tenant_override = scoring_overrides.get(clause_type)

            # Coerce confidence to float — the AI sometimes returns strings
            raw_conf = f.get("confidence", 0.5)
            if isinstance(raw_conf, str):
                normalized = raw_conf.strip().lower()
                if normalized in default_conf_map:
                    confidence = default_conf_map[normalized]
                else:
                    try:
                        confidence = float(normalized)
                    except (ValueError, TypeError):
                        confidence = 0.5
            elif isinstance(raw_conf, (int, float)):
                confidence = float(raw_conf)
            else:
                confidence = 0.5
            confidence = max(0.0, min(1.0, confidence))

            # Apply tenant scoring override for severity
            severity = f.get("severity", "info")
            if tenant_override and tenant_override.get("severity"):
                severity = tenant_override["severity"]

            # Apply tenant scoring override for risk_score
            risk_score = f.get("risk_score")
            if tenant_override and tenant_override.get("score") is not None:
                risk_score = tenant_override["score"]

            findings.append(RiskFinding(
                clause_type=clause_type,
                severity=severity,
                title=f.get("title", ""),
                description=f.get("description", ""),
                recommendation=f.get("recommendation"),
                confidence=confidence,
                risk_score=risk_score,
                chunk_indices=f.get("chunk_indices", []),
            ))

        # Calculate overall risk score using tenant weights if available
        overall_risk = parsed.get("risk_score", 0.0)
        if findings and scoring_overrides:
            weighted_scores = []
            total_weight = 0.0
            for finding in findings:
                override = scoring_overrides.get(finding.clause_type)
                weight = 1.0
                if override and override.get("weight") is not None:
                    weight = override["weight"]
                score = finding.risk_score if finding.risk_score is not None else 0.5
                weighted_scores.append(score * weight)
                total_weight += weight
            if total_weight > 0:
                overall_risk = sum(weighted_scores) / total_weight

        # ── Safeguard: never store the LLM's literal "risk_score" as the
        # overall risk if it is suspiciously equal to the finding count
        # (the LLM sometimes writes the count instead of an aggregate
        # score). When that pattern is detected we fall back to a
        # severity-weighted aggregate computed from the findings.
        llm_literal = parsed.get("risk_score", 0.0)
        finding_count = len(findings)
        looks_like_count = (
            finding_count > 0
            and isinstance(llm_literal, (int, float))
            and 0 < llm_literal < 100
            and (
                abs(llm_literal - finding_count) < 0.01
                or (0 < llm_literal < 1.0 and abs(llm_literal * 10 - finding_count) < 0.1)
            )
        )
        if looks_like_count and findings:
            # Severity-weighted average as a sanity-check fallback.
            SEVERITY_WEIGHTS = {
                "critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.15, "info": 0.0,
            }
            total = 0.0
            for f in findings:
                total += SEVERITY_WEIGHTS.get(f.severity, 0.4)
            # Scale by severity saturation — more findings of the same
            # severity compound the score, but with diminishing returns.
            aggregate = min(1.0, total / max(3.0, len(findings)))
            logger.warning(
                "LLM risk_score %.4f looks like finding count %d; "
                "using severity-weighted aggregate %.4f instead",
                llm_literal, finding_count, aggregate,
            )
            overall_risk = aggregate
        else:
            # Use the LLM's value, but only if it passed the suspicion check.
            overall_risk = llm_literal

        return AnalysisResult(
            risk_score=overall_risk,
            summary=parsed.get("summary", ""),
            findings=findings,
            model_used=model,
            confidence=0.9 if findings else 0.0,
            guardrail_violations=guardrail_violations or [],
            execution_context=AIExecutionContext(
                provider=execution_context.get("provider", ""),
                model=execution_context.get("model", model),
                prompt_version=execution_context.get("prompt_version"),
                analysis_prompt_version=execution_context.get("analysis_prompt_version"),
                guardrail_rule_ids=execution_context.get("guardrail_rule_ids", []),
                source=execution_context.get("source", "ai_analysis_service"),
                context=execution_context.get("context", {}),
            ) if execution_context else None,
        )

    async def get_status(self, run_id: str) -> Optional[AIExecutionRun]:
        return await self.ai_repo.get_run(run_id, self.tenant_id)

    async def list_runs_by_upload(self, upload_id: str) -> list[AIExecutionRun]:
        """List all AI analysis runs for an upload, ordered by recency."""
        return await self.ai_repo.list_runs_by_upload(upload_id, self.tenant_id)

    async def get_findings(self, run_id: str):
        return await self.ai_repo.get_findings_by_run(run_id, self.tenant_id)

    async def get_redlines(self, run_id: str):
        return await self.ai_repo.get_redlines_by_run(run_id, self.tenant_id)
