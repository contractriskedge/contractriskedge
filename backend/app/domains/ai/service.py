"""AI analysis orchestration service — executes multi-step analysis with citation injection and validation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

from app.config import settings
from app.domains.ai.models import ExecutionStatus
from app.domains.ai.schemas import (
    AnalysisRequest, AnalysisResult, AnalysisStatusResponse,
    RiskFinding, RedlineSuggestion, ClauseClassification, Obligation,
    RiskTraceability,
)
from app.domains.ai.llm import (
    OpenAIProvider, LLMRequest, LLMResponse,
    StructuredOutputParser, llm_registry,
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
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext

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

        # 1. Initialize provider
        provider = OpenAIProvider(api_key=settings.openai_api_key)
        llm_registry.register(provider)

        # 2. Create execution run
        run = await self.ai_repo.create_run(
            upload_id=upload_id, tenant_id=self.tenant_id,
            analysis_type=analysis_type, model="gpt-4o",
            provider="openai", user_id=self.user.id if self.user else None,
        )

        try:
            # 3. Retrieve chunks
            chunks = await self.vector_repo.get_chunks_by_upload(upload_id, self.tenant_id)
            if not chunks:
                raise ValueError(f"No chunks found for upload {upload_id}")

            total_tokens = 0
            total_cost = 0.0

            # 4. Execute risk analysis
            risk_result = await self._execute_risk_analysis(chunks, provider)
            total_tokens += risk_result.total_tokens if hasattr(risk_result, 'total_tokens') else 0
            total_cost += risk_result.cost_usd if hasattr(risk_result, 'cost_usd') else 0.0

            # Parse and validate structured output
            parsed = StructuredOutputParser.parse_json(risk_result.content)

            # Validate parsed output against schema before processing
            validated = StructuredOutputParser.validate_model(parsed, AnalysisResult) if parsed else None
            if validated is None and parsed is not None:
                logger.warning(
                    "AI output failed schema validation, using raw parse as fallback",
                    extra={"upload_id": upload_id, "run_id": str(run.run_id)},
                )

            analysis_result = self._build_analysis_result(
                validated.model_dump() if validated else parsed,
                risk_result.model,
            )

            # 5. Store findings
            if analysis_result.findings:
                await self.ai_repo.store_findings(
                    run_id=run.run_id,
                    upload_id=upload_id,
                    tenant_id=self.tenant_id,
                    findings=analysis_result.findings,
                    chunks=chunks,
                )

            # 6. Generate redlines if full analysis
            if analysis_type == "full" or analysis_type == "redline_only":
                redline_results = await self._generate_redlines(chunks, analysis_result.findings, provider)
                analysis_result.redlines = redline_results
                if analysis_result.redlines:
                    await self.ai_repo.store_redlines(
                        run_id=run.run_id,
                        upload_id=upload_id,
                        tenant_id=self.tenant_id,
                        redlines=analysis_result.redlines,
                        chunks=chunks,
                    )

            # 7. Complete run
            latency = risk_result.latency_ms if hasattr(risk_result, 'latency_ms') else 0
            await self.ai_repo.complete_run(
                run_id=run.run_id, result=analysis_result,
                tokens={"prompt": risk_result.prompt_tokens if hasattr(risk_result, 'prompt_tokens') else 0,
                        "completion": risk_result.completion_tokens if hasattr(risk_result, 'completion_tokens') else 0,
                        "total": total_tokens},
                cost_usd=total_cost, latency_ms=latency,
            )

            # 7. Populate review BEFORE marking upload review-ready (workflow integrity)
            review = await self._populate_review_from_ai(
                upload_id=upload_id,
                run_id=str(run.run_id),
                risk_score=analysis_result.risk_score,
                findings_count=len(analysis_result.findings),
                redlines_count=len(analysis_result.redlines),
            )

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
            try:
                await self.ai_repo.session.rollback()
                await self.ai_repo.fail_run(run.run_id, str(exc))
                await self.ai_repo.session.commit()
            except Exception as rollback_exc:
                logger.error(
                    "AI analysis rollback also failed for upload %s: %s",
                    upload_id, rollback_exc,
                )
            logger.error("AI analysis failed for upload %s: %s", upload_id, exc)
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
        """Idempotent handoff: ensure a review exists for a completed AI run."""
        from app.domains.review.repository import ReviewRepository

        review_repo = ReviewRepository(self.ai_repo.session, tenant_id=self.tenant_id)
        existing = await review_repo.get_review_by_upload(upload_id, self.tenant_id)
        if existing:
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
        findings_count: int,
        redlines_count: int,
    ) -> ContractReview:
        """Create or update a ContractReview and import AI findings/redlines.

        Runs inside the same session/transaction as the AI analysis.
        Idempotent: re-analysis replaces old findings/redlines, increments version.
        """
        from app.kernel.database.orm_registry import register_orm_models

        register_orm_models()
        from sqlalchemy import select, delete as sa_delete
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
            logger.info(
                "Re-analysis: reset findings/redlines for review %s (version %d)",
                review.review_id, review.version,
            )
        else:
            # First analysis: create new review
            review = ContractReview(
                upload_id=upload_id,
                tenant_id=self.tenant_id,
                created_by=getattr(self.user, 'id', None) or "system",
            )
            self.ai_repo.session.add(review)
            await self.ai_repo.session.flush()
            logger.info("Created new review %s for upload %s", review.review_id, upload_id)

        # Import AI findings → review_findings
        stmt_findings = select(AIFinding).where(AIFinding.run_id == run_id)
        ai_findings = (await self.ai_repo.session.execute(stmt_findings)).scalars().all()
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

        # Import AI redlines → review_redlines
        stmt_redlines = select(AIRedline).where(AIRedline.run_id == run_id)
        ai_redlines = (await self.ai_repo.session.execute(stmt_redlines)).scalars().all()

        # Build a lookup from clause_type to finding IDs for linking redlines to findings
        finding_by_clause: dict[str, list[str]] = {}
        for af in ai_findings:
            ct = af.clause_type or "other"
            if ct not in finding_by_clause:
                finding_by_clause[ct] = []
            finding_by_clause[ct].append(str(af.finding_id))

        for ar in ai_redlines:
            # Carry traceability metadata from the AI redline JSONB, if present
            # ar.ai_metadata is a JSONB column; fall back to empty dict if None
            raw_meta = getattr(ar, "ai_metadata", None)
            ai_meta = raw_meta if isinstance(raw_meta, dict) else {}

            # Link redline to the first matching finding by clause_type
            linked_finding_id = None
            ct = ar.clause_type or "other"
            if ct in finding_by_clause and finding_by_clause[ct]:
                linked_finding_id = finding_by_clause[ct][0]

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
        return review

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

    async def _generate_redlines(
        self, chunks: list, findings: list[RiskFinding], provider: OpenAIProvider,
    ) -> list[RedlineSuggestion]:
        """Generate redline suggestions for actionable findings (critical/high/medium).

        Integrates with the Clause Playbook to inject approved/preferred/fallback
        language into the AI prompt, ensuring redlines align with company standards.
        """
        eligible = _findings_eligible_for_redlines(findings)
        if not eligible and findings:
            logger.info(
                "No findings eligible for redlines (%d findings; severities=%s)",
                len(findings),
                sorted({f.severity for f in findings}),
            )
        redlines = []

        # Initialize playbook context provider for approved language injection
        from app.domains.playbook.context_provider import PlaybookContextProvider
        playbook_provider = PlaybookContextProvider(self.ai_repo.session, self.tenant_id)

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

            # Fetch playbook context for this clause type (approved/preferred/fallback language)
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

            # Use v4 prompt — playbook-aware, forbids section numbering, returns risk traceability
            prompt = prompt_registry.render(
                "redline_generation", version=4,
                clause_type=finding.clause_type,
                original_text=relevant_text[:2000],
                context=f"Risk: {finding.title}\nDescription: {finding.description}",
                playbook_context=playbook_context,
            )

            template = prompt_registry.get("redline_generation", version=4)
            request = LLMRequest(
                prompt=prompt,
                system_prompt=template.system_prompt if template else None,
                model=template.model if template else "gpt-4o",
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            try:
                response = await provider.complete(request)
                parsed = StructuredOutputParser.parse_json(response.content)
                if parsed:
                    proposed_text = _coerce_proposed_text(parsed.get("proposed_text", ""))
                    rationale = parsed.get("rationale", "")
                    if not isinstance(rationale, str):
                        rationale = _coerce_proposed_text(rationale)
                    anchor_text = _coerce_proposed_text(parsed.get("anchor_text", ""))
                    original_text = _coerce_proposed_text(parsed.get("original_text", ""))
                    operation = normalize_operation(parsed.get("operation"))
                    if not operation:
                        operation = infer_operation(
                            original_text,
                            proposed_text,
                            clause_type=finding.clause_type,
                        )
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
                    # For modification/replace: if no anchor, use a snippet of original_text
                    if not anchor_text.strip() and original_text.strip():
                        anchor_text = original_text.strip()[:200]

                    # Strip AI-hallucinated section numbers from insert proposed_text
                    if operation == RedlineOperation.INSERT:
                        proposed_text = _strip_section_numbers(proposed_text)

                    if not proposed_text.strip():
                        logger.warning(
                            "Redline LLM returned empty proposed_text for %s",
                            finding.clause_type,
                        )
                        continue

                    # Calibrated confidence — derived from operation quality signals,
                    # not from the LLM's self-reported score (which is always ~0.85).
                    confidence = _calibrate_confidence(
                        operation=operation.value,
                        severity=str(finding.severity.value if hasattr(finding.severity, "value") else finding.severity),
                        anchor_text=anchor_text,
                        proposed_text=proposed_text,
                        original_text=original_text,
                    )

                    # Capture risk traceability chain from v3 prompt output
                    traceability = RiskTraceability(
                        detected_risk=str(parsed.get("detected_risk", "") or ""),
                        business_impact=str(parsed.get("business_impact", "") or ""),
                        mitigation_strategy=str(parsed.get("mitigation_strategy", "") or ""),
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
            except Exception as exc:
                logger.warning("Redline generation failed for %s: %s", finding.clause_type, exc)
                continue

        logger.info(
            "Generated %d redlines from %d findings (%d eligible)",
            len(redlines),
            len(findings),
            len(eligible),
        )
        return redlines

    def _build_analysis_result(self, parsed: Optional[dict], model: str) -> AnalysisResult:
        """Build structured AnalysisResult from parsed LLM output."""
        if not parsed:
            return AnalysisResult(model_used=model, confidence=0.0)

        findings = []
        for f in parsed.get("findings", []):
            # Coerce confidence to float — the AI sometimes returns strings
            raw_conf = f.get("confidence", 0.5)
            if isinstance(raw_conf, str):
                conf_map = {"critical": 0.95, "high": 0.85, "medium": 0.65, "low": 0.40}
                normalized = raw_conf.strip().lower()
                if normalized in conf_map:
                    confidence = conf_map[normalized]
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

            findings.append(RiskFinding(
                clause_type=f.get("clause_type", "other"),
                severity=f.get("severity", "info"),
                title=f.get("title", ""),
                description=f.get("description", ""),
                recommendation=f.get("recommendation"),
                confidence=confidence,
                risk_score=f.get("risk_score"),
                chunk_indices=f.get("chunk_indices", []),
            ))

        return AnalysisResult(
            risk_score=parsed.get("risk_score", 0.0),
            summary=parsed.get("summary", ""),
            findings=findings,
            model_used=model,
            confidence=0.9 if findings else 0.0,
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
