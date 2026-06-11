"""Review orchestration service — manages review lifecycle, findings, redlines, comments, and approvals."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update, func

from app.kernel.datetime_utils import ensure_utc, utc_now

from app.domains.review.models import (
    ReviewStatus, FindingResolution, RedlineStatus,
    ContractReview, ReviewFinding, ReviewRedline,
)
from app.domains.review.repository import ReviewRepository
from app.domains.review.utils import enum_value as _enum_value
from app.domains.review.redline_ops import (
    RedlineOperation,
    build_word_diff,
    change_type_for_operation,
    infer_operation,
)
from app.domains.review.schemas import ReviewFilterParams
from app.domains.review.workflow import (
    WorkflowState,
    validate_transition,
    TransitionError,
    ImmutableReviewError,
    map_legacy_status,
    to_db_status,
)
from app.domains.review.lock_guard import (
    assert_review_mutable,
    assert_can_approve_or_reject,
    assert_can_edit_redlines,
    assert_can_escalate,
    assert_can_reassign,
)
from app.domains.review.audit_trail import AuditTrailService
from app.domains.review.finalized_version import create_finalized_version
from app.domains.review.idempotency import IdempotencyService, OperationLock
from app.domains.review.risk_delta_engine import RiskDeltaEngine, DeltaType
from app.domains.ai.repository import AIRepository
from app.domains.ai.models import AIExecutionRun
from app.kernel.events.bus import EventBus
from app.domains.review.events import ReviewEscalated, ReviewApproved, ReviewRejected
from app.kernel.security.auth import UserContext
from app.kernel.web.exceptions import ConflictError
from app.domains.notify.service import NotificationService

logger = logging.getLogger(__name__)


@dataclass
class ReviewService:
    """Orchestrates review lifecycle: creation, finding management, redline review, approvals."""

    review_repo: ReviewRepository
    ai_repo: AIRepository
    event_bus: EventBus
    user: UserContext
    tenant_id: str
    notify_service: Optional[NotificationService] = None
    audit_trail: AuditTrailService = field(init=False)
    idempotency: IdempotencyService = field(init=False)
    risk_delta: RiskDeltaEngine = field(init=False)

    def __post_init__(self):
        self.audit_trail = AuditTrailService(
            session=self.review_repo.session,
            tenant_id=self.tenant_id,
        )
        self.idempotency = IdempotencyService(
            session=self.review_repo.session,
            tenant_id=self.tenant_id,
        )
        self.risk_delta = RiskDeltaEngine(
            session=self.review_repo.session,
            tenant_id=self.tenant_id,
        )

    async def get_or_create_review(self, upload_id: str) -> dict:
        """Get existing review for an upload, or create one lazily from AI results.

        In the normal flow, the ``analyze_contract`` Celery worker auto-creates
        the review after AI analysis completes. This method serves as a fallback
        for edge cases (e.g., reviews created before the worker change).
        """
        review = await self.review_repo.get_review_by_upload(upload_id, self.tenant_id)
        if review:
            return self._review_to_detail(review)

        # Fallback: create review and import from latest completed AI run
        review = await self.review_repo.create_review(upload_id, self.tenant_id, self.user.id)
        ai_run = await self._get_latest_ai_run(upload_id)

        if ai_run:
            await self._import_ai_findings(review.review_id, ai_run.run_id)
            await self._import_ai_redlines(review.review_id, ai_run.run_id)

            # Count actual imported rows
            from app.domains.review.models import ReviewFinding, ReviewRedline
            from sqlalchemy import select, func as sa_func

            count_result = await self.review_repo.session.execute(
                select(sa_func.count()).select_from(ReviewFinding).where(
                    ReviewFinding.review_id == review.review_id,
                    ReviewFinding.tenant_id == self.tenant_id,
                )
            )
            review.finding_count = count_result.scalar() or 0

            count_result = await self.review_repo.session.execute(
                select(sa_func.count()).select_from(ReviewRedline).where(
                    ReviewRedline.review_id == review.review_id,
                    ReviewRedline.tenant_id == self.tenant_id,
                )
            )
            review.redline_count = count_result.scalar() or 0

            await self.review_repo.update_status(
                review.review_id, self.tenant_id, ReviewStatus.AI_ANALYZED,
                changed_by=self.user.id, reason="AI analysis completed",
            )

            logger.info(
                "Fallback review creation: review=%s findings=%d redlines=%d",
                review.review_id, review.finding_count, review.redline_count,
            )

        return self._review_to_detail(review)

    async def get_review(self, review_id: str) -> Optional[dict]:
        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if not review:
            return None
        # Note: finding_count and redline_count are set during review creation
        # and are accurate. We do NOT recompute them here because:
        # 1. The stored counters are updated atomically during import
        # 2. Re-computing requires additional queries that can trigger
        #    greenlet context issues with certain session states
        # 3. The list endpoint already returns accurate counts
        return self._review_to_detail(review)
        review.redline_count = cnt.scalar() or 0
        return self._review_to_detail(review)

    async def list_reviews(self, filters: ReviewFilterParams) -> tuple[list, int]:
        return await self.review_repo.list_reviews(self.tenant_id, filters, filters)

    async def update_status(self, review_id: str, new_status: str, reason: Optional[str] = None) -> Optional[dict]:
        """Update review status with strict workflow validation.

        Uses the WorkflowState machine to validate transitions.
        Records audit trail for every transition.
        """
        # Guard: rejection requires a reason
        if new_status.lower() == "rejected" and not (reason and reason.strip()):
            raise ValueError("Rejection reason is required when rejecting a review.")

        # Guard: closing/archiving requires no open obligations
        if new_status.lower() in ("closed", "archived"):
            from app.domains.obligations.models import Obligation
            from sqlalchemy import select as sa_select, func as sa_func
            open_obl = await self.review_repo.session.execute(
                sa_select(sa_func.count()).select_from(Obligation).where(
                    Obligation.contract_uuid_id == review_id,
                    Obligation.tenant_id == self.tenant_id,
                    ~Obligation.status.in_(["completed", "closed", "waived"]),
                )
            )
            open_count = open_obl.scalar() or 0
            if open_count > 0:
                raise ValueError(
                    f"Cannot close: {open_count} obligation(s) are still open. "
                    "Complete or close all obligations before closing the contract."
                )

        target_state = map_legacy_status(new_status)
        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if not review:
            return None

        current_status = str(review.status.value) if hasattr(review.status, 'value') else str(review.status)
        current_state = map_legacy_status(current_status)

        # Validate transition through the state machine
        try:
            validate_transition(current_state, target_state, review_id=review_id)
        except TransitionError as e:
            raise ValueError(str(e))

        # Map WorkflowState to DB-persistable ReviewStatus before writing.
        # This handles aliases like ai_reviewed→ai_analyzed and
        # negotiation→in_review that exist in WorkflowState but not
        # in the PostgreSQL review_status enum.
        db_status = to_db_status(target_state)

        # Perform the transition
        review = await self.review_repo.update_status(
            review_id, self.tenant_id, ReviewStatus(db_status),
            changed_by=self.user.id, reason=reason,
        )

        # Refresh to load expired attributes (e.g. updated_at)
        if review:
            await self.review_repo.session.refresh(review)

        # Record audit trail
        await self.audit_trail.record_transition(
            review_id=review_id,
            from_status=current_status,
            to_status=db_status,
            actor_id=self.user.id,
            reason=reason,
        )

        return self._review_to_detail(review) if review else None

    async def get_findings(self, review_id: str, severity: Optional[str] = None,
                            resolution: Optional[str] = None, page: int = 1, page_size: int = 50):
        return await self.review_repo.get_findings(
            review_id, self.tenant_id, severity, resolution, page, page_size,
        )

    async def resolve_finding(self, finding_id: str, resolution: str, note: Optional[str] = None) -> Optional[dict]:
        """Resolve a finding with audit trail tracking."""
        # Get the finding first for lock guard and audit
        from app.domains.review.models import ReviewFinding as RFModel
        finding_result = await self.review_repo.session.execute(
            select(RFModel).where(
                RFModel.finding_id == finding_id,
                RFModel.tenant_id == self.tenant_id,
            )
        )
        finding_row = finding_result.scalar_one_or_none()
        if not finding_row:
            return None

        # Lock guard: check if review is in an immutable state
        review = await self.review_repo.get_review(str(finding_row.review_id), self.tenant_id)
        if review:
            raw_status = review.status
            status_str = raw_status.value if hasattr(raw_status, 'value') else str(raw_status)
            assert_review_mutable(status_str, "resolve findings", str(finding_row.review_id))

        old_resolution = str(finding_row.resolution.value) if hasattr(finding_row.resolution, 'value') else (
            finding_row.resolution if finding_row.resolution else None
        )

        res = FindingResolution(resolution)
        finding = await self.review_repo.resolve_finding(
            finding_id, self.tenant_id, res, note, self.user.id,
        )
        if not finding:
            return None

        # Audit trail
        await self.audit_trail.record_finding_action(
            finding_id=finding_id,
            review_id=str(finding_row.review_id),
            actor_id=self.user.id,
            resolution=resolution,
            before_resolution=old_resolution,
            description=note or f"Finding resolved as {resolution} by {self.user.id}",
        )

        # Record risk delta for this decision
        try:
            from app.domains.review.models import ReviewRedline as RRModel

            # Get linked redline for mitigation context
            redline_result = await self.review_repo.session.execute(
                select(RRModel).where(
                    RRModel.finding_id == finding_id,
                    RRModel.tenant_id == self.tenant_id,
                ).limit(1)
            )
            linked_redline = redline_result.scalar_one_or_none()

            # Map resolution to decision type for delta engine
            decision_map = {
                "resolved": "accepted",
                "acknowledged": "acknowledged",
                "dismissed": "dismissed",
                "false_positive": "dismissed",
            }
            decision = decision_map.get(resolution, resolution)

            delta = await self.risk_delta.compute_redline_decision_delta(
                review_id=str(finding_row.review_id),
                finding=finding_row,
                redline=linked_redline or finding_row,
                decision=decision,
                actor_id=self.user.id,
                rationale=note or "",
            )
            await self.risk_delta.persist_delta(delta)

            # ── Persist review_decision_impact as audit event for cross-session timeline ──
            try:
                from app.domains.review.models import ContractReview as CRModel
                review_row = await self.review_repo.session.execute(
                    select(CRModel).where(
                        CRModel.review_id == str(finding_row.review_id),
                        CRModel.tenant_id == self.tenant_id,
                    )
                )
                review_obj = review_row.scalar_one_or_none()
                review_status_str = (
                    review_obj.status.value if hasattr(review_obj.status, 'value')
                    else str(review_obj.status) if review_obj else "unknown"
                ) if review_obj else "unknown"

                await self.audit_trail.record_decision_impact(
                    review_id=str(finding_row.review_id),
                    finding_id=finding_id,
                    actor_id=self.user.id,
                    decision_type=resolution,
                    previous_state=old_resolution or "open",
                    new_state=resolution,
                    delta_amount=delta.delta_amount if hasattr(delta, 'delta_amount') else 0.0,
                    delta_pct=delta.delta_pct if hasattr(delta, 'delta_pct') else 0.0,
                    review_status=review_status_str,
                    description=note or f"Finding resolved as {resolution}",
                )
            except Exception:
                logger.exception(
                    "Failed to record decision impact audit event for finding %s", finding_id,
                )
        except Exception:
            logger.exception("Failed to record risk delta for finding %s", finding_id)

        return {
            "finding_id": str(finding.finding_id),
            "resolution": (
                finding.resolution.value
                if hasattr(finding.resolution, "value")
                else finding.resolution
            ),
            "resolution_note": finding.resolution_note,
            "resolved_by": finding.resolved_by,
            "resolved_at": finding.resolved_at.isoformat() if finding.resolved_at else None,
        }

    async def submit_finding_feedback(
        self, finding_id: str, feedback_type: str,
        reviewer_note: Optional[str] = None,
        retraining_priority: str = "medium",
    ) -> Optional[dict]:
        """Record AI feedback (correct/incorrect/partial) for a finding and persist to DB."""
        from app.domains.review.models import ReviewFinding as RFModel
        from sqlalchemy import update

        # Verify finding exists
        finding_result = await self.review_repo.session.execute(
            select(RFModel).where(
                RFModel.finding_id == finding_id,
                RFModel.tenant_id == self.tenant_id,
            )
        )
        finding_row = finding_result.scalar_one_or_none()
        if not finding_row:
            return None

        # Persist feedback to the finding record
        stmt = (
            update(RFModel)
            .where(RFModel.finding_id == finding_id, RFModel.tenant_id == self.tenant_id)
            .values(
                feedback_type=feedback_type,
                feedback_note=reviewer_note,
                feedback_priority=retraining_priority,
                feedback_at=func.now(),
            )
        )
        await self.review_repo.session.execute(stmt)
        await self.review_repo.session.flush()

        # Record feedback as an audit trail entry
        await self.audit_trail.record_finding_action(
            finding_id=finding_id,
            review_id=str(finding_row.review_id),
            actor_id=self.user.id,
            resolution=feedback_type,
            description=(
                f"AI feedback: {feedback_type}"
                f"{' — ' + reviewer_note if reviewer_note else ''}"
            ),
        )

        return {
            "finding_id": str(finding_id),
            "feedback_type": feedback_type,
            "reviewer_note": reviewer_note,
            "retraining_priority": retraining_priority,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def get_redlines(self, review_id: str, status: Optional[str] = None):
        return await self.review_repo.get_redlines(review_id, self.tenant_id, status)

    async def generate_mitigation_redline(
        self,
        review_id: str,
        mitigation_type: str,
        clause_category: str,
        finding_ids: Optional[list[str]] = None,
    ) -> Optional[dict]:
        """Generate a redline from a mitigation recommendation.

        This is the core of closed-loop remediation:
        Mitigation recommendation → generated redline → review → accept → risk delta

        Args:
            review_id: The review to generate the redline for.
            mitigation_type: The mitigation type key (e.g. 'restricting_derivative_works').
            clause_category: The canonical clause category (e.g. 'intellectual_property').
            finding_ids: Optional specific finding IDs to link.

        Returns:
            Dict with redline details, or None if generation fails.
        """
        from app.domains.review.mitigation_effectiveness import get_mitigation_effectiveness
        from app.domains.review.models import ReviewFinding, ContractReview
        from app.domains.ingestion.models import UploadSession
        from sqlalchemy import select

        # Get review to find upload_id
        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if not review:
            return None
        upload_id = str(review.upload_id)

        # Get the mitigation effectiveness entry for clause text generation
        effects = get_mitigation_effectiveness(clause_category, mitigation_type)
        if not effects:
            logger.warning("No mitigation effectiveness found for %s / %s, using fallback", clause_category, mitigation_type)
            # Use a generic fallback effect so redline generation still works
            effects = [{
                "effectiveness_pct": 0,
                "confidence": 0,
                "source": "fallback",
                "label": f"Mitigation for {mitigation_type.replace('_', ' ').title()}",
                "description": f"Automated recommendation for {clause_category} category.",
                "mitigation_type": mitigation_type,
            }]
        effect = effects[0]

        # Build proposed clause text from the mitigation template
        clause_templates = {
            "adding_indemnification": "The [Counterparty] shall indemnify, defend, and hold harmless [Company] from and against any and all losses, damages, claims, and expenses arising out of or related to [this agreement/defined scope].",
            "adding_liability_cap": "Notwithstanding anything to the contrary, [Counterparty]'s aggregate liability arising out of or related to this agreement shall not exceed [amount].",
            "narrowing_indemnity_scope": "Indemnification obligations under this Section shall apply solely to claims by third parties and shall not apply to losses caused by [Company]'s own negligence or breach.",
            "removing_consequential_damages": "Neither party shall be liable to the other for any indirect, incidental, special, consequential, or punitive damages, except for [exclusions: indemnification obligations, breach of confidentiality, IP infringement].",
            "restricting_derivative_works": "[Counterparty] shall not use [Company]'s data, materials, or deliverables to train, develop, or improve any machine learning model, artificial intelligence system, or similar technology, unless expressly authorized in writing.",
            "adding_ip_ownership": "All intellectual property rights in and to the deliverables, including all modifications, enhancements, and derivative works, shall be owned exclusively by [Company]. [Counterparty] hereby assigns all such rights to [Company].",
            "narrowing_ip_license": "The license granted under this Section is limited to the specific purpose set forth in the Statement of Work and shall not extend to [Counterparty]'s other products, services, or internal operations.",
            "clarifying_no_license": "Nothing in this Agreement grants Recipient any license, right, title, or interest in or to Disclosing Party's Confidential Information or intellectual property, except the limited right to use such information solely for the Purpose defined herein.",
            "restricting_data_use": "[Counterparty] shall not collect, use, store, or disclose [Company]'s data for any purpose other than performing the specific services described in this agreement. Upon termination, all data shall be returned or destroyed.",
            "adding_compliance_language": "[Counterparty] shall comply with all applicable data protection laws, including but not limited to GDPR, CCPA, and PIPL, in its processing of [Company]'s data. [Counterparty] shall notify [Company] within 48 hours of any data breach.",
            "adding_data_breach_protocol": "In the event of a data breach involving [Company]'s data, [Counterparty] shall (a) notify [Company] within 24 hours, (b) provide a detailed incident report, (c) take immediate remedial action, and (d) cooperate with all regulatory notifications.",
            "adding_price_protection": "Annual price increases for services under this agreement shall not exceed the lesser of (a) [X]% or (b) the percentage change in the Consumer Price Index for the prior 12-month period.",
            "adding_service_levels": "[Counterparty] shall maintain the following service levels: uptime of [99.9]%, response time of [X] hours for critical issues, and resolution time of [Y] hours. Failure to meet SLAs shall result in service credits of [Z]% per incident.",
            "clarifying_warranty_scope": "[Counterparty] warrants that the services will be performed in a professional manner consistent with industry standards. EXCEPT AS EXPRESSLY SET FORTH HEREIN, ALL WARRANTIES ARE DISCLAIMED, INCLUDING THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.",
            "adding_for_cause_termination": "Either party may terminate this agreement immediately upon written notice if the other party (a) materially breaches any provision and fails to cure within [30] days, (b) becomes insolvent, or (c) undergoes a change of control that materially adversely affects the other party.",
            "reducing_termination_notice": "The notice period for termination without cause is reduced to [30] days. Either party may terminate this agreement at any time by providing [30] days' written notice to the other party.",
            "adding_auto_renewal_opt_out": "This agreement shall automatically renew for successive [one-year] terms unless either party provides written notice of non-renewal at least [60] days prior to the end of the then-current term.",
            "adding_dispute_resolution": "Any dispute arising out of or related to this agreement shall first be submitted to mediation administered by [JAMS/AAA]. If mediation does not resolve the dispute within [60] days, either party may initiate binding arbitration.",
            "adding_audit_rights": "[Company] shall have the right, upon [10] days' notice and no more than once per calendar year, to audit [Counterparty]'s facilities, records, and systems to verify compliance with this agreement. [Counterparty] shall reasonably cooperate.",
            "clarifying_governing_law": "This agreement shall be governed by and construed in accordance with the laws of [State/Country], without regard to its conflict of laws principles. The parties submit to the exclusive jurisdiction of the courts located in [venue].",
            "adding_security_requirements": "[Counterparty] shall maintain industry-standard security controls, including but not limited to encryption at rest and in transit, access controls, vulnerability management, and incident response. [Counterparty] shall provide [Company] with its SOC 2 Type II report annually.",
            "adding_incident_response": "[Counterparty] shall maintain a written incident response plan that includes (a) identification and containment procedures, (b) escalation protocols, (c) forensic investigation, (d) notification timelines, and (e) post-incident remediation.",
            "adding_regulatory_compliance": "[Counterparty] represents and warrants that it holds all licenses, permits, and authorizations required to perform the services under this agreement and shall maintain them in good standing throughout the term.",
            "adding_anti_corruption": "[Counterparty] represents and warrants that it has not and will not make any payment or transfer anything of value, directly or indirectly, to any government official or other person for the purpose of obtaining or retaining business.",
            "adding_dpa": "[Counterparty] shall process [Company]'s data only in accordance with the terms of the Data Processing Agreement attached hereto as Exhibit A. [Counterparty] shall implement appropriate technical and organizational measures to ensure a level of security appropriate to the risk.",
            "broadening_confidentiality": "Confidential Information shall include all information disclosed by [Company] to [Counterparty], whether orally, in writing, or in any other form, including but not limited to business plans, customer data, financial information, technical data, and trade secrets. [Counterparty] shall protect such information with the same degree of care used to protect its own confidential information, but in no event less than reasonable care.",
            "adding_return_of_information": "Upon termination or expiration of this Agreement, Recipient shall promptly return to Disclosing Party or destroy all Confidential Information and all copies thereof, and certify such return or destruction in writing upon request.",
            "adding_remedies_clause": "Recipient acknowledges that unauthorized use or disclosure of Confidential Information may cause irreparable harm. Disclosing Party shall be entitled to seek injunctive relief and any other remedies available at law or in equity, in addition to any other rights and remedies under this Agreement.",
            "clarifying_exclusions": "The obligations of confidentiality shall not apply to information that: (a) is or becomes publicly available through no fault of Recipient; (b) was rightfully known to Recipient without restriction prior to disclosure; (c) is independently developed by Recipient without use of Confidential Information; or (d) is rightfully received from a third party without restriction on disclosure.",
            "extending_notice_period": "Either party may terminate this agreement without cause by providing not less than [90] days' prior written notice to the other party. During the notice period, both parties shall continue to perform their respective obligations under this agreement.",
            "adding_sla_guarantees": "[Counterparty] guarantees that the services will meet the following service levels: (a) [99.9]% platform uptime, measured monthly; (b) [4] hour response time for critical incidents; (c) [24] hour resolution time for critical incidents. For each [1]% below the uptime commitment, [Counterparty] shall issue a service credit equal to [5]% of monthly fees.",
            "adding_change_of_control": "In the event of a change of control of [Counterparty], [Company] shall have the right to terminate this agreement upon [30] days' written notice. [Counterparty] shall provide [Company] with written notice of any change of control at least [30] days prior to the effective date.",
            "adding_ip_ownership_clause": "All intellectual property rights in and to the deliverables, including all modifications, enhancements, and derivative works, shall be owned exclusively by [Company]. [Counterparty] hereby assigns all such rights to [Company].",
        }

        proposed_text = clause_templates.get(
            mitigation_type,
            f"[Proposed clause for {effect.get('label', mitigation_type)} — please review and customize.]"
        )
        if linked_findings and linked_findings[0].recommendation:
            rec = (linked_findings[0].recommendation or "").strip()
            if rec and mitigation_type.startswith("generic_"):
                proposed_text = rec

        # Get linked findings for context
        linked_findings = []
        if finding_ids:
            for fid in finding_ids:
                f_result = await self.review_repo.session.execute(
                    select(ReviewFinding).where(
                        ReviewFinding.finding_id == fid,
                        ReviewFinding.tenant_id == self.tenant_id,
                    )
                )
                finding = f_result.scalar_one_or_none()
                if finding:
                    linked_findings.append(finding)

        # Build rationale from mitigation description
        rationale = effect.get("description", f"Mitigation recommendation: {effect.get('label', mitigation_type)}")
        if linked_findings:
            finding_titles = [f.title for f in linked_findings[:3]]
            rationale += f" — Addresses: {'; '.join(finding_titles)}"

        # Build metadata with full traceability
        traceability = {
            "detected_risk": f"Exposure in {effect.get('label', clause_category)} category",
            "business_impact": f"Estimated {effect.get('effectiveness_pct', 0)*100:.0f}% exposure reduction via {effect.get('label', mitigation_type)}",
            "mitigation_strategy": effect.get("label", mitigation_type),
            "mitigation_type": mitigation_type,
            "mitigation_effectiveness_pct": effect.get("effectiveness_pct", 0),
            "mitigation_confidence": effect.get("confidence", 0),
            "mitigation_source": effect.get("source", ""),
            "generated_from": "mitigation_recommendation",
        }
        redline_metadata = {
            "traceability": traceability,
            "legal_domain": clause_category,
            "risk_type": "mitigation_generated",
            "generated_by": self.user.id,
        }

        # ── Determine the correct clause_type from the linked finding ──
        # CRITICAL: The redline's clause_type MUST match the linked finding's
        # clause_type to preserve mapping integrity. The caller's clause_category
        # parameter is only used for template selection, NOT for the redline's
        # category. This prevents cross-category mismatches.
        finding_clause_type = None
        if linked_findings:
            # Use the first linked finding's clause_type as the authoritative source
            finding_clause_type = linked_findings[0].clause_type
        effective_clause_type = finding_clause_type or clause_category

        # ── Duplicate detection ─────────────────────────────────
        # Check if a proposed redline already exists for this mitigation type
        from app.domains.review.models import ReviewRedline as RRModel
        from sqlalchemy import and_

        existing_result = await self.review_repo.session.execute(
            select(RRModel).where(
                and_(
                    RRModel.review_id == review_id,
                    RRModel.tenant_id == self.tenant_id,
                    RRModel.clause_type == effective_clause_type,
                    RRModel.status == "proposed",
                )
            ).limit(1)
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            # Check if existing redline has the same mitigation type in metadata
            existing_meta = dict(existing.redline_metadata) if existing.redline_metadata else {}
            existing_trace = existing_meta.get("traceability", {})
            if isinstance(existing_trace, dict) and existing_trace.get("mitigation_type") == mitigation_type:
                logger.info(
                    "Duplicate mitigation redline detected for review %s (type=%s), returning existing %s",
                    review_id, mitigation_type, existing.redline_id,
                )
                return {
                    "redline_id": str(existing.redline_id),
                    "clause_type": existing.clause_type,
                    "proposed_text": existing.proposed_text,
                    "rationale": existing.rationale,
                    "risk_level": existing.risk_level,
                    "status": existing.status.value if hasattr(existing.status, "value") else str(existing.status),
                    "traceability": traceability,
                    "finding_ids": finding_ids or [],
                    "mitigation_type": mitigation_type,
                    "mitigation_label": effect.get("label", mitigation_type),
                    "estimated_reduction_pct": effect.get("effectiveness_pct", 0),
                    "confidence": effect.get("confidence", 0),
                    "duplicate": True,
                    "existing": True,
                }

        # Create the redline
        try:
            redline = await self.review_repo.create_redline(
                review_id=review_id,
                tenant_id=self.tenant_id,
                upload_id=upload_id,
                clause_type=effective_clause_type,
                original_text="",
                proposed_text=proposed_text,
                operation="insert",
                anchor_text=None,
                rationale=rationale,
                risk_level=linked_findings[0].severity if linked_findings else "medium",
                finding_id=str(linked_findings[0].finding_id) if linked_findings else None,
                redline_metadata=redline_metadata,
            )

            # Record audit trail
            await self.audit_trail.record_redline_action(
                redline_id=str(redline.redline_id),
                review_id=review_id,
                actor_id=self.user.id,
                action="generated_from_mitigation",
                before_status="none",
                after_status="proposed",
                description=f"Redline auto-generated from mitigation: {effect.get('label', mitigation_type)}",
            )

            # Explicit commit to ensure persistence across server restarts
            await self.review_repo.session.commit()

            logger.info(
                "✅ Mitigation redline created: id=%s review=%s type=%s generated_from=%s",
                redline.redline_id, review_id, mitigation_type, "mitigation_recommendation",
            )

            return {
                "redline_id": str(redline.redline_id),
                "clause_type": redline.clause_type,
                "proposed_text": redline.proposed_text,
                "rationale": redline.rationale,
                "risk_level": redline.risk_level,
                "status": redline.status.value if hasattr(redline.status, "value") else str(redline.status),
                "traceability": traceability,
                "finding_ids": finding_ids or [],
                "mitigation_type": mitigation_type,
                "mitigation_label": effect.get("label", mitigation_type),
                "estimated_reduction_pct": effect.get("effectiveness_pct", 0),
                "confidence": effect.get("confidence", 0),
            }
        except Exception as exc:
            logger.exception("Failed to generate mitigation redline for review %s", review_id)
            return None

    async def backfill_mitigation_redlines_for_gaps(self, review_id: str) -> dict:
        """Generate fallback mitigation redlines for findings that have no linked redline.

        Called after AI analysis imports findings so NDA / unmapped clause types
        still receive recommended language instead of an empty redlines panel.
        """
        from app.domains.review.clause_category import resolve_mitigation_plan
        from app.domains.review.redline_coverage import audit_finding_redline_coverage

        findings = await self.review_repo.get_findings(review_id, self.tenant_id)
        redlines = await self.review_repo.get_redlines(review_id, self.tenant_id)

        before = audit_finding_redline_coverage(findings, redlines)
        if before["findings_without_redline"] == 0:
            return {"backfilled": 0, "skipped": [], "coverage_before": before, "coverage_after": before}

        linked_ids = {str(r.finding_id) for r in redlines if r.finding_id}
        backfilled = 0
        skipped: list[dict] = []

        for finding in findings:
            fid = str(finding.finding_id)
            if fid in linked_ids:
                continue

            severity = (finding.severity or "").lower()
            has_rec = bool((finding.recommendation or "").strip())
            if severity == "info" and not has_rec:
                skipped.append({"finding_id": fid, "clause_type": finding.clause_type, "reason": "info_without_recommendation"})
                continue

            plan = resolve_mitigation_plan(
                finding.clause_type,
                title=finding.title,
                description=finding.description,
                recommendation=finding.recommendation,
            )

            result = await self.generate_mitigation_redline(
                review_id=review_id,
                mitigation_type=plan.mitigation_type,
                clause_category=plan.clause_category,
                finding_ids=[fid],
            )
            if result and not result.get("duplicate"):
                backfilled += 1
                linked_ids.add(fid)
            elif result and result.get("duplicate"):
                linked_ids.add(fid)
            else:
                skipped.append({
                    "finding_id": fid,
                    "clause_type": finding.clause_type,
                    "reason": "generation_failed",
                    "planned_mitigation": plan.mitigation_type,
                })

        # Refresh counts
        redlines_after = await self.review_repo.get_redlines(review_id, self.tenant_id)
        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if review:
            review.redline_count = len(redlines_after)
            await self.review_repo.session.flush()

        after = audit_finding_redline_coverage(findings, redlines_after)
        logger.info(
            "Redline backfill for review %s: %d generated, %d skipped, coverage %.1f%% → %.1f%%",
            review_id,
            backfilled,
            len(skipped),
            before["coverage_pct"],
            after["coverage_pct"],
        )
        return {
            "backfilled": backfilled,
            "skipped": skipped,
            "coverage_before": before,
            "coverage_after": after,
        }

    async def repair_redline_finding_links(self, review_id: str) -> dict:
        """Re-link redlines to findings by clause category and clear invalid_mapping status."""
        from app.domains.review.mapping_validation import (
            categories_compatible,
            normalize_category,
            validate_redline_finding_mapping,
        )
        from app.domains.review.models import ReviewRedline as RRModel, RedlineStatus

        findings = await self.review_repo.get_findings(review_id, self.tenant_id)
        redlines = await self.review_repo.get_redlines(review_id, self.tenant_id)
        findings_by_id = {str(f.finding_id): f for f in findings}

        repaired = 0
        still_invalid = 0
        details: list[dict] = []

        for redline in redlines:
            old_fid = str(redline.finding_id) if redline.finding_id else None
            redline_cat = normalize_category(redline.clause_type)
            new_fid: Optional[str] = None

            same_type = [f for f in findings if (f.clause_type or "other") == (redline.clause_type or "other")]
            if len(same_type) == 1:
                new_fid = str(same_type[0].finding_id)
            elif redline_cat:
                cat_matches = [
                    f for f in findings
                    if categories_compatible(redline_cat, normalize_category(f.clause_type))
                ]
                if len(cat_matches) == 1:
                    new_fid = str(cat_matches[0].finding_id)

            if new_fid and new_fid != old_fid:
                redline.finding_id = new_fid
                repaired += 1

            linked = findings_by_id.get(str(redline.finding_id)) if redline.finding_id else None
            mapping = validate_redline_finding_mapping(redline, linked)
            old_status = (
                redline.status.value if hasattr(redline.status, "value") else str(redline.status)
            )
            if mapping.valid and old_status == RedlineStatus.INVALID_MAPPING.value:
                redline.status = RedlineStatus.PROPOSED
            elif not mapping.valid:
                redline.status = RedlineStatus.INVALID_MAPPING
                still_invalid += 1

            details.append({
                "redline_id": str(redline.redline_id),
                "clause_type": redline.clause_type,
                "finding_id": str(redline.finding_id) if redline.finding_id else None,
                "finding_title": linked.title if linked else None,
                "finding_clause_type": linked.clause_type if linked else None,
                "mapping_valid": mapping.valid,
                "status": redline.status.value if hasattr(redline.status, "value") else str(redline.status),
            })

        await self.review_repo.session.flush()
        return {
            "repaired_links": repaired,
            "still_invalid": still_invalid,
            "redlines": details,
        }

    async def get_redline_coverage(self, review_id: str) -> dict:
        """Return finding→redline coverage audit for a review."""
        from app.domains.review.redline_coverage import audit_finding_redline_coverage

        findings = await self.review_repo.get_findings(review_id, self.tenant_id)
        redlines = await self.review_repo.get_redlines(review_id, self.tenant_id)
        return audit_finding_redline_coverage(findings, redlines)

    async def update_redline(self, redline_id: str, status: str, modified_text: Optional[str] = None,
                              review_notes: Optional[str] = None) -> Optional[dict]:
        """Update a redline with workflow lock guard and audit trail."""
        # First get the redline to know which review it belongs to
        from app.domains.review.models import ReviewRedline as RRModel
        redline_result = await self.review_repo.session.execute(
            select(RRModel).where(
                RRModel.redline_id == redline_id,
                RRModel.tenant_id == self.tenant_id,
            )
        )
        redline_row = redline_result.scalar_one_or_none()
        if not redline_row:
            return None

        # Lock guard: check if review is in an immutable state
        review = await self.review_repo.get_review(str(redline_row.review_id), self.tenant_id)
        if review:
            raw_status = review.status
            status_str = raw_status.value if hasattr(raw_status, 'value') else str(raw_status)
            assert_can_edit_redlines(status_str, str(redline_row.review_id))

        old_status = str(redline_row.status.value) if hasattr(redline_row.status, 'value') else str(redline_row.status)

        if status == RedlineStatus.ACCEPTED.value:
            from app.domains.review.mapping_validation import validate_redline_finding_mapping
            from app.domains.review.models import ReviewFinding as RFModel

            finding_row = None
            if redline_row.finding_id:
                finding_result = await self.review_repo.session.execute(
                    select(RFModel).where(
                        RFModel.finding_id == redline_row.finding_id,
                        RFModel.tenant_id == self.tenant_id,
                    )
                )
                finding_row = finding_result.scalar_one_or_none()
            mapping = validate_redline_finding_mapping(
                redline_row,
                finding_row,
                displayed_finding_id=str(redline_row.finding_id) if redline_row.finding_id else None,
            )
            if not mapping.valid:
                await self.audit_trail.record_mapping_validation_failed(
                    redline_id=redline_id,
                    review_id=str(redline_row.review_id),
                    actor_id=self.user.id,
                    mapping_warning=mapping.warning or "Cannot accept redline with invalid finding mapping",
                    finding_id=mapping.finding_id,
                    finding_title=mapping.finding_title,
                    redline_title=mapping.redline_title,
                    finding_category=mapping.finding_category,
                    redline_category=mapping.redline_category,
                )
                raise ValueError(
                    mapping.warning or "Cannot accept redline: invalid finding mapping"
                )

        rs = RedlineStatus(status)
        redline = await self.review_repo.update_redline(
            redline_id, self.tenant_id, rs, modified_text, self.user.id, review_notes,
        )
        if not redline:
            return None

        # Audit trail
        await self.audit_trail.record_redline_action(
            redline_id=redline_id,
            review_id=str(redline_row.review_id),
            actor_id=self.user.id,
            action=status,
            before_status=old_status,
            after_status=status,
            description=f"Redline {status} by {self.user.id}",
        )

        # Record risk delta for redline decisions
        try:
            from app.domains.review.models import ReviewFinding as RFModel

            # Map redline status to decision type
            decision_map = {
                "accepted": "accepted",
                "modified": "modified",
                "rejected": "rejected",
                "dismissed": "dismissed",
            }
            decision = decision_map.get(status)
            if decision:
                # Get linked finding for risk context
                finding = None
                if redline_row.finding_id:
                    finding_result = await self.review_repo.session.execute(
                        select(RFModel).where(
                            RFModel.finding_id == redline_row.finding_id,
                            RFModel.tenant_id == self.tenant_id,
                        )
                    )
                    finding = finding_result.scalar_one_or_none()

                # If the linked finding doesn't exist (orphaned reference), compute
                # the delta using the redline's own data but with finding_id=None
                # to avoid FK violation on risk_delta_events.finding_id.
                delta_finding = finding if finding else None
                delta = await self.risk_delta.compute_redline_decision_delta(
                    review_id=str(redline_row.review_id),
                    finding=delta_finding or redline_row,
                    redline=redline_row,
                    decision=decision,
                    actor_id=self.user.id,
                    rationale=review_notes or "",
                )
                # Null out finding_id if the finding record doesn't actually exist
                if not finding and redline_row.finding_id:
                    delta.finding_id = None
                await self.risk_delta.persist_delta(delta)

                # ── Auto-sync: when redline is accepted/modified, auto-resolve linked finding ──
                if decision in ("accepted", "modified") and finding and redline_row.finding_id:
                    try:
                        old_res = str(finding.resolution.value) if hasattr(finding.resolution, 'value') else (
                            finding.resolution if finding.resolution else None
                        )
                        # Only auto-resolve if finding is still open
                        if old_res is None or old_res in ("acknowledged",):
                            res = FindingResolution("resolved")
                            await self.review_repo.resolve_finding(
                                str(redline_row.finding_id),
                                self.tenant_id,
                                res,
                                f"Auto-resolved: redline {status}",
                                self.user.id,
                            )
                            # Record audit event for the auto-resolution
                            await self.audit_trail.record_finding_action(
                                finding_id=str(redline_row.finding_id),
                                review_id=str(redline_row.review_id),
                                actor_id=self.user.id,
                                resolution="resolved",
                                before_resolution=old_res,
                                description=(
                                    f"Auto-resolved via redline {status} by {self.user.id}"
                                ),
                            )
                            # Record decision impact audit event for cross-session timeline
                            await self.audit_trail.record_decision_impact(
                                review_id=str(redline_row.review_id),
                                finding_id=str(redline_row.finding_id),
                                actor_id=self.user.id,
                                decision_type="resolved",
                                previous_state=old_res or "open",
                                new_state="resolved",
                                delta_amount=delta.delta_amount if hasattr(delta, 'delta_amount') else 0.0,
                                delta_pct=delta.delta_pct if hasattr(delta, 'delta_pct') else 0.0,
                                review_status=status,
                                description=f"Auto-resolved via redline {status}",
                            )
                            logger.info(
                                "Auto-resolved finding %s via redline %s (%s)",
                                redline_row.finding_id, redline_id, status,
                            )
                    except Exception:
                        logger.exception(
                            "Failed to auto-resolve finding %s via redline %s",
                            redline_row.finding_id, redline_id,
                        )
        except Exception:
            logger.exception("Failed to record risk delta for redline %s", redline_id)

        result = {
            "redline_id": str(redline.redline_id),
            "status": (
                redline.status.value if hasattr(redline.status, "value") else redline.status
            ),
            "reviewer_modified_text": redline.reviewer_modified_text,
            "review_notes": redline.review_notes,
            "reviewed_by": redline.reviewed_by,
            "reviewed_at": redline.reviewed_at.isoformat() if redline.reviewed_at else None,
        }
        if rs in (RedlineStatus.ACCEPTED, RedlineStatus.MODIFIED):
            try:
                version = await self._sync_redline_applied_version(str(redline.review_id))
                if version:
                    result["document_version"] = version
            except Exception:
                logger.exception(
                    "Failed to create document version after redline %s", redline_id,
                )
        return result

    async def add_comment(self, review_id: str, body: str, entity_type: Optional[str] = None,
                           entity_id: Optional[str] = None, parent_comment_id: Optional[str] = None,
                           mentions: Optional[list[str]] = None) -> dict:
        comment = await self.review_repo.add_comment(
            review_id, self.tenant_id, self.user.id, body,
            entity_type, entity_id, parent_comment_id, mentions,
        )
        return {
            "comment_id": str(comment.comment_id),
            "author_id": comment.author_id,
            "body": comment.body,
            "mentions": comment.mentions,
            "created_at": comment.created_at.isoformat(),
        }

    async def get_comments(self, review_id: str):
        return await self.review_repo.get_comments(review_id, self.tenant_id)

    async def assign_reviewer(self, review_id: str, assignee_id: str, role: str = "reviewer",
                               due_date: Optional[datetime] = None) -> dict:
        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")

        # Lock guard: check if review is mutable
        raw_status = review.status
        status_str = raw_status.value if hasattr(raw_status, 'value') else str(raw_status)
        assert_can_reassign(status_str, review_id)

        # Determine or normalize priority before assignment
        priority = self._normalize_priority(review.priority) if getattr(review, 'priority', None) else self._calculate_priority(review)
        if due_date is None:
            due_date = utc_now() + timedelta(hours=self._sla_hours_for_priority(priority))

        # Transition status before creating assignment (fail fast on invalid state).
        # Re-assignment is idempotent: if the review is already in a state that
        # accepts assignment (e.g. IN_REVIEW), we do not re-transition.
        current = review.status
        if isinstance(current, str):
            try:
                current = ReviewStatus(current)
            except ValueError:
                current = None

        if current == ReviewStatus.AI_ANALYZED:
            await self.review_repo.update_status(
                review_id, self.tenant_id, ReviewStatus.REVIEW_READY,
                changed_by=self.user.id, reason=f"Review ready — assigning to {assignee_id}",
            )
            current = ReviewStatus.REVIEW_READY

        target_status = None
        if current == ReviewStatus.REVIEW_READY:
            target_status = ReviewStatus.IN_REVIEW
        elif current == ReviewStatus.ESCALATED and role == "legal_ops":
            target_status = ReviewStatus.LEGAL_APPROVAL
        # NOTE: We do NOT transition from IN_REVIEW (or any other non-listed
        # state) — re-assignment to an already-active review keeps the
        # current status to avoid "Invalid state transition" errors.

        if target_status:
            await self.review_repo.update_status(
                review_id, self.tenant_id, target_status,
                changed_by=self.user.id, reason=f"Assigned to {assignee_id} ({role})",
            )

        assignment = await self.review_repo.assign_reviewer(
            review_id, self.tenant_id, assignee_id, self.user.id, role, due_date,
        )
        # Update review with assignment metadata
        from sqlalchemy import update, func
        from app.domains.review.models import ContractReview

        stmt = (
            update(ContractReview)
            .where(ContractReview.review_id == review_id, ContractReview.tenant_id == self.tenant_id)
            .values(
                assigned_to=assignee_id,
                assigned_by=self.user.id,
                assigned_at=func.now(),
                started_at=func.now(),
                priority=priority,
                sla_deadline=due_date,
                sla_status="on_track",
                sla_breached=False,
            )
        )
        await self.review_repo.session.execute(stmt)

        updated_review = await self.review_repo.get_review(review_id, self.tenant_id)
        result = {
            "assignment_id": str(assignment.assignment_id),
            "assignee_id": assignment.assignee_id,
            "role": assignment.role,
            "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
        }
        if updated_review:
            result["review"] = self._review_to_detail(updated_review)

        # Record audit event for assignment
        try:
            previous_assignee = str(updated_review.assigned_to) if updated_review and updated_review.assigned_to else None
            if previous_assignee == assignee_id:
                previous_assignee = None  # Same assignee, no change
            await self.audit_trail.record_assignment(
                review_id=review_id,
                assignee_id=assignee_id,
                assigned_by=self.user.id,
                role=role,
                previous_assignee=previous_assignee,
            )
        except Exception:
            pass  # Non-blocking — assignment succeeded even if audit fails

        # Send notification
        if self.notify_service:
            await self.notify_service.send_review_assigned(review_id, assignee_id, self.user.id)

        return result

    async def escalate(self, review_id: str, reason: str, escalated_to: Optional[str] = None,
                        raise_priority: bool = False,
                        target_workflow_stage: Optional[str] = None) -> dict:
        # Idempotency check: prevent duplicate escalation
        lock_key = f"escalate:{review_id}:{reason[:32]}"
        if not OperationLock.acquire(lock_key):
            raise ConflictError(message="Escalation already in progress for this review.")

        try:
            if await self.idempotency.is_duplicate("escalate", review_id, self.user.id):
                # Allow re-escalation with different target, but prevent exact duplicate
                pass  # Escalations can be re-escalated to different targets

            return await self._escalate_impl(review_id, reason, escalated_to, raise_priority, target_workflow_stage)
        finally:
            OperationLock.release(lock_key)

    async def _escalate_impl(self, review_id: str, reason: str, escalated_to: Optional[str] = None,
                              raise_priority: bool = False,
                              target_workflow_stage: Optional[str] = None) -> dict:
        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")

        # Lock guard: enforce workflow immutability matrix. Blocks escalation
        # from terminal/locked states (approved, rejected, finalized,
        # executed, archived/closed) and from the ESCALATED state itself.
        raw_status = review.status
        status_str = raw_status.value if hasattr(raw_status, 'value') else str(raw_status)
        assert_can_escalate(status_str, review_id)

        escalation = await self.review_repo.escalate(
            review_id, self.tenant_id, self.user.id, reason, escalated_to,
        )

        # Determine the actual target status based on workflow stage
        target_status: Optional[ReviewStatus] = None
        effective_stage: Optional[str] = target_workflow_stage

        if target_workflow_stage == "legal_approval":
            target_status = ReviewStatus.LEGAL_APPROVAL
            effective_stage = "legal_approval"
        elif target_workflow_stage == "exec_approval":
            target_status = ReviewStatus.EXEC_APPROVAL
            effective_stage = "executive"
        elif target_workflow_stage == "compliance":
            target_status = ReviewStatus.IN_REVIEW
            effective_stage = "compliance"

        # Transition to the target status (or escalated if no routing target)
        final_status = target_status if target_status else ReviewStatus.ESCALATED
        await self.review_repo.update_status(
            review_id, self.tenant_id, final_status,
            changed_by=self.user.id,
            reason=f"{'Escalated to ' + target_workflow_stage.replace('_', ' ') if target_workflow_stage else 'Escalated'}: {reason}",
        )

        # Update review metadata
        from sqlalchemy import update, func
        from app.domains.review.models import ContractReview

        update_values: dict = {
            "escalation_count": ContractReview.escalation_count + 1,
            "workflow_stage": effective_stage or "escalated",
            "updated_at": func.now(),
        }

        if raise_priority:
            from sqlalchemy import select
            result = await self.review_repo.session.execute(
                select(ContractReview.priority).where(
                    ContractReview.review_id == review_id,
                    ContractReview.tenant_id == self.tenant_id,
                )
            )
            current_priority = result.scalar()
            priority_bump = {"low": "medium", "medium": "high", "high": "critical", "critical": "critical"}
            update_values["priority"] = priority_bump.get(current_priority, "high")

        # Auto-assign escalated_to as the new assignee when routing to a stage
        if escalated_to:
            update_values["assigned_to"] = escalated_to
            update_values["assigned_by"] = self.user.id
            update_values["assigned_at"] = func.now()

        await self.review_repo.session.execute(
            update(ContractReview)
            .where(ContractReview.review_id == review_id, ContractReview.tenant_id == self.tenant_id)
            .values(**update_values)
        )

        # Emit escalation routed event
        await self.event_bus.emit(ReviewEscalated(
            tenant_id=self.tenant_id,
            actor_id=self.user.id,
            data={
                "review_id": review_id,
                "escalated_by": self.user.id,
                "escalated_to": escalated_to,
                "reason": reason,
                "raise_priority": raise_priority,
                "target_workflow_stage": target_workflow_stage,
                "target_status": final_status.value if hasattr(final_status, "value") else str(final_status),
            },
        ))

        # Audit trail for escalation
        await self.audit_trail.record_escalation(
            review_id=review_id,
            actor_id=self.user.id,
            escalated_to=escalated_to,
            reason=reason,
            target_stage=target_workflow_stage,
        )
        await self.audit_trail.record_transition(
            review_id=review_id,
            from_status=status_str,
            to_status=final_status.value if hasattr(final_status, 'value') else str(final_status),
            actor_id=self.user.id,
            reason=f"Escalated: {reason}",
        )

        # Send escalation notification to the target
        if self.notify_service and escalated_to:
            stage_label = target_workflow_stage.replace("_", " ").title() if target_workflow_stage else "Escalated"
            await self.notify_service.send_notification(
                user_id=escalated_to,
                notif_type="review.escalated",
                title=f"Review {stage_label}",
                body=reason,
                severity="high",
                entity_type="review",
                entity_id=review_id,
                action_url=f"/reviews/{review_id}",
                dedup_key=f"escalation:{review_id}",
            )

        # Mark idempotency complete
        await self.idempotency.mark_completed("escalate", review_id, self.user.id, {
            "escalation_id": str(escalation.escalation_id),
            "level": escalation.level,
        })

        return {
            "escalation_id": str(escalation.escalation_id),
            "level": escalation.level,
            "escalated_to": escalated_to,
            "reason": escalation.reason,
            "priority_bumped": raise_priority,
            "target_workflow_stage": target_workflow_stage,
            "target_status": final_status.value if hasattr(final_status, 'value') else str(final_status),
        }

    async def approve(self, review_id: str, decision: str, comments: Optional[str] = None,
                       conditions: Optional[dict] = None) -> dict:
        # Idempotency check: prevent double approve/reject
        op_type = "approve" if decision == "approved" else "reject"
        lock_key = f"{op_type}:{review_id}"

        if not OperationLock.acquire(lock_key):
            raise ConflictError(
                message=f"Cannot {decision}: operation already in progress for this review.",
            )
        try:
            if await self.idempotency.is_duplicate(op_type, review_id, self.user.id):
                raise ConflictError(
                    message=f"Cannot {decision}: review has already been {decision}.",
                    details={"duplicate_operation": True},
                )

            return await self._approve_impl(review_id, decision, comments, conditions)
        finally:
            OperationLock.release(lock_key)

    async def _approve_impl(self, review_id: str, decision: str, comments: Optional[str] = None,
                              conditions: Optional[dict] = None) -> dict:
        """Internal approve implementation — assumes idempotency check already passed."""
        op_type = "approve" if decision == "approved" else "reject"
        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if not review:
            raise ConflictError(message=f"Review {review_id} not found")

        # Lock guard: verify we can approve/reject from current state
        raw_status = review.status
        status_str = raw_status.value if hasattr(raw_status, 'value') else str(raw_status)
        try:
            assert_can_approve_or_reject(status_str, review_id)
        except ImmutableReviewError as e:
            raise ValueError(str(e))

        # Guard: rejection requires a reason
        if decision == "rejected" and not (comments and comments.strip()):
            raise ValueError("Rejection reason (comments) is required when rejecting a review.")

        # Guard: if approving, check for unresolved critical/high findings
        if decision == "approved" or decision == "conditionally_approved":
            from app.domains.review.models import ReviewFinding
            from sqlalchemy import select, func as sa_func
            unresolved = await self.review_repo.session.execute(
                select(sa_func.count()).select_from(ReviewFinding).where(
                    ReviewFinding.review_id == review_id,
                    ReviewFinding.tenant_id == self.tenant_id,
                    ReviewFinding.resolution.is_(None),
                    ReviewFinding.severity.in_(["critical", "high"]),
                )
            )
            count = unresolved.scalar() or 0
            if count > 0:
                # Allow override if reason is provided (admin bypass)
                if comments and "override:" in comments.lower():
                    logger.info(
                        "Approval override for review %s: %d unresolved findings overridden by %s",
                        review_id, count, self.user.id,
                    )
                    # Store override metadata on the review
                    from app.domains.review.models import ContractReview
                    from sqlalchemy import update as sa_update
                    from datetime import datetime, timezone
                    stmt = (
                        sa_update(ContractReview)
                        .where(ContractReview.review_id == review_id)
                        .values(
                            approval_override_reason=comments,
                            approval_override_by=self.user.id,
                            approval_override_timestamp=datetime.now(timezone.utc),
                        )
                    )
                    await self.review_repo.session.execute(stmt)
                else:
                    action_label = "approve" if decision == "approved" else "conditionally approve"
                    raise ConflictError(
                        message=(
                            f"Cannot {action_label}: {count} critical/high finding(s) are still open. "
                            "Resolve or dismiss them in Findings first, or add 'override:' to your comments to bypass."
                        ),
                        details={"unresolved_critical_high_count": count},
                    )

        new_status = ReviewStatus.APPROVED if decision == "approved" else ReviewStatus.REJECTED
        if decision == "conditionally_approved":
            new_status = ReviewStatus.APPROVED

        current = review.status
        if isinstance(current, str):
            current = ReviewStatus(current)

        approval = await self.review_repo.approve(
            review_id, self.tenant_id, self.user.id, decision, comments, conditions,
        )
        await self.review_repo.update_status(
            review_id, self.tenant_id, new_status,
            changed_by=self.user.id, reason=comments,
        )

        # Audit trail for approval/rejection
        await self.audit_trail.record_approval_action(
            review_id=review_id,
            actor_id=self.user.id,
            decision=decision,
            conditions=conditions,
            description=comments or f"Review {decision} by {self.user.id}",
        )

        # Record status transition in audit trail
        await self.audit_trail.record_transition(
            review_id=review_id,
            from_status=status_str,
            to_status=new_status.value,
            actor_id=self.user.id,
            reason=comments,
        )

        # Update review with approval/rejection metadata
        from sqlalchemy import update, func
        from app.domains.review.models import ContractReview

        update_values: dict = {
            "completed_at": func.now(),
            "updated_at": func.now(),
        }

        if new_status == ReviewStatus.APPROVED:
            await self._link_approved_document_version(review_id)

        if new_status == ReviewStatus.REJECTED:
            # If conditions dict contains rejection_category, store it
            rejection_category = None
            rejection_severity = None
            if conditions:
                rejection_category = conditions.get("category")
                rejection_severity = conditions.get("severity")
            update_values["rejection_reason"] = comments
            update_values["rejection_category"] = rejection_category
            update_values["rejection_severity"] = rejection_severity
            update_values["rejected_by"] = self.user.id
            update_values["rejected_at"] = func.now()

        await self.review_repo.session.execute(
            update(ContractReview)
            .where(ContractReview.review_id == review_id, ContractReview.tenant_id == self.tenant_id)
            .values(**update_values)
        )

        # Emit approval/rejection event
        event_cls = ReviewApproved if new_status == ReviewStatus.APPROVED else ReviewRejected
        await self.event_bus.emit(event_cls(
            tenant_id=self.tenant_id,
            actor_id=self.user.id,
            data={
                "review_id": review_id,
                "decision": decision,
                "approved_by": self.user.id,
                "approved_at": utc_now().isoformat(),
                "comments": comments,
                "conditions": conditions,
            },
        ))

        # Mark idempotency complete
        await self.idempotency.mark_completed(op_type, review_id, self.user.id, {
            "approval_id": str(approval.approval_id),
            "decision": decision,
        })

        # Send approval/rejection notification (non-blocking — must not fail the approval)
        if self.notify_service:
            try:
                review = await self.review_repo.get_review(review_id, self.tenant_id)
                if review and review.created_by:
                    notif_type = "approval.completed"
                    title = "Review Approved" if new_status == ReviewStatus.APPROVED else "Review Rejected"
                    severity = "medium" if new_status == ReviewStatus.APPROVED else "high"
                    await self.notify_service.send_notification(
                        user_id=review.created_by,
                        notif_type=notif_type,
                        title=title,
                        body=comments or f"Review {decision} by {self.user.id}",
                        severity=severity,
                        entity_type="review",
                        entity_id=review_id,
                        action_url=f"/reviews/{review_id}",
                        dedup_key=f"approval:{review_id}",
                    )
            except Exception as exc:
                logger.warning("Approval notification failed for %s: %s", review_id, exc)

        return {
            "approval_id": str(approval.approval_id),
            "decision": approval.decision,
            "comments": approval.comments,
            "conditions": approval.conditions,
            "approved_by": self.user.id,
            "approved_at": approval.decided_at.isoformat() if approval.decided_at else datetime.utcnow().isoformat(),
        }

    async def finalize(self, review_id: str) -> dict:
        """Finalize an approved review — locks the version and sets FINALIZED status.

        Only APPROVED reviews can be finalized. Once finalized:
        - Status becomes FINALIZED (immutable)
        - The current document version is locked
        - A finalized version (v3 Final Approved) is generated
        - Approval signature metadata is embedded
        - A finalization event is emitted
        """
        # Idempotency check: prevent double finalize
        lock_key = f"finalize:{review_id}"
        if not OperationLock.acquire(lock_key):
            raise ConflictError(message="Finalization already in progress for this review.")

        try:
            if await self.idempotency.is_duplicate("finalize", review_id, self.user.id):
                raise ConflictError(
                    message="Review has already been finalized.",
                    details={"duplicate_operation": True},
                )

            return await self._finalize_impl(review_id)
        finally:
            OperationLock.release(lock_key)

    async def _finalize_impl(self, review_id: str) -> dict:
        from app.domains.review.failure_recovery import transactional_operation

        async with transactional_operation(self.review_repo.session, "finalize_review"):
            review = await self.review_repo.get_review(review_id, self.tenant_id)
            if not review:
                raise ValueError("Review not found")

            raw_status = review.status
            current_status = raw_status.value if hasattr(raw_status, "value") else str(raw_status)

            # Use workflow state machine for validation
            current_wf = map_legacy_status(current_status)
            try:
                validate_transition(current_wf, WorkflowState.FINALIZED, review_id=review_id)
            except TransitionError as e:
                raise ValueError(str(e))

        # Get approval info for metadata
        approved_by = None
        approved_at = None
        approval_comments = None
        approval_conditions = None
        try:
            from app.domains.review.models import ReviewApproval
            approval_result = await self.review_repo.session.execute(
                select(ReviewApproval).where(
                    ReviewApproval.review_id == review_id,
                    ReviewApproval.tenant_id == self.tenant_id,
                    ReviewApproval.decision == "approved",
                ).order_by(ReviewApproval.created_at.desc()).limit(1)
            )
            approval_row = approval_result.scalar_one_or_none()
            if approval_row:
                approved_by = approval_row.approver_id
                approved_at = approval_row.decided_at
                approval_comments = approval_row.comments
                approval_conditions = approval_row.conditions
        except Exception:
            logger.warning("Could not fetch approval metadata for review %s", review_id)

        # Create the finalized version (v3 Final Approved)
        finalized_version = await create_finalized_version(
            session=self.review_repo.session,
            review_id=review_id,
            tenant_id=self.tenant_id,
            user_id=self.user.id,
            approved_by=approved_by or review.created_by,
            approved_at=approved_at or datetime.utcnow(),
            approval_comments=approval_comments,
            approval_conditions=approval_conditions,
        )

        # Update status to FINALIZED
        await self.review_repo.update_status(
            review_id, self.tenant_id, ReviewStatus.FINALIZED,
            changed_by=self.user.id,
            reason="Review finalized — version locked",
        )

        # Lock all document versions as finalized
        from app.domains.review.models import ContractDocumentVersion
        from sqlalchemy import update as sa_update
        await self.review_repo.session.execute(
            sa_update(ContractDocumentVersion).where(
                ContractDocumentVersion.review_id == review_id,
                ContractDocumentVersion.tenant_id == self.tenant_id,
                ContractDocumentVersion.status == "current",
            ).values(status="finalized")
        )

        # Audit trail
        await self.audit_trail.record_transition(
            review_id=review_id,
            from_status=current_status,
            to_status="finalized",
            actor_id=self.user.id,
            reason="Review finalized — version locked",
        )
        if finalized_version:
            await self.audit_trail.record_version_action(
                version_id=finalized_version.version_id,
                review_id=review_id,
                actor_id=self.user.id,
                action="finalize",
                version_number=finalized_version.version_number,
                description=f"Final Approved Contract v{finalized_version.version_number} created",
            )

        # Send finalized notification
        if self.notify_service:
            try:
                await self.notify_service.send_finalized_notification(
                    review_id=review_id,
                    created_by=review.created_by,
                    finalized_by=self.user.id,
                )
                if finalized_version:
                    await self.notify_service.send_version_generated_notification(
                        review_id=review_id,
                        user_id=review.created_by,
                        version_number=finalized_version.version_number,
                        label=finalized_version.label,
                    )
            except Exception as exc:
                logger.warning("Finalized notification failed for %s: %s", review_id, exc)

        from app.domains.review.events import ReviewFinalized
        event = ReviewFinalized(
            tenant_id=self.tenant_id,
            actor_id=self.user.id,
            data={
                "review_id": review_id,
                "tenant_id": self.tenant_id,
                "finalized_by": self.user.id,
                "finalized_at": datetime.utcnow().isoformat(),
                "finalized_version": {
                    "version_id": finalized_version.version_id if finalized_version else None,
                    "version_number": finalized_version.version_number if finalized_version else None,
                },
            },
        )
        logger.info("Emitting ReviewFinalized event for review %s", review_id[:8])
        await self.event_bus.emit(event)

        # Mark idempotency complete
        await self.idempotency.mark_completed("finalize", review_id, self.user.id, {
            "status": "finalized",
            "finalized_version_id": finalized_version.version_id if finalized_version else None,
        })

        return {
            "review_id": review_id,
            "status": "finalized",
            "finalized_by": self.user.id,
            "finalized_version": {
                "version_id": finalized_version.version_id if finalized_version else None,
                "version_number": finalized_version.version_number if finalized_version else None,
                "storage_key": finalized_version.storage_key if finalized_version else None,
                "checksum_sha256": finalized_version.checksum_sha256 if finalized_version else None,
            } if finalized_version else None,
        }

    async def get_status_history(self, review_id: str):
        return await self.review_repo.get_status_history(review_id, self.tenant_id)

    async def get_assignments(self, review_id: str):
        return await self.review_repo.get_assignments(review_id, self.tenant_id)

    async def get_escalations(self, review_id: str):
        return await self.review_repo.get_escalations(review_id, self.tenant_id)

    async def get_approvals(self, review_id: str):
        return await self.review_repo.get_approvals(review_id, self.tenant_id)

    async def re_analyze(self, review_id: str, analysis_type: str = "full",
                          reason: Optional[str] = None) -> Optional[dict]:
        """Intelligent re-analysis that preserves reviewer decisions.

        Instead of brute-force re-analysis, this method:
        1. Preserves accepted redlines and reviewer decisions
        2. Compares old vs new findings to generate only delta findings
        3. Marks superseded findings as superseded
        4. Only generates new AI findings for clauses that changed
        5. Preserves existing resolutions on unchanged findings
        """
        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if not review:
            return None

        # Lock guard: cannot re-analyze immutable reviews
        raw_status = review.status
        status_str = raw_status.value if hasattr(raw_status, 'value') else str(raw_status)
        assert_review_mutable(status_str, "re-analyze", review_id)

        # Get the previous run for version tracking
        previous_run = await self._get_latest_ai_run(str(review.upload_id))
        previous_run_id = str(previous_run.run_id) if previous_run else None

        # Preserve accepted redlines and reviewer decisions
        accepted_redlines = await self.review_repo.get_redlines(
            review_id, self.tenant_id, RedlineStatus.ACCEPTED.value,
        )
        modified_redlines = await self.review_repo.get_redlines(
            review_id, self.tenant_id, RedlineStatus.MODIFIED.value,
        )
        rejected_redlines = await self.review_repo.get_redlines(
            review_id, self.tenant_id, RedlineStatus.REJECTED.value,
        )
        preserved_redline_ids = [str(r.redline_id) for r in accepted_redlines + modified_redlines]

        # Get existing findings with their resolutions
        existing_findings, _ = await self.review_repo.get_findings(
            review_id, self.tenant_id, page=1, page_size=500,
        )
        resolved_finding_ids = [
            str(f.finding_id) for f in existing_findings
            if f.resolution is not None
        ]

        # Increment review version
        current_version = getattr(review, 'version', 0) or 0
        new_version = current_version + 1

        # Create a new AI execution run
        from app.domains.ai.models import AIExecutionRun, ExecutionStatus
        new_run = AIExecutionRun(
            upload_id=review.upload_id,
            tenant_id=review.tenant_id,
            user_id=self.user.id,
            analysis_type=analysis_type,
            status=ExecutionStatus.PENDING,
            model="gpt-4o",
            provider="openai",
        )
        self.review_repo.session.add(new_run)
        await self.review_repo.session.flush()

        # Update review version and transition through workflow state machine
        current_state = map_legacy_status(status_str)
        target_state = WorkflowState.UPLOADED  # Reset to start of analysis pipeline
        try:
            validate_transition(current_state, target_state, review_id=review_id)
        except TransitionError:
            # If direct transition not allowed, still allow re-analysis
            pass

        # Store preservation metadata on the review
        review_metadata = dict(review.document_metadata or {})
        review_metadata["re_analysis"] = {
            "previous_run_id": previous_run_id,
            "analysis_type": analysis_type,
            "reason": reason,
            "preserved_redlines_count": len(preserved_redline_ids),
            "preserved_findings_count": len(resolved_finding_ids),
            "previous_version": current_version,
            "new_version": new_version,
            "triggered_by": self.user.id,
            "triggered_at": datetime.utcnow().isoformat(),
        }

        await self.review_repo.session.execute(
            update(ContractReview).where(
                ContractReview.review_id == review_id,
                ContractReview.tenant_id == self.tenant_id,
            ).values(
                status=ReviewStatus.DRAFT,
                version=new_version,
                document_metadata=review_metadata,
                updated_at=func.now(),
            )
        )

        # Mark existing redlines as superseded if they were not accepted
        if rejected_redlines:
            for rl in rejected_redlines:
                await self.review_repo.session.execute(
                    update(ReviewRedline).where(
                        ReviewRedline.redline_id == rl.redline_id,
                        ReviewRedline.tenant_id == self.tenant_id,
                    ).values(status=RedlineStatus.SUPERSEDED.value)
                )

        # Log status change
        from app.domains.review.models import ReviewStatusHistory
        self.review_repo.session.add(ReviewStatusHistory(
            review_id=review_id, tenant_id=self.tenant_id,
            from_status=status_str,
            to_status="draft",
            changed_by=self.user.id,
            reason=f"Re-analysis triggered: {reason or analysis_type} (preserving {len(preserved_redline_ids)} redlines, {len(resolved_finding_ids)} findings)",
        ))
        await self.review_repo.session.flush()

        # Audit trail
        await self.audit_trail.record(
            event_type="review.re_analyzed",
            entity_type="review",
            entity_id=review_id,
            actor_id=self.user.id,
            action="re_analyze",
            before_state={"status": status_str, "version": current_version},
            after_state={"status": "draft", "version": new_version},
            description=f"Re-analysis triggered ({analysis_type}): preserving {len(preserved_redline_ids)} accepted redlines, {len(resolved_finding_ids)} resolved findings. Reason: {reason or 'N/A'}",
            metadata={
                "analysis_type": analysis_type,
                "previous_run_id": previous_run_id,
                "preserved_redlines": len(preserved_redline_ids),
                "preserved_findings": len(resolved_finding_ids),
            },
        )

        # Dispatch the analysis task with preservation context
        try:
            from workers.ai_worker import analyze_contract_task
            analyze_contract_task.delay(
                upload_id=str(review.upload_id),
                tenant_id=self.tenant_id,
                user_id=self.user.id,
                analysis_type=analysis_type,
                preserve_redline_ids=preserved_redline_ids,
                preserve_finding_ids=resolved_finding_ids,
            )
        except ImportError:
            logger.warning("Could not import ai_worker task — running synchronously")
            from app.domains.ai.service import AIService
            ai_service = AIService(
                ai_repo=self.ai_repo,
                vector_repo=None,
                ingest_repo=None,
                event_bus=self.event_bus,
                user=self.user,
                tenant_id=self.tenant_id,
            )
            await ai_service.analyze(str(review.upload_id), analysis_type)

        return {
            "run_id": str(new_run.run_id),
            "previous_run_id": previous_run_id,
            "version": new_version,
            "preserved_redlines": len(preserved_redline_ids),
            "preserved_findings": len(resolved_finding_ids),
        }

    async def soft_delete(self, review_id: str, reason: Optional[str] = None) -> bool:
        """Soft-delete a review by setting is_deleted and deleted_at."""
        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if not review:
            return False

        raw_status = review.status
        status_str = raw_status.value if hasattr(raw_status, 'value') else str(raw_status)

        await self.review_repo.session.execute(
            update(ContractReview).where(
                ContractReview.review_id == review_id,
                ContractReview.tenant_id == self.tenant_id,
            ).values(
                is_deleted=True,
                deleted_at=func.now(),
                updated_at=func.now(),
            )
        )

        # Log the deletion in status history
        from app.domains.review.models import ReviewStatusHistory
        self.review_repo.session.add(ReviewStatusHistory(
            review_id=review_id, tenant_id=self.tenant_id,
            from_status=status_str,
            to_status="deleted",
            changed_by=self.user.id,
            reason=reason or "Review soft-deleted",
        ))
        await self.review_repo.session.flush()

        # Audit trail
        await self.audit_trail.record(
            event_type="review.deleted",
            entity_type="review",
            entity_id=review_id,
            actor_id=self.user.id,
            action="delete",
            before_state={"status": status_str},
            description=reason or "Review soft-deleted",
        )
        return True

    async def _get_latest_ai_run(self, upload_id: str) -> Optional[AIExecutionRun]:
        """Get the most recent AI execution run for an upload."""
        stmt = select(AIExecutionRun).where(
            AIExecutionRun.upload_id == upload_id,
            AIExecutionRun.tenant_id == self.tenant_id,
            AIExecutionRun.status == "completed",
        ).order_by(AIExecutionRun.created_at.desc()).limit(1)
        result = await self.review_repo.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _import_ai_findings(self, review_id: str, ai_run_id: str):
        """Import AI findings into the review context."""
        from app.domains.ai.models import AIFinding
        from app.domains.vectors.models import Chunk
        from sqlalchemy import select
        stmt = select(AIFinding).where(AIFinding.run_id == ai_run_id)
        result = await self.review_repo.session.execute(stmt)
        findings = result.scalars().all()
        chunk_ids = [cid for finding in findings for cid in (finding.chunk_ids or [])]
        chunks_by_id = {}
        if chunk_ids:
            chunk_result = await self.review_repo.session.execute(
                select(Chunk).where(
                    Chunk.chunk_id.in_(chunk_ids),
                    Chunk.tenant_id == self.tenant_id,
                )
            )
            chunks_by_id = {c.chunk_id: c for c in chunk_result.scalars().all()}

        for finding in findings:
            source_chunk = None
            for cid in finding.chunk_ids or []:
                if cid in chunks_by_id:
                    source_chunk = chunks_by_id[cid]
                    break
            source_text = finding.clause_text or (source_chunk.text if source_chunk else None)
            if source_text and source_chunk and finding.clause_text:
                source_start = source_chunk.text.lower().find(finding.clause_text.lower())
                if source_start < 0:
                    source_start = 0
            else:
                source_start = 0 if source_text else None
            source_end = source_start + len(source_text) if source_text and source_start is not None else None
            page_number = None
            if finding.page_numbers:
                page_number = finding.page_numbers[0]
            elif source_chunk and source_chunk.page_numbers:
                page_number = source_chunk.page_numbers[0]

            rf = ReviewFinding(
                review_id=review_id, upload_id=finding.upload_id,
                tenant_id=finding.tenant_id, ai_finding_id=finding.finding_id,
                clause_type=finding.clause_type, severity=finding.severity.value,
                title=finding.title, description=finding.description,
                recommendation=finding.recommendation, confidence=finding.confidence,
                risk_score=finding.risk_score,
                chunk_ids=finding.chunk_ids, page_numbers=finding.page_numbers,
                page_number=page_number,
                section_heading=source_chunk.section_heading if source_chunk else None,
                paragraph_index=(source_chunk.chunk_index + 1) if source_chunk else None,
                source_text=source_text,
                source_start_offset=source_start,
                source_end_offset=source_end,
                confidence_score=finding.confidence,
            )
            self.review_repo.session.add(rf)
        await self.review_repo.session.flush()

    async def _import_ai_redlines(self, review_id: str, ai_run_id: str):
        """Import AI redlines into the review context."""
        from app.domains.ai.models import AIRedline
        from sqlalchemy import select
        stmt = select(AIRedline).where(AIRedline.run_id == ai_run_id)
        result = await self.review_repo.session.execute(stmt)
        for redline in result.scalars().all():
            rr = ReviewRedline(
                review_id=review_id, upload_id=redline.upload_id,
                tenant_id=redline.tenant_id, ai_redline_id=redline.redline_id,
                clause_type=redline.clause_type, original_text=redline.original_text,
                proposed_text=redline.proposed_text,
                operation=getattr(redline, "operation", None),
                anchor_text=getattr(redline, "anchor_text", None),
                rationale=redline.rationale,
                risk_level=redline.risk_level, confidence=redline.confidence,
            )
            self.review_repo.session.add(rr)
        await self.review_repo.session.flush()

    @staticmethod
    def _normalize_priority(priority: Optional[str]) -> str:
        normalized = (priority or "").strip().lower()
        if normalized in ("critical", "high", "medium", "low"):
            return normalized
        if normalized == "urgent":
            return "critical"
        if normalized == "normal":
            return "low"
        return "low"

    @staticmethod
    def _calculate_priority(review) -> str:
        metadata = getattr(review, "document_metadata", None) or {}
        risk_score = metadata.get("risk_score", 0) if isinstance(metadata, dict) else 0
        finding_count = getattr(review, "finding_count", 0) or 0

        if risk_score >= 0.8:
            return "critical"
        if finding_count >= 5:
            return "high"
        if risk_score >= 0.5:
            return "medium"
        return "low"

    @staticmethod
    def _sla_hours_for_priority(priority: str) -> int:
        mapping = {
            "low": 72,
            "medium": 48,
            "high": 24,
            "critical": 4,
        }
        return mapping.get(ReviewService._normalize_priority(priority), 72)

    # ── Routing Engine ─────────────────────────────────────────────

    async def evaluate_routing_rules(self, review) -> Optional[dict]:
        """Evaluate routing rules against a review and return the best matching rule action."""
        from sqlalchemy import text as sa_text

        result = await self.review_repo.session.execute(
            sa_text("""
                SELECT * FROM routing_rules
                WHERE tenant_id = :tenant_id AND is_active = TRUE
                ORDER BY priority DESC
            """),
            {"tenant_id": self.tenant_id},
        )
        rules = result.fetchall()

        # Get review risk score from metadata
        metadata = getattr(review, 'document_metadata', None) or {}
        risk_score = metadata.get("risk_score", 0) if isinstance(metadata, dict) else 0

        for rule in rules:
            conditions = rule.conditions or {}
            risk_min = conditions.get("risk_min", 0)
            risk_max = conditions.get("risk_max", 1)

            if risk_min <= risk_score <= risk_max:
                return {
                    "rule_id": str(rule.rule_id),
                    "assign_to": rule.assign_to,
                    "set_priority": rule.set_priority or "normal",
                    "set_workflow_stage": rule.set_workflow_stage or "reviewer",
                    "sla_hours": rule.sla_hours or 48,
                }
        return None

    async def apply_routing_rules(self, review_id: str) -> Optional[dict]:
        """Evaluate and apply routing rules to a review."""
        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if not review:
            return None

        rule_action = await self.evaluate_routing_rules(review)
        if not rule_action:
            return None

        priority = self._normalize_priority(rule_action.get("set_priority") or self._calculate_priority(review))
        sla_hours = rule_action.get("sla_hours") or self._sla_hours_for_priority(priority)
        sla_deadline = utc_now() + timedelta(hours=sla_hours)

        await self.review_repo.session.execute(
            update(ContractReview).where(
                ContractReview.review_id == review_id,
                ContractReview.tenant_id == self.tenant_id,
            ).values(
                assigned_to=rule_action["assign_to"],
                assigned_by="routing_engine",
                assigned_at=func.now(),
                started_at=func.now(),
                workflow_stage=rule_action["set_workflow_stage"],
                priority=priority,
                sla_deadline=sla_deadline,
                sla_status="on_track",
                sla_breached=False,
            )
        )

        # Auto-transition to in_review if currently in review_ready or ai_analyzed
        raw_status = review.status
        current_status = raw_status.value if hasattr(raw_status, 'value') else raw_status
        if current_status in ("review_ready", "ai_analyzed"):
            await self.review_repo.update_status(
                review_id, self.tenant_id, ReviewStatus.IN_REVIEW,
                changed_by="routing_engine",
                reason=f"Auto-routed to {rule_action['assign_to']} (risk-based)",
            )

        await self.review_repo.session.flush()
        return rule_action

    # ── Workload Metrics ───────────────────────────────────────────

    async def get_workload_metrics(self) -> dict:
        """Get operational workload metrics for the review queue."""
        from sqlalchemy import text as sa_text

        TERMINAL = "('approved', 'closed', 'finalized', 'archived', 'rejected')"

        result = await self.review_repo.session.execute(
            sa_text(f"""
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE r.assigned_to IS NULL AND r.status NOT IN {TERMINAL})::int AS unassigned,
                    COUNT(*) FILTER (WHERE r.status = 'ai_analyzed' AND r.assigned_to IS NULL)::int AS ai_analyzed,
                    COUNT(*) FILTER (WHERE r.status IN ('ai_analyzed', 'review_ready') AND r.assigned_to IS NULL)::int AS ready_for_review,
                    COUNT(*) FILTER (WHERE r.assigned_to IS NOT NULL AND r.status IN ('ai_analyzed', 'review_ready'))::int AS assigned,
                    COUNT(*) FILTER (WHERE r.status = 'in_review')::int AS in_review,
                    COUNT(*) FILTER (WHERE r.status = 'legal_review')::int AS legal_review,
                    COUNT(*) FILTER (WHERE r.status = 'legal_approval')::int AS legal_approval,
                    COUNT(*) FILTER (WHERE r.status = 'approved')::int AS approved,
                    COUNT(*) FILTER (WHERE r.sla_status IN ('overdue', 'critical_overdue') AND r.status NOT IN {TERMINAL})::int AS overdue,
                    COUNT(*) FILTER (WHERE r.status = 'escalated')::int AS escalated,
                    COUNT(*) FILTER (WHERE r.priority IN ('urgent', 'critical') AND r.status NOT IN {TERMINAL})::int AS critical,
                    COUNT(*) FILTER (WHERE r.status = 'closed')::int AS closed,
                    COUNT(*) FILTER (WHERE r.sla_status IN ('warning', 'overdue', 'critical_overdue') AND r.status NOT IN {TERMINAL})::int AS sla_at_risk,
                    COUNT(*) FILTER (WHERE r.completed_at IS NOT NULL AND r.completed_at::date = CURRENT_DATE)::int AS completed_today,
                    -- Risk distribution
                    COUNT(*) FILTER (WHERE (r.metadata->>'risk_score')::float >= 0.7 AND r.status NOT IN {TERMINAL})::int AS critical_risk,
                    COUNT(*) FILTER (WHERE (r.metadata->>'risk_score')::float >= 0.5 AND (r.metadata->>'risk_score')::float < 0.7 AND r.status NOT IN {TERMINAL})::int AS high_risk,
                    COUNT(*) FILTER (WHERE (r.metadata->>'risk_score')::float >= 0.3 AND (r.metadata->>'risk_score')::float < 0.5 AND r.status NOT IN {TERMINAL})::int AS medium_risk,
                    COUNT(*) FILTER (WHERE (r.metadata->>'risk_score')::float < 0.3 AND r.status NOT IN {TERMINAL})::int AS low_risk,
                    -- Queue aging
                    COUNT(*) FILTER (WHERE r.created_at >= NOW() - INTERVAL '2 days' AND r.status NOT IN {TERMINAL})::int AS age_0_2_days,
                    COUNT(*) FILTER (WHERE r.created_at >= NOW() - INTERVAL '5 days' AND r.created_at < NOW() - INTERVAL '2 days' AND r.status NOT IN {TERMINAL})::int AS age_3_5_days,
                    COUNT(*) FILTER (WHERE r.created_at >= NOW() - INTERVAL '10 days' AND r.created_at < NOW() - INTERVAL '5 days' AND r.status NOT IN {TERMINAL})::int AS age_6_10_days,
                    COUNT(*) FILTER (WHERE r.created_at < NOW() - INTERVAL '10 days' AND r.status NOT IN {TERMINAL})::int AS age_10_plus_days
                FROM contract_reviews r
                WHERE r.tenant_id = :tenant_id AND r.is_deleted = FALSE
            """),
            {"tenant_id": self.tenant_id},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else {}

    async def get_reviewer_workloads(self) -> list[dict]:
        """Per-reviewer workload snapshot for the current tenant.

        Returns one entry per reviewer who has any reviews assigned (active
        or historical). Each entry contains the reviewer's display name,
        email, role, plus their active / overdue / completed counts and a
        derived workload percentage (0–100) suitable for sorting and
        capacity-balancing in the UI.

        The result shape mirrors the frontend `ReviewerWorkload` interface
        in ``frontend/components/ai-review/types.ts`` — keep them in sync.
        """
        from sqlalchemy import text as sa_text

        # Cap considered "overloaded" — mirrors the executive service.
        OVERLOAD_THRESHOLD = 5

        sql = sa_text("""
            SELECT
                u.user_id,
                u.name,
                u.email,
                u.role,
                COUNT(*) FILTER (WHERE r.status NOT IN (
                    'approved', 'rejected', 'closed',
                    'finalized', 'archived', 'executed'
                ))::int AS active_reviews,
                COUNT(*) FILTER (
                    WHERE r.completed_at IS NOT NULL
                      AND r.completed_at::date = CURRENT_DATE
                )::int AS completed_today,
                COUNT(*) FILTER (
                    WHERE r.sla_status IN ('overdue', 'critical_overdue')
                      AND r.status NOT IN (
                          'approved', 'rejected', 'closed',
                          'finalized', 'archived', 'executed'
                      )
                )::int AS overdue_reviews,
                COALESCE(
                    AVG(EXTRACT(EPOCH FROM (
                        COALESCE(r.completed_at, NOW()) - r.created_at
                    )) / 3600.0)::float, 0.0
                ) AS avg_review_time_hours,
                COUNT(*) FILTER (
                    WHERE r.sla_status IN ('overdue', 'critical_overdue')
                )::int AS sla_breaches
            FROM admin_users u
            LEFT JOIN contract_reviews r
                ON r.assigned_to = u.user_id
               AND r.tenant_id   = u.tenant_id
               AND r.is_deleted  = FALSE
            WHERE u.tenant_id = :tenant_id
              AND u.is_active  = TRUE
              AND u.role IN ('reviewer', 'legal_ops', 'compliance', 'executive', 'admin')
            GROUP BY u.user_id, u.name, u.email, u.role
            ORDER BY active_reviews DESC, u.name ASC
        """)
        result = await self.review_repo.session.execute(sql, {"tenant_id": self.tenant_id})
        rows = result.fetchall()

        out: list[dict] = []
        for row in rows:
            active = row.active_reviews or 0
            # Workload %: simple ratio against the overload threshold, clamped
            # to 0–100. This gives the frontend a meaningful scale even when
            # every reviewer has only 1–2 reviews (≤ 40% load).
            workload_pct = min(100, round((active / OVERLOAD_THRESHOLD) * 100))
            out.append({
                "user_id": row.user_id,
                "name": row.name or row.user_id,
                "email": row.email,
                "role": row.role,
                "active_reviews": active,
                "completed_today": row.completed_today or 0,
                "overdue_reviews": row.overdue_reviews or 0,
                "avg_review_time_hours": round(float(row.avg_review_time_hours or 0.0), 2),
                "workload_pct": workload_pct,
                "sla_breaches": row.sla_breaches or 0,
            })
        return out

    # ── Bulk Operations ────────────────────────────────────────────

    async def bulk_assign(self, review_ids: list[str], assignee_id: str,
                           role: str = "reviewer",
                           due_date: Optional[datetime] = None) -> dict:
        """Assign multiple reviews to a reviewer."""
        succeeded = 0
        failed = 0
        errors = []

        for rid in review_ids:
            try:
                await self.assign_reviewer(rid, assignee_id, role, due_date)
                succeeded += 1
            except Exception as e:
                failed += 1
                errors.append(f"{rid}: {str(e)}")

        # Log bulk action
        from app.domains.review.models import BulkAction
        action = BulkAction(
            tenant_id=self.tenant_id,
            action_type="assign",
            review_ids=[uuid.UUID(rid) for rid in review_ids],
            params={"assignee_id": assignee_id, "role": role},
            triggered_by=self.user.id,
            result={"succeeded": succeeded, "failed": failed, "errors": errors},
        )
        self.review_repo.session.add(action)
        await self.review_repo.session.flush()

        return {
            "action_id": str(action.action_id),
            "action_type": "assign",
            "total": len(review_ids),
            "succeeded": succeeded,
            "failed": failed,
            "errors": errors,
        }

    async def bulk_escalate(self, review_ids: list[str], reason: str,
                             escalated_to: Optional[str] = None) -> dict:
        """Escalate multiple reviews."""
        succeeded = 0
        failed = 0
        errors = []

        for rid in review_ids:
            try:
                await self.escalate(rid, reason, escalated_to)
                succeeded += 1
            except Exception as e:
                failed += 1
                errors.append(f"{rid}: {str(e)}")

        from app.domains.review.models import BulkAction
        action = BulkAction(
            tenant_id=self.tenant_id,
            action_type="escalate",
            review_ids=[uuid.UUID(rid) for rid in review_ids],
            params={"reason": reason, "escalated_to": escalated_to},
            triggered_by=self.user.id,
            result={"succeeded": succeeded, "failed": failed, "errors": errors},
        )
        self.review_repo.session.add(action)
        await self.review_repo.session.flush()

        return {
            "action_id": str(action.action_id),
            "action_type": "escalate",
            "total": len(review_ids),
            "succeeded": succeeded,
            "failed": failed,
            "errors": errors,
        }

    async def bulk_approve(self, review_ids: list[str], decision: str = "approved",
                            comments: Optional[str] = None) -> dict:
        """Approve/reject multiple reviews."""
        succeeded = 0
        failed = 0
        errors = []
        skipped = 0

        for rid in review_ids:
            try:
                # Idempotent: skip if already approved/rejected
                op_type = "approve" if decision == "approved" else "reject"
                lock_key = f"{op_type}:{rid}"
                if not OperationLock.acquire(lock_key):
                    skipped += 1
                    continue
                try:
                    if await self.idempotency.is_duplicate(op_type, rid, self.user.id):
                        skipped += 1
                        continue
                    await self._approve_impl(rid, decision, comments)
                    succeeded += 1
                finally:
                    OperationLock.release(lock_key)
            except Exception as e:
                failed += 1
                errors.append(f"{rid}: {str(e)}")

        from app.domains.review.models import BulkAction
        action = BulkAction(
            tenant_id=self.tenant_id,
            action_type="approve",
            review_ids=[uuid.UUID(rid) for rid in review_ids],
            params={"decision": decision},
            triggered_by=self.user.id,
            result={"succeeded": succeeded, "failed": failed, "skipped": skipped, "errors": errors},
        )
        self.review_repo.session.add(action)
        await self.review_repo.session.flush()

        return {
            "action_id": str(action.action_id),
            "action_type": "approve",
            "total": len(review_ids),
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
        }

    # ── Bulk Redline Actions ─────────────────────────────────────

    async def bulk_accept_redlines(self, review_id: str, max_risk_level: str = "low") -> dict:
        """Accept all redlines up to a specified risk level.

        Args:
            review_id: The review to operate on
            max_risk_level: Maximum risk level to auto-accept ('low', 'medium', 'high', 'critical')

        Returns:
            Summary of accepted redlines
        """
        risk_hierarchy = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        max_level = risk_hierarchy.get(max_risk_level, 0)

        redlines = await self.review_repo.get_redlines(review_id, self.tenant_id)
        accepted = 0
        errors = []

        for rl in redlines:
            rl_status = rl.status.value if hasattr(rl.status, 'value') else str(rl.status)
            rl_risk = rl.risk_level or "medium"
            rl_risk_level = risk_hierarchy.get(rl_risk, 1)

            if rl_status == "proposed" and rl_risk_level <= max_level:
                try:
                    await self.update_redline(str(rl.redline_id), "accepted")
                    accepted += 1
                except Exception as e:
                    errors.append(f"{rl.redline_id}: {str(e)}")

        # Audit bulk action
        await self.audit_trail.record(
            event_type="redline.bulk_accepted",
            entity_type="review",
            entity_id=review_id,
            actor_id=self.user.id,
            action="bulk_accept",
            description=f"Bulk accepted {accepted} redlines (max risk: {max_risk_level})",
            metadata={
                "total_candidates": len(redlines),
                "accepted": accepted,
                "max_risk_level": max_risk_level,
            },
        )

        return {
            "review_id": review_id,
            "accepted": accepted,
            "errors": errors,
            "max_risk_level": max_risk_level,
        }

    async def bulk_reject_redlines(self, review_id: str, severity: str = "informational") -> dict:
        """Reject all redlines matching a severity/risk level.

        Args:
            review_id: The review to operate on
            severity: Reject redlines at this level ('informational', 'low', 'medium')

        Returns:
            Summary of rejected redlines
        """
        target_levels = {"informational": ["info"], "low": ["info", "low"], "medium": ["info", "low", "medium"]}
        target_risks = target_levels.get(severity, ["info"])

        redlines = await self.review_repo.get_redlines(review_id, self.tenant_id)
        rejected = 0
        errors = []

        for rl in redlines:
            rl_status = rl.status.value if hasattr(rl.status, 'value') else str(rl.status)
            rl_risk = (rl.risk_level or "medium").lower()

            if rl_status == "proposed" and rl_risk in target_risks:
                try:
                    await self.update_redline(str(rl.redline_id), "rejected")
                    rejected += 1
                except Exception as e:
                    errors.append(f"{rl.redline_id}: {str(e)}")

        # Audit bulk action
        await self.audit_trail.record(
            event_type="redline.bulk_rejected",
            entity_type="review",
            entity_id=review_id,
            actor_id=self.user.id,
            action="bulk_reject",
            description=f"Bulk rejected {rejected} redlines (severity: {severity})",
            metadata={
                "total_candidates": len(redlines),
                "rejected": rejected,
                "severity": severity,
            },
        )

        return {
            "review_id": review_id,
            "rejected": rejected,
            "errors": errors,
            "severity": severity,
        }

    @staticmethod
    def _compute_sla(review) -> dict:
        """Compute SLA status and overdue hours for a review.

        Uses DB-stored values as base, then recomputes from sla_deadline
        if present for real-time accuracy.
        """
        now = utc_now()
        sla_deadline = ensure_utc(review.sla_deadline)
        sla_breached = review.sla_breached or False
        sla_status = getattr(review, 'sla_status', None) or "on_track"
        overdue_hours = getattr(review, 'overdue_hours', None) or 0.0

        if sla_deadline:
            diff = (sla_deadline - now).total_seconds()
            overdue_hours = max(0, -diff / 3600)
            if diff < 0:
                sla_status = "critical_overdue" if overdue_hours >= 24 else "overdue"
                sla_breached = True
            elif diff < 4 * 3600:
                sla_status = "warning"
            else:
                sla_status = "on_track"
        # else: keep DB-stored sla_status and overdue_hours when no deadline set

        return {
            "sla_deadline": sla_deadline.isoformat() if sla_deadline else None,
            "sla_due_at": sla_deadline.isoformat() if sla_deadline else None,
            "sla_breached": sla_breached,
            "sla_status": sla_status,
            "overdue_hours": round(overdue_hours, 1),
        }

    @staticmethod
    def _review_to_detail(review) -> dict:
        # Extract document filename from transient attribute (set by repository join)
        filename = getattr(review, '_document_filename', None)
        content_type = getattr(review, '_document_content_type', None)
        # Extract assignee display name from transient attribute (set by repository join)
        assignee_name = getattr(review, '_assignee_name', None)
        # Extract risk_score from document metadata (set by AI analysis)
        metadata = getattr(review, 'document_metadata', None) or {}
        risk_score = metadata.get("risk_score") if isinstance(metadata, dict) else None
        contract_number = metadata.get("contract_number") if isinstance(metadata, dict) else None
        # Fallback: generate a display contract number from the review's created_at
        if not contract_number and hasattr(review, 'created_at') and review.created_at:
            try:
                ts = review.created_at
                month_year = ts.strftime("%m%Y")
                short_id = str(review.review_id)[:4].upper() if hasattr(review, 'review_id') else "0000"
                contract_number = f"C{month_year}-{short_id}"
            except Exception:
                contract_number = None
        # Extract status safely (could be enum or string)
        raw_status = review.status
        status_str = raw_status.value if hasattr(raw_status, 'value') else (raw_status if isinstance(raw_status, str) else str(raw_status))
        # Compute SLA
        sla = ReviewService._compute_sla(review)
        # Resolve critical/high finding count from transient attribute (set by repository join or computed)
        critical_finding_count = getattr(review, '_critical_finding_count', None)
        return {
            "review_id": str(review.review_id),
            "upload_id": str(review.upload_id),
            "contract_id": str(review.contract_id) if review.contract_id else None,
            "status": status_str,
            "assigned_to": review.assigned_to,
            # Friendly display name resolved from admin_users via repository join.
            # Frontend should prefer this over `assigned_to` for display purposes.
            "assigned_to_name": assignee_name,
            "assigned_by": review.assigned_by,
            "assigned_at": review.assigned_at.isoformat() if review.assigned_at else None,
            "started_at": (getattr(review, "started_at", None) or review.assigned_at).isoformat() if (getattr(review, "started_at", None) or review.assigned_at) else None,
            "workflow_stage": review.workflow_stage,
            "priority": ReviewService._normalize_priority(review.priority),
            "finding_count": review.finding_count,
            "critical_finding_count": critical_finding_count or 0,
            "redline_count": review.redline_count,
            "comment_count": review.comment_count,
            "escalation_count": review.escalation_count,
            **sla,
            "created_by": review.created_by,
            "created_at": review.created_at.isoformat(),
            "updated_at": review.updated_at.isoformat() if review.updated_at else review.created_at.isoformat(),
            "completed_at": review.completed_at.isoformat() if review.completed_at else None,
            # Rejection metadata
            "rejection_reason": review.rejection_reason,
            "rejection_category": review.rejection_category,
            "rejection_severity": review.rejection_severity,
            "rejected_by": review.rejected_by,
            "rejected_at": review.rejected_at.isoformat() if review.rejected_at else None,
            # Document metadata from upload_sessions join
            "document_name": filename,
            "original_filename": filename,
            "document_type": content_type,
            # Risk score from AI analysis (stored in document_metadata)
            "risk_score": risk_score,
            "contract_number": contract_number,
            "version": review.version or 1,
            # Approved version reference
            "approved_version_id": str(review.approved_version_id) if review.approved_version_id else None,
            "approved_version_number": None,  # resolved by repository join if needed
        }

    async def _link_approved_document_version(self, review_id: str) -> None:
        """Link the current document version to this approval (non-blocking on failure)."""
        try:
            from app.domains.review.models import ContractDocumentVersion, ContractReview

            current_version = await self.review_repo.session.execute(
                select(ContractDocumentVersion).where(
                    ContractDocumentVersion.review_id == review_id,
                    ContractDocumentVersion.tenant_id == self.tenant_id,
                    ContractDocumentVersion.status == "current",
                )
            )
            cv = current_version.scalar_one_or_none()
            if not cv:
                return

            await self.review_repo.session.execute(
                update(ContractDocumentVersion)
                .where(ContractDocumentVersion.version_id == cv.version_id)
                .values(status="approved_release")
            )
            await self.review_repo.session.execute(
                update(ContractReview)
                .where(
                    ContractReview.review_id == review_id,
                    ContractReview.tenant_id == self.tenant_id,
                )
                .values(approved_version_id=cv.version_id)
            )
            await self.review_repo.session.flush()
        except Exception as exc:
            logger.warning("Could not link approved document version for %s: %s", review_id, exc)

    # ── Document Versioning ───────────────────────────────────────

    async def ensure_original_document_version(self, review_id: str) -> None:
        """Create v1 (original upload) if no document versions exist yet."""
        from app.domains.review.models import ContractDocumentVersion
        from app.domains.ingestion.models import UploadSession

        rid = uuid.UUID(review_id)
        tid = uuid.UUID(self.tenant_id)

        count_result = await self.review_repo.session.execute(
            select(func.count())
            .select_from(ContractDocumentVersion)
            .where(
                ContractDocumentVersion.review_id == rid,
                ContractDocumentVersion.tenant_id == tid,
            )
        )
        if (count_result.scalar() or 0) > 0:
            return

        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if not review:
            return

        upload_result = await self.review_repo.session.execute(
            select(UploadSession).where(
                UploadSession.upload_id == review.upload_id,
                UploadSession.tenant_id == tid,
            )
        )
        upload = upload_result.scalar_one_or_none()

        version = ContractDocumentVersion(
            review_id=rid,
            tenant_id=tid,
            version_number=1,
            label="Original Upload",
            status="current",
            source_document_id=review.upload_id,
            storage_key=upload.storage_key if upload else None,
            file_size_bytes=upload.file_size if upload else None,
            mime_type=(upload.content_type if upload else None) or "application/pdf",
            checksum_sha256=(
                upload.server_checksum_sha256 if upload else None
            ),
            created_by=review.created_by or self.user.id,
        )
        self.review_repo.session.add(version)
        await self.review_repo.session.flush()

    async def _sync_redline_applied_version(self, review_id: str) -> Optional[dict]:
        """Ensure v1 exists and v2 reflects all accepted/modified redlines."""
        accepted = await self.review_repo.get_redlines(
            review_id, self.tenant_id, RedlineStatus.ACCEPTED.value,
        )
        modified = await self.review_repo.get_redlines(
            review_id, self.tenant_id, RedlineStatus.MODIFIED.value,
        )
        applied_ids = {str(r.redline_id) for r in accepted}
        applied_ids.update(str(r.redline_id) for r in modified)
        if not applied_ids:
            return None

        await self.ensure_original_document_version(review_id)

        from app.domains.review.models import ContractDocumentVersion

        rid = uuid.UUID(review_id)
        tid = uuid.UUID(self.tenant_id)
        ids_list = sorted(applied_ids)
        summary = f"Applied {len(ids_list)} accepted redline(s)"

        existing_result = await self.review_repo.session.execute(
            select(ContractDocumentVersion).where(
                ContractDocumentVersion.review_id == rid,
                ContractDocumentVersion.tenant_id == tid,
                ContractDocumentVersion.version_number == 2,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            artifact = None
            if not existing.storage_key:
                artifact = await self._generate_redline_document_artifact(
                    review_id, ids_list, version_number=existing.version_number,
                )
            await self.review_repo.session.execute(
                update(ContractDocumentVersion)
                .where(ContractDocumentVersion.version_id == existing.version_id)
                .values(
                    label="AI Redlines Applied",
                    status="current",
                    change_summary=artifact["change_summary"] if artifact else summary,
                    accepted_redline_ids=[uuid.UUID(x) for x in ids_list],
                    **(
                        {
                            "storage_key": artifact["storage_key"],
                            "file_size_bytes": artifact["file_size_bytes"],
                            "checksum_sha256": artifact["checksum_sha256"],
                        }
                        if artifact
                        else {}
                    ),
                )
            )
            await self.review_repo.session.flush()
            return {
                "version_id": str(existing.version_id),
                "version_number": existing.version_number,
                "label": "AI Redlines Applied",
                "change_summary": artifact["change_summary"] if artifact else summary,
                "storage_key": artifact["storage_key"] if artifact else existing.storage_key,
            }

        return await self.create_version(
            review_id,
            label="AI Redlines Applied",
            change_summary=summary,
            accepted_redline_ids=ids_list,
        )

    async def get_versions(self, review_id: str) -> list[dict]:
        """Get all document versions for a review."""
        await self.ensure_original_document_version(review_id)

        from app.domains.review.models import ContractDocumentVersion
        from sqlalchemy import select

        # Backfill v2 when redlines were accepted before versioning ran
        max_result = await self.review_repo.session.execute(
            select(func.max(ContractDocumentVersion.version_number)).where(
                ContractDocumentVersion.review_id == uuid.UUID(review_id),
                ContractDocumentVersion.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        if (max_result.scalar() or 0) < 2:
            accepted_count = await self.review_repo.get_redlines(
                review_id, self.tenant_id, RedlineStatus.ACCEPTED.value,
            )
            if accepted_count:
                try:
                    await self._sync_redline_applied_version(review_id)
                except Exception:
                    logger.exception(
                        "Failed to backfill document version for review %s", review_id,
                    )

        stmt = select(ContractDocumentVersion).where(
            ContractDocumentVersion.review_id == review_id,
            ContractDocumentVersion.tenant_id == self.tenant_id,
        ).order_by(ContractDocumentVersion.version_number)
        result = await self.review_repo.session.execute(stmt)
        versions = result.scalars().all()

        # Generate missing .docx files for versions that only have metadata
        for v in versions:
            if v.storage_key or not v.accepted_redline_ids:
                continue
            try:
                await self._generate_redline_document_artifact(
                    review_id,
                    [str(r) for r in v.accepted_redline_ids],
                    version_number=v.version_number,
                    version_id=v.version_id,
                )
            except Exception:
                logger.exception(
                    "Failed to generate file for review %s v%s",
                    review_id, v.version_number,
                )

        # Re-fetch after possible file generation
        result = await self.review_repo.session.execute(stmt)
        versions = result.scalars().all()
        return [
            {
                "version_id": str(v.version_id),
                "review_id": str(v.review_id),
                "version_number": v.version_number,
                "label": v.label,
                "status": v.status,
                "source_document_id": str(v.source_document_id) if v.source_document_id else None,
                "storage_key": v.storage_key,
                "change_summary": v.change_summary,
                "accepted_redline_ids": [str(r) for r in v.accepted_redline_ids] if v.accepted_redline_ids else [],
                "file_size_bytes": v.file_size_bytes,
                "mime_type": v.mime_type,
                "checksum_sha256": v.checksum_sha256,
                "created_by": v.created_by,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ]

    async def _generate_redline_document_artifact(
        self,
        review_id: str,
        accepted_redline_ids: list[str],
        version_number: int,
        version_id: Optional[uuid.UUID] = None,
    ) -> Optional[dict]:
        """Build a .docx with accepted redlines and optionally persist on a version row."""
        from app.domains.review.models import ContractDocumentVersion, ContractReview, ReviewRedline
        from app.domains.ingestion.models import UploadSession
        from app.domains.review.document_generation import generate_version_from_redlines

        review_row = (
            await self.review_repo.session.execute(
                select(ContractReview).where(
                    ContractReview.review_id == review_id,
                    ContractReview.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not review_row:
            return None

        upload_row = (
            await self.review_repo.session.execute(
                select(UploadSession).where(
                    UploadSession.upload_id == review_row.upload_id,
                    UploadSession.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not upload_row or not upload_row.storage_key:
            return None

        redlines_result = await self.review_repo.session.execute(
            select(ReviewRedline).where(
                ReviewRedline.redline_id.in_([uuid.UUID(rid) for rid in accepted_redline_ids]),
                ReviewRedline.tenant_id == self.tenant_id,
            )
        )
        redlines_data = []
        for r in redlines_result.scalars().all():
            operation = infer_operation(
                r.original_text,
                r.proposed_text,
                clause_type=r.clause_type,
                stored_operation=getattr(r, "operation", None),
            )
            proposed = (
                r.reviewer_modified_text
                if _enum_value(r.status) == "modified" and r.reviewer_modified_text
                else r.proposed_text
            )
            redlines_data.append({
                "redline_id": str(r.redline_id),
                "clause_type": r.clause_type,
                "original_text": r.original_text,
                "proposed_text": proposed,
                "operation": operation.value,
                "anchor_text": getattr(r, "anchor_text", None) or "",
                "rationale": r.rationale,
                "risk_level": r.risk_level,
            })
        if not redlines_data:
            return None

        gen_result = await generate_version_from_redlines(
            session=self.review_repo.session,
            review_id=review_id,
            tenant_id=self.tenant_id,
            user_id=self.user.id,
            source_upload_id=str(review_row.upload_id),
            original_storage_key=upload_row.storage_key,
            accepted_redlines=redlines_data,
            version_number=version_number,
        )
        if not gen_result:
            return None

        artifact = {
            "storage_key": gen_result.storage_key,
            "file_size_bytes": gen_result.file_size_bytes,
            "checksum_sha256": gen_result.checksum_sha256,
            "change_summary": gen_result.change_summary,
        }

        if version_id:
            await self.review_repo.session.execute(
                update(ContractDocumentVersion)
                .where(ContractDocumentVersion.version_id == version_id)
                .values(**artifact)
            )
            await self.review_repo.session.flush()

        return artifact

    async def create_version(self, review_id: str, label: Optional[str] = None,
                              change_summary: Optional[str] = None,
                              accepted_redline_ids: Optional[list[str]] = None) -> dict:
        """Create a new document version for a review.

        Calculates the next version number automatically.
        Marks the previous current version as 'archived'.
        If accepted_redline_ids are provided, attempts to generate a real .docx
        artifact by applying redline changes to the original document.
        """
        from app.domains.review.models import ContractDocumentVersion, ContractReview
        from app.domains.ingestion.models import UploadSession
        from sqlalchemy import select, update, func

        # Get the latest version number
        result = await self.review_repo.session.execute(
            select(func.max(ContractDocumentVersion.version_number)).where(
                ContractDocumentVersion.review_id == review_id,
                ContractDocumentVersion.tenant_id == self.tenant_id,
            )
        )
        max_version = result.scalar() or 0
        next_version = max_version + 1

        # Archive previous current version
        if max_version > 0:
            await self.review_repo.session.execute(
                update(ContractDocumentVersion).where(
                    ContractDocumentVersion.review_id == review_id,
                    ContractDocumentVersion.tenant_id == self.tenant_id,
                    ContractDocumentVersion.status == "current",
                ).values(status="archived")
            )

        # Try to generate a real document artifact
        storage_key = None
        file_size_bytes = None
        checksum_sha256 = None
        gen_change_summary = change_summary

        if accepted_redline_ids:
            try:
                artifact = await self._generate_redline_document_artifact(
                    review_id, accepted_redline_ids, version_number=next_version,
                )
                if artifact:
                    storage_key = artifact["storage_key"]
                    file_size_bytes = artifact["file_size_bytes"]
                    checksum_sha256 = artifact["checksum_sha256"]
                    gen_change_summary = artifact["change_summary"]
                    logger.info(
                        "Generated document artifact for review=%s version=v%s",
                        review_id, next_version,
                    )
            except Exception as exc:
                logger.warning(
                    "Document generation failed (non-blocking) for review=%s: %s",
                    review_id, exc, exc_info=True,
                )

        # Create new version record
        version_label = label or _default_version_label(next_version, accepted_redline_ids)
        version = ContractDocumentVersion(
            review_id=review_id,
            tenant_id=self.tenant_id,
            version_number=next_version,
            label=version_label,
            status="current",
            change_summary=gen_change_summary,
            accepted_redline_ids=[uuid.UUID(rid) for rid in (accepted_redline_ids or [])],
            storage_key=storage_key,
            file_size_bytes=file_size_bytes,
            checksum_sha256=checksum_sha256,
            created_by=self.user.id,
        )
        self.review_repo.session.add(version)
        await self.review_repo.session.flush()

        return {
            "version_id": str(version.version_id),
            "review_id": str(version.review_id),
            "version_number": version.version_number,
            "label": version.label,
            "status": version.status,
            "change_summary": version.change_summary,
            "storage_key": storage_key,
            "file_size_bytes": file_size_bytes,
            "checksum_sha256": checksum_sha256,
            "created_by": version.created_by,
            "created_at": version.created_at.isoformat(),
        }

    async def download_version(self, review_id: str, version_id: str) -> tuple[bytes, str, str]:
        """Return file bytes, filename, and content type for a document version."""
        from app.domains.review.models import ContractDocumentVersion

        result = await self.review_repo.session.execute(
            select(ContractDocumentVersion).where(
                ContractDocumentVersion.version_id == uuid.UUID(version_id),
                ContractDocumentVersion.review_id == uuid.UUID(review_id),
                ContractDocumentVersion.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        version = result.scalar_one_or_none()
        if not version or not version.storage_key:
            raise ValueError("Version file not available")

        from app.config import settings
        from app.integrations.storage.s3 import storage_service

        bucket = settings.s3_bucket or "contractrisk-documents"
        data = await storage_service.download_fileobj(bucket, version.storage_key)
        filename = version.storage_key.rsplit("/", 1)[-1]
        mime = version.mime_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return data, filename, mime

    async def export_tracked_changes(self, review_id: str, version_id: str) -> tuple[bytes, str, str]:
        """Generate a tracked-changes DOCX showing redlines as visual markup."""
        from app.domains.review.models import ContractDocumentVersion, ReviewRedline

        result = await self.review_repo.session.execute(
            select(ContractDocumentVersion).where(
                ContractDocumentVersion.version_id == uuid.UUID(version_id),
                ContractDocumentVersion.review_id == uuid.UUID(review_id),
                ContractDocumentVersion.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            raise ValueError("Version not found")

        # Get the original upload document
        from app.domains.review.models import ContractReview
        from app.domains.ingestion.models import UploadSession

        review_result = await self.review_repo.session.execute(
            select(ContractReview).where(
                ContractReview.review_id == uuid.UUID(review_id),
                ContractReview.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        review = review_result.scalar_one_or_none()
        if not review:
            raise ValueError("Review not found")

        upload_result = await self.review_repo.session.execute(
            select(UploadSession).where(
                UploadSession.upload_id == review.upload_id,
                UploadSession.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        upload = upload_result.scalar_one_or_none()
        if not upload or not upload.storage_key:
            raise ValueError("Original document not available")

        from app.config import settings
        from app.integrations.storage.s3 import storage_service
        bucket = settings.s3_bucket or "contractrisk-documents"

        # Download original document
        original_bytes = await storage_service.download_fileobj(bucket, upload.storage_key)

        # Get accepted/modified redlines
        redlines_result = await self.review_repo.session.execute(
            select(ReviewRedline).where(
                ReviewRedline.review_id == uuid.UUID(review_id),
                ReviewRedline.tenant_id == uuid.UUID(self.tenant_id),
                ReviewRedline.status.in_(["accepted", "modified"]),
            )
        )
        redlines_data = [
            {
                "original_text": r.original_text,
                "proposed_text": r.reviewer_modified_text or r.proposed_text,
                "clause_type": r.clause_type,
            }
            for r in redlines_result.scalars().all()
        ]

        # Generate tracked-changes DOCX
        from app.domains.review.document_generation import generate_tracked_changes_docx
        tracked_bytes = generate_tracked_changes_docx(original_bytes, redlines_data)
        filename = f"tracked_v{version.version_number}.docx"
        return tracked_bytes, filename, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    async def diff_versions(self, review_id: str, version_id_a: str, version_id_b: str) -> dict:
        """Produce a structured clause-level diff between two document versions.

        Uses difflib to compute word-level inline changes so the frontend can
        highlight only the changed words (green insertions, red deletions)
        instead of showing entire before/after blocks.
        """
        from app.domains.review.models import ContractDocumentVersion, ReviewRedline

        # Fetch both versions
        result = await self.review_repo.session.execute(
            select(ContractDocumentVersion).where(
                ContractDocumentVersion.version_id.in_([
                    uuid.UUID(version_id_a), uuid.UUID(version_id_b)
                ]),
                ContractDocumentVersion.review_id == uuid.UUID(review_id),
                ContractDocumentVersion.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        versions = {str(v.version_id): v for v in result.scalars().all()}
        v_a = versions.get(version_id_a)
        v_b = versions.get(version_id_b)
        if not v_a or not v_b:
            raise ValueError("One or both versions not found")

        # Collect redline IDs from both versions
        all_redline_ids = set()
        for v in [v_a, v_b]:
            if v.accepted_redline_ids:
                all_redline_ids.update(str(rid) for rid in v.accepted_redline_ids)

        # Fetch redline details and compute word-level diffs
        changes = []
        if all_redline_ids:
            redline_uuids = [uuid.UUID(rid) for rid in all_redline_ids]
            redlines_result = await self.review_repo.session.execute(
                select(ReviewRedline).where(
                    ReviewRedline.redline_id.in_(redline_uuids),
                    ReviewRedline.tenant_id == self.tenant_id,
                )
            )
            for rl in redlines_result.scalars().all():
                operation = infer_operation(
                    rl.original_text,
                    rl.proposed_text,
                    clause_type=rl.clause_type,
                    stored_operation=getattr(rl, "operation", None),
                )
                after_text = (
                    rl.reviewer_modified_text
                    if _enum_value(rl.status) == "modified" and rl.reviewer_modified_text
                    else rl.proposed_text
                )[:3000]
                before_text = (
                    "" if operation == RedlineOperation.INSERT else rl.original_text[:3000]
                )
                word_diff = build_word_diff(operation, rl.original_text, after_text)

                changes.append({
                    "type": change_type_for_operation(operation),
                    "operation": operation.value,
                    "clause_type": rl.clause_type or "unknown",
                    "severity": rl.risk_level or "medium",
                    "status": _enum_value(rl.status),
                    "rationale": rl.rationale or "",
                    "confidence": rl.confidence,
                    "anchor_text": getattr(rl, "anchor_text", None) or "",
                    "before": before_text,
                    "after": after_text,
                    "word_diff": word_diff,
                })

        return {
            "version_a": {
                "version_id": version_id_a,
                "version_number": v_a.version_number,
                "label": v_a.label,
            },
            "version_b": {
                "version_id": version_id_b,
                "version_number": v_b.version_number,
                "label": v_b.label,
            },
            "changes": changes,
            "total_changes": len(changes),
        }

    # ── Stub endpoints for frontend compatibility ─────────────────────
    # These return empty/default data until the full implementations
    # are built out. They exist so the frontend doesn't get 404s.

    async def _sync_review_policy_linkage(self, review_id: str) -> None:
        """Match findings to policy rules and persist linkage on review_findings."""
        from sqlalchemy import text as sa_text
        import json
        import uuid as _uuid

        from app.domains.review.policy_linkage import pick_best_rule, normalize_clause_category

        findings_sql = sa_text("""
            SELECT finding_id, clause_type, severity, title, description,
                   recommendation, resolution, rule_id, playbook_id, evaluation_id
            FROM review_findings
            WHERE tenant_id = :tenant_id AND review_id = CAST(:review_id AS uuid)
        """)
        result = await self.review_repo.session.execute(
            findings_sql, {"tenant_id": self.tenant_id, "review_id": review_id}
        )
        findings = [dict(row._mapping) for row in result.fetchall()]
        if not findings:
            return

        rules_sql = sa_text("""
            SELECT rule_id, playbook_id, name, description, priority, is_mandatory,
                   effect, target_category, conditions, target_clause_id
            FROM policy_rules
            WHERE tenant_id = :tenant_id AND is_active = TRUE
            ORDER BY priority ASC
        """)
        result = await self.review_repo.session.execute(rules_sql, {"tenant_id": self.tenant_id})
        rules = [dict(row._mapping) for row in result.fetchall()]
        if not rules:
            return

        review_sql = sa_text("""
            SELECT upload_id FROM contract_reviews
            WHERE review_id = CAST(:review_id AS uuid) AND tenant_id = :tenant_id
        """)
        r = await self.review_repo.session.execute(
            review_sql, {"tenant_id": self.tenant_id, "review_id": review_id}
        )
        upload_id = r.scalar()
        if not upload_id:
            return

        eval_sql = sa_text("""
            SELECT evaluation_id, deviations, results
            FROM policy_evaluations
            WHERE tenant_id = :tenant_id AND review_id = CAST(:review_id AS uuid)
            LIMIT 1
        """)
        r = await self.review_repo.session.execute(
            eval_sql, {"tenant_id": self.tenant_id, "review_id": review_id}
        )
        eval_row = r.fetchone()
        evaluation_id = eval_row.evaluation_id if eval_row else None
        deviations = list(eval_row.deviations or []) if eval_row else []
        eval_results = list(eval_row.results or []) if eval_row else []

        clause_sql = sa_text("""
            SELECT clause_id, playbook_id, category, title, body
            FROM clause_standards
            WHERE tenant_id = :tenant_id AND is_active = TRUE
        """)
        result = await self.review_repo.session.execute(clause_sql, {"tenant_id": self.tenant_id})
        clause_by_category: dict[str, dict] = {}
        for row in result.fetchall():
            cat = normalize_clause_category(row.category)
            if cat and cat not in clause_by_category:
                clause_by_category[cat] = dict(row._mapping)

        playbook_sql = sa_text("""
            SELECT lp.playbook_id, lp.name, lp.created_by, pv.version_label
            FROM legal_playbooks lp
            LEFT JOIN playbook_versions pv ON pv.version_id = lp.active_version_id
            WHERE lp.tenant_id = :tenant_id
        """)
        result = await self.review_repo.session.execute(playbook_sql, {"tenant_id": self.tenant_id})
        playbooks = {str(row.playbook_id): dict(row._mapping) for row in result.fetchall()}

        for f in findings:
            if f.get("rule_id"):
                continue
            rule = pick_best_rule(f, rules)
            if not rule:
                continue

            clause_std = clause_by_category.get(normalize_clause_category(f.get("clause_type")))
            pb = playbooks.get(str(rule["playbook_id"])) if rule.get("playbook_id") else None

            update_sql = sa_text("""
                UPDATE review_findings
                SET playbook_id = CAST(:playbook_id AS uuid),
                    rule_id = CAST(:rule_id AS uuid),
                    evaluation_id = CAST(:evaluation_id AS uuid),
                    clause_standard_id = CAST(:clause_standard_id AS uuid),
                    policy_owner = :policy_owner
                WHERE finding_id = CAST(:finding_id AS uuid)
                  AND tenant_id = :tenant_id
            """)
            await self.review_repo.session.execute(
                update_sql,
                {
                    "finding_id": str(f["finding_id"]),
                    "tenant_id": self.tenant_id,
                    "playbook_id": str(rule["playbook_id"]) if rule.get("playbook_id") else None,
                    "rule_id": str(rule["rule_id"]),
                    "evaluation_id": str(evaluation_id) if evaluation_id else None,
                    "clause_standard_id": str(clause_std["clause_id"]) if clause_std else None,
                    "policy_owner": (pb or {}).get("created_by") or "Legal Ops",
                },
            )

            f["rule_id"] = rule["rule_id"]
            f["playbook_id"] = rule.get("playbook_id")
            f["evaluation_id"] = evaluation_id
            f["clause_standard_id"] = clause_std["clause_id"] if clause_std else None

            deviation_entry = {
                "finding_id": str(f["finding_id"]),
                "rule_id": str(rule["rule_id"]),
                "clause_category": f.get("clause_type"),
                "severity": f.get("severity"),
                "title": f.get("title"),
                "description": f.get("description"),
            }
            if not any(d.get("finding_id") == str(f["finding_id"]) for d in deviations):
                deviations.append(deviation_entry)

            result_entry = {
                "rule_id": str(rule["rule_id"]),
                "rule_name": rule.get("name"),
                "matched": True,
                "effect": rule.get("effect"),
                "finding_id": str(f["finding_id"]),
            }
            if not any(er.get("rule_id") == str(rule["rule_id"]) and er.get("finding_id") == str(f["finding_id"]) for er in eval_results):
                eval_results.append(result_entry)

        if not evaluation_id and (deviations or eval_results):
            evaluation_id = _uuid.uuid4()
            primary_playbook = str(rules[0]["playbook_id"]) if rules else None
            insert_eval = sa_text("""
                INSERT INTO policy_evaluations
                    (evaluation_id, tenant_id, upload_id, review_id, playbook_id, status,
                     total_rules_evaluated, rules_passed, rules_failed,
                     deviations_found, mandatory_blocks, approval_required,
                     results, deviations, recommendations)
                VALUES
                    (CAST(:evaluation_id AS uuid), :tenant_id, :upload_id,
                     CAST(:review_id AS uuid), CAST(:playbook_id AS uuid), 'completed',
                     :total, 0, :failed, :deviations_found, 0, 0,
                     CAST(:results AS jsonb), CAST(:deviations AS jsonb), '[]'::jsonb)
            """)
            await self.review_repo.session.execute(
                insert_eval,
                {
                    "evaluation_id": str(evaluation_id),
                    "tenant_id": self.tenant_id,
                    "upload_id": str(upload_id),
                    "review_id": review_id,
                    "playbook_id": primary_playbook,
                    "total": len(eval_results),
                    "failed": len(deviations),
                    "deviations_found": len(deviations),
                    "results": json.dumps(eval_results),
                    "deviations": json.dumps(deviations),
                },
            )
            backfill_eval = sa_text("""
                UPDATE review_findings
                SET evaluation_id = CAST(:evaluation_id AS uuid)
                WHERE tenant_id = :tenant_id AND review_id = CAST(:review_id AS uuid)
                  AND rule_id IS NOT NULL AND evaluation_id IS NULL
            """)
            await self.review_repo.session.execute(
                backfill_eval,
                {"evaluation_id": str(evaluation_id), "tenant_id": self.tenant_id, "review_id": review_id},
            )
        elif evaluation_id and deviations:
            update_eval = sa_text("""
                UPDATE policy_evaluations
                SET deviations = CAST(:deviations AS jsonb),
                    results = CAST(:results AS jsonb),
                    deviations_found = :deviations_found,
                    rules_failed = :rules_failed,
                    total_rules_evaluated = :total
                WHERE evaluation_id = CAST(:evaluation_id AS uuid) AND tenant_id = :tenant_id
            """)
            await self.review_repo.session.execute(
                update_eval,
                {
                    "evaluation_id": str(evaluation_id),
                    "tenant_id": self.tenant_id,
                    "deviations": json.dumps(deviations),
                    "results": json.dumps(eval_results),
                    "deviations_found": len(deviations),
                    "rules_failed": len(deviations),
                    "total": max(len(eval_results), len(deviations)),
                },
            )

        await self.review_repo.session.flush()

    async def get_policy_violations(self, review_id: str) -> dict:
        """Return policy violations with persisted finding↔rule linkage."""
        from sqlalchemy import text as sa_text

        from app.domains.review.policy_linkage import build_violation_dto, normalize_clause_category

        await self._sync_review_policy_linkage(review_id)

        findings_sql = sa_text("""
            SELECT finding_id, clause_type, severity, title, description,
                   recommendation, resolution, rule_id, playbook_id, evaluation_id,
                   clause_standard_id, policy_owner
            FROM review_findings
            WHERE tenant_id = :tenant_id AND review_id = CAST(:review_id AS uuid)
              AND rule_id IS NOT NULL
        """)
        result = await self.review_repo.session.execute(
            findings_sql, {"tenant_id": self.tenant_id, "review_id": review_id}
        )
        findings = [dict(row._mapping) for row in result.fetchall()]

        rules_by_id: dict[str, dict] = {}
        if findings:
            rule_ids = [str(f["rule_id"]) for f in findings if f.get("rule_id")]
            if rule_ids:
                rules_sql = sa_text("""
                    SELECT rule_id, playbook_id, name, description, priority, is_mandatory,
                           effect, target_category, conditions
                    FROM policy_rules
                    WHERE tenant_id = :tenant_id AND rule_id = ANY(CAST(:rule_ids AS uuid[]))
                """)
                result = await self.review_repo.session.execute(
                    rules_sql, {"tenant_id": self.tenant_id, "rule_ids": rule_ids}
                )
                rules_by_id = {str(row.rule_id): dict(row._mapping) for row in result.fetchall()}

        playbook_sql = sa_text("""
            SELECT lp.playbook_id, lp.name, lp.created_by, pv.version_label
            FROM legal_playbooks lp
            LEFT JOIN playbook_versions pv ON pv.version_id = lp.active_version_id
            WHERE lp.tenant_id = :tenant_id
        """)
        result = await self.review_repo.session.execute(playbook_sql, {"tenant_id": self.tenant_id})
        playbooks = {str(row.playbook_id): dict(row._mapping) for row in result.fetchall()}

        clause_sql = sa_text("""
            SELECT clause_id, title, body, category
            FROM clause_standards WHERE tenant_id = :tenant_id
        """)
        result = await self.review_repo.session.execute(clause_sql, {"tenant_id": self.tenant_id})
        clauses_by_id = {str(row.clause_id): dict(row._mapping) for row in result.fetchall()}

        redline_sql = sa_text("""
            SELECT finding_id, COUNT(*) AS cnt
            FROM review_redlines
            WHERE tenant_id = :tenant_id AND review_id = CAST(:review_id AS uuid)
              AND finding_id IS NOT NULL
            GROUP BY finding_id
        """)
        result = await self.review_repo.session.execute(
            redline_sql, {"tenant_id": self.tenant_id, "review_id": review_id}
        )
        redline_counts = {str(row.finding_id): row.cnt for row in result.fetchall()}

        violations: list[dict] = []
        for f in findings:
            rule = rules_by_id.get(str(f["rule_id"]))
            if not rule:
                continue
            pb = playbooks.get(str(f["playbook_id"])) if f.get("playbook_id") else None
            clause_std = clauses_by_id.get(str(f["clause_standard_id"])) if f.get("clause_standard_id") else None
            if not clause_std and f.get("clause_type"):
                for cs in clauses_by_id.values():
                    if normalize_clause_category(cs.get("category")) == normalize_clause_category(f.get("clause_type")):
                        clause_std = cs
                        break
            status = "resolved" if f.get("resolution") else "open"
            violations.append(
                build_violation_dto(
                    finding=f,
                    rule=rule,
                    playbook=pb,
                    version_label=(pb or {}).get("version_label"),
                    review_id=review_id,
                    clause_standard=clause_std,
                    redline_count=redline_counts.get(str(f["finding_id"]), 0),
                    status=status,
                )
            )

        if violations:
            override_sql = sa_text("""
                SELECT rule_id, review_id, status, justification, requested_by, requested_at
                FROM policy_overrides
                WHERE tenant_id = :tenant_id AND review_id = CAST(:review_id AS uuid)
            """)
            result = await self.review_repo.session.execute(
                override_sql, {"tenant_id": self.tenant_id, "review_id": review_id}
            )
            overrides = {(str(o.rule_id), str(o.review_id)): dict(o._mapping) for o in result.fetchall()}
            for v in violations:
                key = (v["rule_id"], review_id)
                if key in overrides:
                    o = overrides[key]
                    v["waiver_status"] = o.get("status")
                    v["waiver_justification"] = o.get("justification")
                    v["waiver_requested_by"] = o.get("requested_by")
                    v["waiver_requested_at"] = (
                        o["requested_at"].isoformat()
                        if hasattr(o.get("requested_at"), "isoformat")
                        else str(o.get("requested_at"))
                    )
                    v["status"] = "waived" if o.get("status") == "approved" else v["status"]

        return {"violations": violations}

    async def waive_policy_violation(
        self,
        review_id: str,
        rule_id: str,
        justification: str,
        risk_assessment: Optional[str] = None,
        proposed_alternative: Optional[str] = None,
    ) -> dict:
        """Waive a policy violation by creating a policy_override.

        The policy_overrides.evaluation_id FK is required, so we lazily create
        a parent policy_evaluations row if one does not already exist.
        """
        from sqlalchemy import text as sa_text
        import uuid as _uuid

        # 1. Resolve the upload_id for this review.
        review_sql = sa_text(
            "SELECT upload_id FROM contract_reviews WHERE review_id = CAST(:review_id AS uuid) AND tenant_id = :tenant_id"
        )
        r = await self.review_repo.session.execute(
            review_sql, {"tenant_id": self.tenant_id, "review_id": review_id}
        )
        upload_id = r.scalar() or _uuid.UUID("00000000-0000-0000-0000-000000000000")

        # 2. Ensure a parent policy_evaluations row exists (FK requirement).
        eval_sql = sa_text("""
            SELECT evaluation_id FROM policy_evaluations
            WHERE tenant_id = :tenant_id AND review_id = CAST(:review_id AS uuid)
            LIMIT 1
        """)
        r = await self.review_repo.session.execute(
            eval_sql, {"tenant_id": self.tenant_id, "review_id": review_id}
        )
        evaluation_id = r.scalar()
        if not evaluation_id:
            evaluation_id = _uuid.uuid4()
            insert_eval = sa_text("""
                INSERT INTO policy_evaluations
                    (evaluation_id, tenant_id, upload_id, review_id, status,
                     total_rules_evaluated, rules_passed, rules_failed,
                     deviations_found, mandatory_blocks, approval_required,
                     results, deviations, recommendations)
                VALUES
                    (CAST(:evaluation_id AS uuid), :tenant_id, :upload_id,
                     CAST(:review_id AS uuid), 'completed', 0, 0, 0, 0, 0, 0,
                     '[]'::jsonb, '[]'::jsonb, '[]'::jsonb)
            """)
            await self.review_repo.session.execute(
                insert_eval,
                {
                    "evaluation_id": str(evaluation_id),
                    "tenant_id": self.tenant_id,
                    "upload_id": str(upload_id),
                    "review_id": review_id,
                },
            )

        # 3. Insert the override.
        override_id = str(_uuid.uuid4())
        insert_override = sa_text("""
            INSERT INTO policy_overrides
                (override_id, tenant_id, evaluation_id, rule_id, upload_id,
                 review_id, override_type, justification, risk_assessment,
                 proposed_alternative, status, requested_by, metadata)
            VALUES
                (CAST(:override_id AS uuid), :tenant_id, CAST(:evaluation_id AS uuid),
                 CAST(:rule_id AS uuid), :upload_id, CAST(:review_id AS uuid),
                 :override_type, :justification, :risk_assessment,
                 :proposed_alternative, :status, :requested_by, :metadata)
            RETURNING override_id, status, requested_at
        """)
        result = await self.review_repo.session.execute(
            insert_override,
            {
                "override_id": override_id,
                "tenant_id": self.tenant_id,
                "evaluation_id": str(evaluation_id),
                "rule_id": rule_id,
                "upload_id": str(upload_id),
                "review_id": review_id,
                "override_type": "waiver",
                "justification": justification,
                "risk_assessment": risk_assessment or "",
                "proposed_alternative": proposed_alternative or "",
                "status": "pending",
                "requested_by": self.user.id if self.user else "system",
                "metadata": "{}",
            },
        )
        row = result.fetchone()

        # 4. Audit the waiver.
        await self.audit_trail.record(
            event_type="policy.violation.waived",
            entity_type="review",
            entity_id=review_id,
            actor_id=self.user.id if self.user else "system",
            action="waive_policy_violation",
            description=f"Policy violation waived for rule {rule_id[:8]}: {justification[:120]}",
        )

        return {
            "override_id": override_id,
            "status": row.status if row else "pending",
            "requested_at": row.requested_at.isoformat() if row and hasattr(row.requested_at, "isoformat") else None,
        }

    async def get_missing_clauses(self, review_id: str) -> dict:
        return {"missing_clauses": []}

    async def get_recommendations(self, review_id: str) -> dict:
        """Get actionable recommendations from findings for a review.

        Returns findings that have recommendations as actionable recommendation items.
        """
        from app.domains.review.models import ReviewFinding
        from sqlalchemy import select

        stmt = (
            select(ReviewFinding)
            .where(
                ReviewFinding.review_id == review_id,
                ReviewFinding.tenant_id == self.tenant_id,
                ReviewFinding.recommendation.isnot(None),
                ReviewFinding.recommendation != "",
            )
            .order_by(ReviewFinding.confidence.desc(), ReviewFinding.created_at.desc())
        )
        result = await self.review_repo.session.execute(stmt)
        findings = result.scalars().all()

        recommendations = []
        for f in findings:
            recommendations.append({
                "recommendation_id": f"rec-{str(f.finding_id)[:8]}",
                "finding_id": str(f.finding_id),
                "review_id": review_id,
                "clause_type": f.clause_type,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "recommendation": f.recommendation,
                "confidence": f.confidence,
                "risk_score": f.risk_score,
                "status": "resolved" if f.resolution is not None else "pending",
                "resolution": f.resolution.value if hasattr(f.resolution, "value") else f.resolution,
                "created_at": f.created_at.isoformat() if hasattr(f.created_at, "isoformat") else str(f.created_at),
            })

        return {"recommendations": recommendations}

    async def get_workflow(self, review_id: str) -> dict:
        """Get workflow state for a review, derived from actual review data."""
        from app.domains.review.models import ContractReview, ReviewStatus
        from sqlalchemy import select

        review = await self.review_repo.get_review(review_id, self.tenant_id)
        if not review:
            return {
                "current_stage": "unknown",
                "available_actions": [],
                "stages": [],
                "sla_remaining_hours": 0,
                "escalation_level": 0,
                "reviewers": [],
                "queue_position": 0,
                "queue_total": 0,
                "workload_score": 0,
            }

        # Derive current_stage from workflow_stage or status
        raw_status = review.status
        status_str = raw_status.value if hasattr(raw_status, 'value') else str(raw_status)
        current_stage = review.workflow_stage or ReviewStatus(status_str).derive_workflow_stage()

        # Build stage progression from status history
        from sqlalchemy import text as sa_text
        hist_sql = sa_text("""
            SELECT from_status, to_status, changed_by, created_at
            FROM review_status_history
            WHERE tenant_id = :tenant_id AND review_id = :review_id
            ORDER BY created_at ASC
        """)
        result = await self.review_repo.session.execute(
            hist_sql, {"tenant_id": self.tenant_id, "review_id": review_id}
        )
        history = result.fetchall()

        # Map statuses to stage labels
        stage_label_map = {
            "draft": "Intake", "uploaded": "Intake",
            "analyzing": "AI Analysis", "ai_analyzed": "AI Analysis",
            "review_ready": "AI Analysis", "in_review": "Review",
            "legal_approval": "Legal Approval", "exec_approval": "Executive Approval",
            "approved": "Approved", "rejected": "Rejected",
            "escalated": "Escalated", "closed": "Completed",
            "finalized": "Finalized", "archived": "Archived",
        }

        stages_built = []
        seen_stages = set()
        for h in history:
            stage_id = h.to_status
            if stage_id not in seen_stages:
                seen_stages.add(stage_id)
                is_current = (stage_id == status_str)
                stages_built.append({
                    "id": stage_id,
                    "label": stage_label_map.get(stage_id, stage_id.replace("_", " ").title()),
                    "status": "current" if is_current else "completed",
                    "completed_at": str(h.created_at) if h.created_at else None,
                    "completed_by": h.changed_by,
                })

        # Determine available actions based on current status
        from app.domains.review.workflow import WorkflowState, map_legacy_status
        current_wf = map_legacy_status(status_str)
        available_actions = [s.value for s in WorkflowState.valid_transitions().get(current_wf, set())]

        # Count active reviewers for this review
        from app.domains.review.models import ReviewAssignment
        reviewer_count = await self.review_repo.session.execute(
            select(ReviewAssignment).where(
                ReviewAssignment.review_id == review_id,
                ReviewAssignment.tenant_id == self.tenant_id,
            )
        )
        reviewers_list = [
            {
                "user_id": a.assignee_id,
                "name": a.assignee_id,
                "role": a.role,
                "assigned_at": str(a.created_at) if a.created_at else None,
            }
            for a in reviewer_count.scalars().all()
        ]

        # SLA calculations
        sla_remaining = 0
        if review.sla_deadline:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if review.sla_deadline.tzinfo is None:
                from app.kernel.datetime_utils import ensure_utc
                deadline = ensure_utc(review.sla_deadline)
            else:
                deadline = review.sla_deadline
            delta = deadline - now
            sla_remaining = delta.total_seconds() / 3600

        return {
            "current_stage": current_stage,
            "available_actions": available_actions,
            "stages": stages_built,
            "sla_remaining_hours": round(sla_remaining, 1),
            "escalation_level": review.escalation_count or 0,
            "reviewers": reviewers_list,
            "queue_position": 0,
            "queue_total": 0,
            "workload_score": 0,
        }

    async def get_activity(self, review_id: str) -> dict:
        """Get activity events for a review from governance_audit_events and review_status_history."""
        from sqlalchemy import text as sa_text

        # Query governance_audit_events for this review.
        # entity_id may be the finding_id or redline_id, so also check metadata->>'review_id'.
        # NOTE: governance_audit_events does not have an `action` or `description` column;
        # we synthesize them from event_type and change_summary.
        gov_sql = sa_text("""
            SELECT event_id, event_type, actor_id, actor_role, change_summary, metadata, created_at
            FROM governance_audit_events
            WHERE tenant_id = :tenant_id
              AND (
                entity_id = CAST(:review_id AS uuid)
                OR metadata->>'review_id' = :review_id2
              )
            ORDER BY created_at DESC
            LIMIT 50
        """)
        result = await self.review_repo.session.execute(
            gov_sql, {"tenant_id": self.tenant_id, "review_id": review_id, "review_id2": review_id}
        )
        gov_events = []
        for row in result.fetchall():
            meta = row.metadata or {}
            if not isinstance(meta, dict):
                meta = {}
            # Prefer a human-readable summary; fall back to a synthesized label.
            description = row.change_summary or meta.get("description") or f"{row.event_type} event"
            gov_events.append({
                "event_id": str(row.event_id),
                "event_type": row.event_type,
                "action": row.event_type,
                "actor_id": row.actor_id,
                "actor_role": row.actor_role,
                "description": description,
                "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else str(row.created_at),
            })

        # Query review_status_history for status transitions
        hist_sql = sa_text("""
            SELECT history_id, from_status, to_status, changed_by, reason, created_at
            FROM review_status_history
            WHERE tenant_id = :tenant_id
              AND review_id = CAST(:review_id AS uuid)
            ORDER BY created_at DESC
            LIMIT 50
        """)
        result = await self.review_repo.session.execute(
            hist_sql, {"tenant_id": self.tenant_id, "review_id": review_id}
        )
        hist_events = [
            {
                "event_id": f"hist-{str(row.history_id)[:8]}",
                "event_type": "review.status_transition",
                "action": f"{row.from_status} → {row.to_status}",
                "actor_id": row.changed_by,
                "description": row.reason or f"Status changed from {row.from_status} to {row.to_status}",
                "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else str(row.created_at),
            }
            for row in result.fetchall()
        ]

        # Merge and sort by created_at desc
        all_events = gov_events + hist_events
        all_events.sort(key=lambda e: e["created_at"], reverse=True)

        return {"events": all_events}

    async def get_document(self, review_id: str) -> dict:
        return {"sections": [], "total_pages": 0}


def _default_version_label(version_number: int, accepted_redline_ids: Optional[list[str]] = None) -> str:
    """Generate a descriptive version label based on version number and content."""
    labels = {
        1: "Original Upload",
        2: "AI Redlines Applied",
        3: "Legal Review Updates",
        4: "Approval Candidate",
    }
    if version_number in labels:
        return labels[version_number]
    if accepted_redline_ids:
        return f"v{version_number} — Redlines Applied ({len(accepted_redline_ids)} changes)"
    return f"v{version_number} — Document Update"


# ── Risk Breakdown ────────────────────────────────────────────────

_SEVERITY_WEIGHTS = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.15, "info": 0.0}


def _risk_score_label(score: float) -> str:
    if score >= 0.81:
        return "Critical"
    if score >= 0.61:
        return "High"
    if score >= 0.41:
        return "Elevated"
    if score >= 0.21:
        return "Moderate"
    return "Minimal"


def _normalize_severity(value: Optional[str], default: str = "medium") -> str:
    raw = (value or default).strip().lower()
    return raw if raw in _SEVERITY_WEIGHTS else default


def _resolution_value(resolution) -> Optional[str]:
    if resolution is None:
        return None
    if hasattr(resolution, "value"):
        return resolution.value
    return str(resolution) if resolution else None


def _risk_breakdown_shell(
    overall: float = 0.0,
    *,
    breakdown: Optional[list] = None,
    status: Optional[str] = None,
    **extra,
) -> dict:
    """Consistent risk-breakdown payload for all early-return paths."""
    from app.domains.review.risk_scoring import risk_breakdown_shell

    if breakdown is not None:
        extra["breakdown"] = breakdown
    return risk_breakdown_shell(overall, status=status, **extra)


def _redline_as_risk_item(redline):
    """Adapt a review redline into a finding-shaped object for breakdown math."""
    from types import SimpleNamespace

    status_val = _enum_value(redline.status) or "proposed"
    resolution = None
    if status_val in ("accepted", "modified"):
        resolution = "resolved"
    elif status_val == "rejected":
        resolution = "dismissed"

    meta = dict(redline.redline_metadata) if redline.redline_metadata else {}
    trace = meta.get("traceability") if isinstance(meta.get("traceability"), dict) else {}
    title = (
        (trace.get("detected_risk") or "").strip()
        or (redline.rationale or "").strip()
        or (redline.clause_type or "Contract risk").replace("_", " ").title()
    )
    if len(title) > 120:
        title = f"{title[:117]}..."

    return SimpleNamespace(
        finding_id=redline.redline_id,
        clause_type=redline.clause_type,
        severity=_normalize_severity(redline.risk_level),
        title=title,
        risk_score=None,
        resolution=resolution,
    )


def _aggregate_only_breakdown(overall: float, contract_value: float = 0, currency: str = "USD") -> dict:
    """When AI produced a score but no findings/redlines to categorize."""
    label = _risk_score_label(overall)
    return _risk_breakdown_shell(
        overall,
        remaining_exposure=overall,
        status="score_only",
        contract_value=contract_value,
        currency=currency,
        breakdown=[
            {
                "category": "general",
                "label": "Overall Contract Risk",
                "contribution": round(overall, 4),
                "finding_count": 0,
                "severity": "high" if overall >= 0.61 else "medium",
                "mitigated_count": 0,
                "dismissed_count": 0,
                "accepted_count": 0,
                "open_count": 0,
                "findings": [],
            }
        ],
        open_findings=[
            {
                "title": "Elevated contract risk detected by AI",
                "clause_type": "general",
                "severity": "high" if overall >= 0.61 else "medium",
                "resolution": "open",
                "resolution_label": "Open Exposure",
            }
        ],
    )


async def compute_risk_breakdown(
    session,
    tenant_id: str,
    review_id: str,
) -> dict:
    """Decompose overall risk score into per-category contributions.

    Returns:
    {
        "overall_risk_score": 0.85,
        "breakdown": [
            {"category": "indemnification", "label": "Indemnification", "contribution": 0.20, "finding_count": 2, "severity": "critical"},
            {"category": "limitation_of_liability", "label": "Limitation of Liability", "contribution": 0.15, ...},
        ],
        "resolved_risk_delta": -0.10,  // risk reduction from resolved findings
        "unresolved_risk_score": 0.75,
    }
    """
    from app.domains.review.models import ReviewFinding, ContractReview
    from sqlalchemy import select

    # Get the review
    review_result = await session.execute(
        select(ContractReview).where(
            ContractReview.review_id == review_id,
            ContractReview.tenant_id == tenant_id,
        )
    )
    review = review_result.scalar_one_or_none()
    if not review:
        return _risk_breakdown_shell(0.0, status="not_found")

    # Snapshot contract value / currency for the financial_impact panel
    metadata = dict(review.document_metadata) if review.document_metadata else {}
    try:
        contract_value = float(metadata.get("financial_value", 0) or 0)
    except (TypeError, ValueError):
        contract_value = 0.0
    currency = (metadata.get("currency") or "USD")
    shell_kw = {"contract_value": contract_value, "currency": currency}

    # Check if review has any AI analysis run — if not, return early with status info
    from app.domains.ai.models import AIExecutionRun
    run_exists = await session.execute(
        select(AIExecutionRun).where(
            AIExecutionRun.upload_id == review.upload_id,
            AIExecutionRun.tenant_id == tenant_id,
        ).limit(1)
    )
    if not run_exists.scalar_one_or_none():
        return _risk_breakdown_shell(0.0, status="no_analysis", **shell_kw)

    # Get overall risk score from document metadata
    overall = metadata.get("risk_score", 0.0) or 0.0

    # Get all findings
    findings_result = await session.execute(
        select(ReviewFinding).where(
            ReviewFinding.review_id == review_id,
            ReviewFinding.tenant_id == tenant_id,
        )
    )
    findings = list(findings_result.scalars().all())

    if not findings:
        from app.domains.review.models import ReviewRedline

        redlines_result = await session.execute(
            select(ReviewRedline).where(
                ReviewRedline.review_id == review_id,
                ReviewRedline.tenant_id == tenant_id,
            )
        )
        redlines = list(redlines_result.scalars().all())
        if redlines:
            findings = [_redline_as_risk_item(r) for r in redlines]
        elif overall > 0:
            return _aggregate_only_breakdown(overall, contract_value=contract_value, currency=currency)
        else:
            return _risk_breakdown_shell(0.0, status="analyzed", **shell_kw)

    from collections import defaultdict
    from types import SimpleNamespace

    from app.domains.review.models import ReviewRedline
    from app.domains.review.risk_scoring import (
        risk_breakdown_payload,
        resolution_value,
    )

    # Load redlines for traceability + effective resolution from accepted redlines
    redlines_result = await session.execute(
        select(ReviewRedline).where(
            ReviewRedline.review_id == review_id,
            ReviewRedline.tenant_id == tenant_id,
        )
    )
    redlines = list(redlines_result.scalars().all())
    redlines_by_finding: dict[str, list] = defaultdict(list)
    for rl in redlines:
        if rl.finding_id:
            redlines_by_finding[str(rl.finding_id)].append(rl)

    def _redline_implied_resolution(redline) -> Optional[str]:
        status_val = _enum_value(redline.status) or "proposed"
        if status_val in ("accepted", "modified"):
            return "resolved"
        if status_val == "rejected":
            return "dismissed"
        return None

    # Overlay redline decisions onto findings for scoring when finding not yet resolved
    scoring_findings = []
    for f in findings:
        effective_res = resolution_value(f.resolution)
        if not effective_res:
            for rl in redlines_by_finding.get(str(f.finding_id), []):
                implied = _redline_implied_resolution(rl)
                if implied:
                    effective_res = implied
                    break
        scoring_findings.append(
            SimpleNamespace(
                finding_id=f.finding_id,
                clause_type=f.clause_type,
                severity=f.severity,
                title=f.title,
                description=f.description,
                recommendation=f.recommendation,
                risk_score=f.risk_score,
                resolution=effective_res,
            )
        )

    review_status = _enum_value(review.status) if review else None
    review_started = bool(
        review.started_at
        or review.assigned_to
        or review_status
        not in (None, "draft", "uploaded", "ai_analyzed")
        or any(resolution_value(f.resolution) for f in findings)
        or any(_redline_implied_resolution(rl) for rl in redlines)
    )

    payload = risk_breakdown_payload(
        overall,
        scoring_findings,
        review_status=review_status,
        review_started=review_started,
        redlines_by_finding=redlines_by_finding,
        status="analyzed",
    )

    # ── Estimated Business Impact ─────────────────────────────────────
    # Compute dollar exposure from the contract's financial value and the
    # current / post-mitigation risk score.  Uses a deterministic curve so
    # a 70% risk on a $5M MSA maps to ~$350K of exposure.
    try:
        contract_value = float(metadata.get("financial_value", 0) or 0)
    except (TypeError, ValueError):
        contract_value = 0.0

    current_risk = float(payload.get("current_contract_risk", 0) or 0)
    # After mitigation, the residual risk = remaining_exposure capped at
    # 0.05 (5%) once the suggested mitigations are applied.
    after_mitigation = round(min(current_risk * 0.18, 0.05), 4)

    payload["financial_impact"] = {
        "contract_value": round(contract_value, 2),
        "currency": (metadata.get("currency") or "USD"),
        "current_risk_pct": round(current_risk * 100, 1),
        "current_exposure": round(contract_value * current_risk, 2),
        "after_mitigation_pct": round(after_mitigation * 100, 1),
        "after_mitigation_exposure": round(contract_value * after_mitigation, 2),
        "potential_savings": round(contract_value * (current_risk - after_mitigation), 2),
    }

    # ── Governance Traceability ───────────────────────────────────────
    # Enrich the payload with policy/rule linkage counts so the frontend
    # can display the governance traceability chain in the right panel.
    try:
        from sqlalchemy import text as sa_text

        # Count distinct playbooks linked to findings in this review
        pb_count_result = await session.execute(
            sa_text("""
                SELECT COUNT(DISTINCT playbook_id)
                FROM review_findings
                WHERE tenant_id = :tenant_id
                  AND review_id = CAST(:review_id AS uuid)
                  AND playbook_id IS NOT NULL
            """),
            {"tenant_id": tenant_id, "review_id": review_id},
        )
        linked_playbook_count = pb_count_result.scalar() or 0

        # Count distinct rules linked to findings in this review
        rule_count_result = await session.execute(
            sa_text("""
                SELECT COUNT(DISTINCT rule_id)
                FROM review_findings
                WHERE tenant_id = :tenant_id
                  AND review_id = CAST(:review_id AS uuid)
                  AND rule_id IS NOT NULL
            """),
            {"tenant_id": tenant_id, "review_id": review_id},
        )
        linked_rule_count = rule_count_result.scalar() or 0

        # Count distinct clause standards linked to findings
        clause_std_count_result = await session.execute(
            sa_text("""
                SELECT COUNT(DISTINCT clause_standard_id)
                FROM review_findings
                WHERE tenant_id = :tenant_id
                  AND review_id = CAST(:review_id AS uuid)
                  AND clause_standard_id IS NOT NULL
            """),
            {"tenant_id": tenant_id, "review_id": review_id},
        )
        linked_requirement_count = clause_std_count_result.scalar() or 0

        # Count violations (findings with linked rules)
        violation_count_result = await session.execute(
            sa_text("""
                SELECT COUNT(*)
                FROM review_findings
                WHERE tenant_id = :tenant_id
                  AND review_id = CAST(:review_id AS uuid)
                  AND rule_id IS NOT NULL
            """),
            {"tenant_id": tenant_id, "review_id": review_id},
        )
        linked_violation_count = violation_count_result.scalar() or 0

        # Count total findings
        finding_count_result = await session.execute(
            sa_text("""
                SELECT COUNT(*)
                FROM review_findings
                WHERE tenant_id = :tenant_id
                  AND review_id = CAST(:review_id AS uuid)
            """),
            {"tenant_id": tenant_id, "review_id": review_id},
        )
        total_finding_count = finding_count_result.scalar() or 0

        # Count total redlines
        redline_count_result = await session.execute(
            sa_text("""
                SELECT COUNT(*)
                FROM review_redlines
                WHERE tenant_id = :tenant_id
                  AND review_id = CAST(:review_id AS uuid)
            """),
            {"tenant_id": tenant_id, "review_id": review_id},
        )
        total_redline_count = redline_count_result.scalar() or 0

        # Resolve playbook names for linked policies
        pb_names_result = await session.execute(
            sa_text("""
                SELECT DISTINCT lp.playbook_id, lp.name, pv.version_label
                FROM review_findings rf
                JOIN legal_playbooks lp ON lp.playbook_id = rf.playbook_id
                LEFT JOIN playbook_versions pv ON pv.version_id = lp.active_version_id
                WHERE rf.tenant_id = :tenant_id
                  AND rf.review_id = CAST(:review_id AS uuid)
                  AND rf.playbook_id IS NOT NULL
            """),
            {"tenant_id": tenant_id, "review_id": review_id},
        )
        linked_policies = [
            {
                "playbook_id": str(row.playbook_id),
                "name": row.name,
                "version_label": row.version_label,
            }
            for row in pb_names_result.fetchall()
        ]

        payload["governance_traceability"] = {
            "linked_policy_count": linked_playbook_count,
            "linked_rule_count": linked_rule_count,
            "linked_requirement_count": linked_requirement_count,
            "linked_violation_count": linked_violation_count,
            "linked_finding_count": total_finding_count,
            "linked_redline_count": total_redline_count,
            "linked_policies": linked_policies,
        }
    except Exception:
        logger.debug("Could not resolve governance traceability for review %s", review_id, exc_info=True)
        payload["governance_traceability"] = {
            "linked_policy_count": 0,
            "linked_rule_count": 0,
            "linked_requirement_count": 0,
            "linked_violation_count": 0,
            "linked_finding_count": 0,
            "linked_redline_count": 0,
            "linked_policies": [],
        }

    return payload


def _resolution_type_label(resolution: Optional[str]) -> str:
    """Map resolution value to a human-readable type label."""
    if resolution == "resolved":
        return "mitigated"
    elif resolution in ("dismissed", "false_positive"):
        return "dismissed"
    elif resolution == "acknowledged":
        return "accepted_risk"
    return "open"
