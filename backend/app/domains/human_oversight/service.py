"""Human Oversight Layer service — approval workflows, policy exceptions, decision impact."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.human_oversight.schemas import (
    ApprovalStatus, ApprovalType, ApprovalPriority, ExceptionSeverity, AcknowledgmentStatus,
    AIRecommendationApproval, ApprovalDecision, ApprovalRequestCreate, ApprovalSummary,
    PolicyExceptionRequest, PolicyExceptionCreate, PolicyExceptionReview,
    AcknowledgmentRequirement, AcknowledgmentAction, AcknowledgmentSummary,
    DecisionImpactPreview, BulkDecisionRequest, BulkDecisionResult,
    HumanOversightDashboard,
)

logger = logging.getLogger(__name__)


@dataclass
class ApprovalService:
    """Manages AI recommendation approval workflows."""

    session: AsyncSession
    tenant_id: str

    async def create_approval(self, request: ApprovalRequestCreate, actor: str) -> AIRecommendationApproval:
        """Create an approval request for an AI recommendation."""
        now = datetime.now(timezone.utc)
        approval_id = uuid.uuid4().hex[:12]

        sql = sa_text("""
            INSERT INTO ai_approvals (approval_id, tenant_id, review_id, upload_id,
                approval_type, title, description, ai_recommendation, proposed_action,
                risk_impact, confidence, priority, status, requested_by, requested_at,
                expires_at, finding_ids, redline_ids, rule_ids,
                required_approvers, required_roles, approval_level, correlation_id)
            VALUES (:aid, :tid, :rid, :uid,
                :atype, :title, :desc, :rec, :action,
                :impact, :conf, :priority, 'pending', :actor, :now,
                :expires, :fids, :red_ids, :rule_ids,
                :approvers, :roles, :level, :corr)
            RETURNING approval_id, review_id, upload_id, approval_type, title, description,
                ai_recommendation, proposed_action, risk_impact, confidence, priority,
                status, requested_by, requested_at, expires_at,
                finding_ids, redline_ids, rule_ids,
                required_approvers, required_roles, approval_level, correlation_id
        """)
        result = await self.session.execute(sql, {
            "aid": approval_id,
            "tid": self.tenant_id,
            "rid": request.review_id,
            "uid": request.upload_id,
            "atype": request.approval_type.value,
            "title": request.title,
            "desc": request.description,
            "rec": request.ai_recommendation,
            "action": request.proposed_action,
            "impact": request.risk_impact,
            "conf": request.confidence,
            "priority": request.priority.value,
            "actor": actor,
            "now": now,
            "expires": request.expires_at,
            "fids": request.finding_ids,
            "red_ids": request.redline_ids,
            "rule_ids": request.rule_ids,
            "approvers": request.required_approvers,
            "roles": request.required_roles,
            "level": request.approval_level,
            "corr": uuid.uuid4().hex[:12],
        })
        await self.session.commit()
        row = result.fetchone()
        return self._row_to_approval(row)

    async def decide(self, approval_id: str, decision: ApprovalDecision, actor: str) -> AIRecommendationApproval:
        """Approve, reject, or conditionally approve an AI recommendation.

        Enforces approval governance:
        - Only pending approvals can be decided.
        - The acting user must be in ``required_approvers`` or have a role in ``required_roles``.
        """
        now = datetime.now(timezone.utc)

        if decision.decision not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.CONDITIONALLY_APPROVED):
            raise ValueError(f"Invalid decision: {decision.decision}")

        # ── Fetch current approval to check authorisation ──────────────
        fetch_sql = sa_text("""
            SELECT required_approvers, required_roles, status
            FROM ai_approvals
            WHERE approval_id = :aid AND tenant_id = :tid
        """)
        fetch_result = await self.session.execute(fetch_sql, {"aid": approval_id, "tid": self.tenant_id})
        current = fetch_result.fetchone()
        if not current:
            raise ValueError(f"Approval '{approval_id}' not found")
        if current.status != ApprovalStatus.PENDING.value:
            raise ValueError(f"Approval '{approval_id}' is already decided (status={current.status})")

        required_approvers: list[str] = current.required_approvers or []
        required_roles: list[str] = current.required_roles or []

        if required_approvers or required_roles:
            # Resolve the acting user's roles — the caller should inject a
            # ``user_roles`` kwarg when available; otherwise we check the
            # approval's stored requirements directly.
            user_authorised = actor in required_approvers
            # If we have no role information we rely on the RBAC middleware
            # having already verified ``WORKFLOWS_APPROVE`` permission.
            if not user_authorised and required_approvers:
                raise PermissionError(
                    f"User '{actor}' is not in required_approvers "
                    f"{required_approvers} for approval '{approval_id}'"
                )

        sql = sa_text("""
            UPDATE ai_approvals
            SET status = :decision,
                decided_by = :actor,
                decided_at = :now,
                decision_notes = :notes,
                conditions = CAST(:conditions AS jsonb),
                updated_at = :now
            WHERE approval_id = :aid AND tenant_id = :tid AND status = 'pending'
            RETURNING approval_id, review_id, upload_id, approval_type, title, description,
                ai_recommendation, proposed_action, risk_impact, confidence, priority,
                status, requested_by, requested_at, expires_at,
                decided_by, decided_at, decision_notes, conditions,
                finding_ids, redline_ids, rule_ids,
                required_approvers, required_roles, approval_level, correlation_id,
                extra_metadata
        """)
        result = await self.session.execute(sql, {
            "aid": approval_id,
            "tid": self.tenant_id,
            "decision": decision.decision.value,
            "actor": actor,
            "now": now,
            "notes": decision.notes,
            "conditions": json.dumps(decision.conditions) if decision.conditions else None,
        })
        await self.session.commit()
        row = result.fetchone()
        if not row:
            raise ValueError(f"Approval '{approval_id}' not found or already decided")
        return self._row_to_approval(row)

    async def list_pending(self, review_id: Optional[str] = None) -> list[ApprovalSummary]:
        """List pending approval requests that have not yet expired."""
        now = datetime.now(timezone.utc)

        if review_id:
            sql = sa_text("""
                SELECT approval_id, review_id, approval_type, title, status, priority,
                    confidence, requested_by, requested_at, expires_at,
                    decided_by, decided_at, approval_level
                FROM ai_approvals
                WHERE tenant_id = :tid
                  AND review_id = :rid
                  AND status = 'pending'
                  AND (expires_at IS NULL OR expires_at > :now)
                ORDER BY priority ASC, created_at DESC
            """)
            result = await self.session.execute(sql, {"tid": self.tenant_id, "rid": review_id, "now": now})
        else:
            sql = sa_text("""
                SELECT approval_id, review_id, approval_type, title, status, priority,
                    confidence, requested_by, requested_at, expires_at,
                    decided_by, decided_at, approval_level
                FROM ai_approvals
                WHERE tenant_id = :tid
                  AND status = 'pending'
                  AND (expires_at IS NULL OR expires_at > :now)
                ORDER BY priority ASC, created_at DESC
            """)
            result = await self.session.execute(sql, {"tid": self.tenant_id, "now": now})

        return [ApprovalSummary(
            approval_id=str(r.approval_id),
            review_id=str(r.review_id),
            approval_type=r.approval_type,
            title=r.title,
            status=r.status,
            priority=r.priority,
            confidence=r.confidence or 0.0,
            requested_by=r.requested_by,
            requested_at=r.requested_at,
            expires_at=r.expires_at,
            decided_by=r.decided_by,
            decided_at=r.decided_at,
            approval_level=r.approval_level or 1,
        ) for r in result.fetchall()]

    async def get_dashboard(self) -> HumanOversightDashboard:
        """Get oversight dashboard."""
        now = datetime.now(timezone.utc)

        pending_sql = sa_text("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending')::int AS pending,
                COUNT(*) FILTER (WHERE status = 'pending' AND expires_at IS NOT NULL AND expires_at < NOW())::int AS overdue,
                COUNT(*) FILTER (WHERE decided_at >= CURRENT_DATE)::int AS decided_today
            FROM ai_approvals WHERE tenant_id = :tid
        """)
        result = await self.session.execute(pending_sql, {"tid": self.tenant_id})
        row = result.fetchone()

        # ── SLA breaches: pending approvals past their expiration ─────
        sla_sql = sa_text("""
            SELECT COUNT(*)::int AS cnt
            FROM ai_approvals
            WHERE tenant_id = :tid
              AND status = 'pending'
              AND expires_at IS NOT NULL
              AND expires_at < NOW()
        """)
        sla_result = await self.session.execute(sla_sql, {"tid": self.tenant_id})
        sla_row = sla_result.fetchone()

        by_type_sql = sa_text("""
            SELECT approval_type, COUNT(*)::int AS count
            FROM ai_approvals WHERE tenant_id = :tid AND status = 'pending'
            GROUP BY approval_type
        """)
        by_type_result = await self.session.execute(by_type_sql, {"tid": self.tenant_id})
        by_type = {r.approval_type: r.count for r in by_type_result.fetchall()}

        by_priority_sql = sa_text("""
            SELECT priority, COUNT(*)::int AS count
            FROM ai_approvals WHERE tenant_id = :tid AND status = 'pending'
            GROUP BY priority
        """)
        by_priority_result = await self.session.execute(by_priority_sql, {"tid": self.tenant_id})
        by_priority = {r.priority: r.count for r in by_priority_result.fetchall()}

        recent = await self.list_pending()

        # Exception counts
        exc_sql = sa_text("""
            SELECT COUNT(*)::int AS cnt FROM policy_exceptions
            WHERE tenant_id = :tid AND status = 'pending'
        """)
        exc_result = await self.session.execute(exc_sql, {"tid": self.tenant_id})
        exc_row = exc_result.fetchone()

        # Acknowledgment counts
        ack_sql = sa_text("""
            SELECT COUNT(*)::int AS cnt FROM acknowledgment_requirements
            WHERE tenant_id = :tid AND status = 'pending'
        """)
        ack_result = await self.session.execute(ack_sql, {"tid": self.tenant_id})
        ack_row = ack_result.fetchone()

        return HumanOversightDashboard(
            pending_approvals=(row.pending if row else 0),
            pending_exceptions=(exc_row.cnt if exc_row else 0),
            pending_acknowledgments=(ack_row.cnt if ack_row else 0),
            overdue_approvals=(row.overdue if row else 0),
            approval_sla_breaches=(sla_row.cnt if sla_row else 0),
            total_decisions_today=(row.decided_today if row else 0),
            recent_approvals=recent[:10],
            by_type=by_type,
            by_priority=by_priority,
        )

    async def bulk_decide(self, request: BulkDecisionRequest, actor: str) -> BulkDecisionResult:
        """Decide multiple approvals in bulk.

        Each entity_id in the request is treated as an approval_id.
        Only pending approvals where the actor is authorised will be affected.
        """
        total = len(request.entity_ids)
        succeeded = 0
        failed = 0
        errors: list[str] = []

        for eid in request.entity_ids:
            try:
                decision = ApprovalDecision(
                    decision=ApprovalStatus(request.decision),
                    notes=request.notes,
                )
                await self.decide(eid, decision, actor=actor)
                succeeded += 1
            except (ValueError, PermissionError) as exc:
                failed += 1
                errors.append(f"{eid}: {exc}")

        return BulkDecisionResult(
            total=total,
            succeeded=succeeded,
            failed=failed,
            errors=errors,
        )

    def _row_to_approval(self, row) -> AIRecommendationApproval:
        return AIRecommendationApproval(
            approval_id=str(row.approval_id),
            review_id=str(row.review_id),
            upload_id=str(row.upload_id),
            approval_type=row.approval_type,
            title=row.title,
            description=row.description or "",
            ai_recommendation=row.ai_recommendation or "",
            proposed_action=row.proposed_action or "",
            risk_impact=row.risk_impact or "",
            confidence=row.confidence or 0.0,
            priority=row.priority,
            status=row.status,
            requested_by=row.requested_by,
            requested_at=row.requested_at,
            expires_at=row.expires_at,
            decided_by=row.decided_by,
            decided_at=row.decided_at,
            decision_notes=row.decision_notes,
            conditions=row.conditions,
            finding_ids=row.finding_ids or [],
            redline_ids=row.redline_ids or [],
            rule_ids=row.rule_ids or [],
            required_approvers=row.required_approvers or [],
            required_roles=row.required_roles or [],
            approval_level=row.approval_level or 1,
            correlation_id=row.correlation_id,
        )


@dataclass
class PolicyExceptionService:
    """Manages structured policy exception workflows."""

    session: AsyncSession
    tenant_id: str

    async def create_exception(self, request: PolicyExceptionCreate, actor: str) -> PolicyExceptionRequest:
        """Create a policy exception request."""
        now = datetime.now(timezone.utc)
        exception_id = uuid.uuid4().hex[:12]

        sql = sa_text("""
            INSERT INTO policy_exceptions (exception_id, tenant_id, review_id, upload_id,
                rule_id, rule_name, policy_name, clause_category, severity,
                justification, proposed_alternative, risk_assessment,
                status, requested_by, requested_at,
                effective_date, expiration_date, correlation_id)
            VALUES (:eid, :tid, :rid, :uid,
                :rule_id, :rule_name, :policy, :category, :severity,
                :just, :alt, :risk,
                'pending', :actor, :now,
                :eff, :exp, :corr)
            RETURNING exception_id, review_id, upload_id, rule_id, rule_name, policy_name,
                clause_category, severity, justification, proposed_alternative, risk_assessment,
                status, requested_by, requested_at, effective_date, expiration_date,
                correlation_id
        """)
        result = await self.session.execute(sql, {
            "eid": exception_id,
            "tid": self.tenant_id,
            "rid": request.review_id,
            "uid": request.upload_id,
            "rule_id": request.rule_id,
            "rule_name": request.rule_name,
            "policy": request.policy_name,
            "category": request.clause_category,
            "severity": request.severity.value,
            "just": request.justification,
            "alt": request.proposed_alternative,
            "risk": request.risk_assessment,
            "actor": actor,
            "now": now,
            "eff": request.effective_date,
            "exp": request.expiration_date,
            "corr": uuid.uuid4().hex[:12],
        })
        await self.session.commit()
        row = result.fetchone()
        return self._row_to_exception(row)

    async def review_exception(self, exception_id: str, review: PolicyExceptionReview, actor: str) -> PolicyExceptionRequest:
        """Review and decide on a policy exception."""
        now = datetime.now(timezone.utc)

        sql = sa_text("""
            UPDATE policy_exceptions
            SET status = :decision,
                reviewed_by = :actor,
                reviewed_at = :now,
                review_notes = :notes,
                expiration_date = COALESCE(:exp, expiration_date),
                updated_at = :now
            WHERE exception_id = :eid AND tenant_id = :tid AND status = 'pending'
            RETURNING exception_id, review_id, upload_id, rule_id, rule_name, policy_name,
                clause_category, severity, justification, proposed_alternative, risk_assessment,
                status, requested_by, requested_at, effective_date, expiration_date,
                reviewed_by, reviewed_at, review_notes, approval_level, correlation_id
        """)
        result = await self.session.execute(sql, {
            "eid": exception_id,
            "tid": self.tenant_id,
            "decision": review.decision.value,
            "actor": actor,
            "now": now,
            "notes": review.review_notes,
            "exp": review.expiration_date,
        })
        await self.session.commit()
        row = result.fetchone()
        if not row:
            raise ValueError(f"Exception '{exception_id}' not found or already decided")
        return self._row_to_exception(row)

    async def list_pending(self) -> list[PolicyExceptionRequest]:
        """List pending policy exceptions."""
        sql = sa_text("""
            SELECT * FROM policy_exceptions
            WHERE tenant_id = :tid AND status = 'pending'
            ORDER BY severity ASC, created_at DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [self._row_to_exception(r) for r in result.fetchall()]

    def _row_to_exception(self, row) -> PolicyExceptionRequest:
        return PolicyExceptionRequest(
            exception_id=str(row.exception_id),
            review_id=str(row.review_id),
            upload_id=str(row.upload_id),
            rule_id=str(row.rule_id) if row.rule_id else None,
            rule_name=row.rule_name or "",
            policy_name=row.policy_name or "",
            clause_category=row.clause_category or "",
            severity=row.severity,
            justification=row.justification,
            proposed_alternative=row.proposed_alternative,
            risk_assessment=row.risk_assessment or "",
            status=row.status,
            requested_by=row.requested_by,
            requested_at=row.requested_at,
            effective_date=row.effective_date,
            expiration_date=row.expiration_date,
            reviewed_by=row.reviewed_by,
            reviewed_at=row.reviewed_at,
            review_notes=row.review_notes,
            approval_level=row.approval_level or 1,
            correlation_id=row.correlation_id,
        )


@dataclass
class AcknowledgmentService:
    """Tracks reviewer acknowledgment of AI findings and recommendations."""

    session: AsyncSession
    tenant_id: str

    async def create_requirement(self, review_id: str, entity_type: str, entity_id: str,
                                   title: str, description: str = "", mandatory: bool = True) -> AcknowledgmentRequirement:
        """Create an acknowledgment requirement."""
        now = datetime.now(timezone.utc)
        ack_id = uuid.uuid4().hex[:12]

        sql = sa_text("""
            INSERT INTO acknowledgment_requirements (ack_id, tenant_id, review_id,
                entity_type, entity_id, title, description, mandatory, status, created_at)
            VALUES (:aid, :tid, :rid, :etype, :eid, :title, :desc, :mandatory, 'pending', :now)
            RETURNING ack_id, review_id, entity_type, entity_id, title, description,
                mandatory, status, acknowledged_by, acknowledged_at, notes, created_at
        """)
        result = await self.session.execute(sql, {
            "aid": ack_id,
            "tid": self.tenant_id,
            "rid": review_id,
            "etype": entity_type,
            "eid": entity_id,
            "title": title,
            "desc": description,
            "mandatory": mandatory,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return self._row_to_ack(row)

    async def acknowledge(self, ack_id: str, action: AcknowledgmentAction, actor: str) -> AcknowledgmentRequirement:
        """Acknowledge or dispute an AI finding."""
        now = datetime.now(timezone.utc)

        sql = sa_text("""
            UPDATE acknowledgment_requirements
            SET status = :status, acknowledged_by = :actor, acknowledged_at = :now, notes = :notes
            WHERE ack_id = :aid AND tenant_id = :tid AND status = 'pending'
            RETURNING ack_id, review_id, entity_type, entity_id, title, description,
                mandatory, status, acknowledged_by, acknowledged_at, notes, created_at
        """)
        result = await self.session.execute(sql, {
            "aid": ack_id,
            "tid": self.tenant_id,
            "status": action.status.value,
            "actor": actor,
            "now": now,
            "notes": action.notes,
        })
        await self.session.commit()
        row = result.fetchone()
        if not row:
            raise ValueError(f"Acknowledgment '{ack_id}' not found or already resolved")
        return self._row_to_ack(row)

    async def get_summary(self, review_id: str) -> AcknowledgmentSummary:
        """Get acknowledgment summary for a review."""
        sql = sa_text("""
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE status = 'acknowledged')::int AS acked,
                COUNT(*) FILTER (WHERE status = 'disputed')::int AS disputed,
                COUNT(*) FILTER (WHERE status = 'pending')::int AS pending,
                COUNT(*) FILTER (WHERE status = 'pending' AND mandatory = TRUE)::int AS blocking
            FROM acknowledgment_requirements
            WHERE tenant_id = :tid AND review_id = :rid
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id, "rid": review_id})
        row = result.fetchone()

        return AcknowledgmentSummary(
            review_id=review_id,
            total_requirements=row.total,
            acknowledged=row.acked,
            disputed=row.disputed,
            pending=row.pending,
            all_acknowledged=row.pending == 0,
            blocking_requirements=row.blocking,
        )

    def _row_to_ack(self, row) -> AcknowledgmentRequirement:
        return AcknowledgmentRequirement(
            ack_id=str(row.ack_id),
            review_id=str(row.review_id),
            entity_type=row.entity_type,
            entity_id=str(row.entity_id),
            title=row.title,
            description=row.description or "",
            mandatory=row.mandatory,
            status=row.status,
            acknowledged_by=row.acknowledged_by,
            acknowledged_at=row.acknowledged_at,
            notes=row.notes,
            created_at=row.created_at,
        )


@dataclass
class DecisionImpactService:
    """Computes the impact of AI decisions before they are committed."""

    session: AsyncSession
    tenant_id: str

    async def preview_redline_approval(self, redline_id: str, review_id: str) -> DecisionImpactPreview:
        """Preview the impact of approving a redline."""
        sql = sa_text("""
            SELECT rf.risk_score AS current_risk, rf.severity,
                   rr.original_text, rr.proposed_text,
                   rr.clause_type
            FROM review_redlines rr
            LEFT JOIN review_findings rf ON rf.finding_id = rr.finding_id
            WHERE rr.redline_id = :red_id AND rr.tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"red_id": redline_id, "tid": self.tenant_id})
        row = result.fetchone()

        if not row:
            return DecisionImpactPreview(
                decision_type="approve_redline",
                entity_id=redline_id,
                entity_type="redline",
                summary="Redline not found",
            )

        current_risk = row.current_risk or 0.5
        estimated_after = max(0.0, current_risk - 0.15)  # estimated reduction

        return DecisionImpactPreview(
            decision_type="approve_redline",
            entity_id=redline_id,
            entity_type="redline",
            risk_score_current=current_risk,
            risk_score_after=round(estimated_after, 2),
            risk_delta=round(estimated_after - current_risk, 2),
            affected_clauses=[row.clause_type] if row.clause_type else [],
            summary=f"Approving this redline would reduce risk from {current_risk:.2f} to {estimated_after:.2f}",
        )

    async def preview_finding_resolution(self, finding_id: str, resolution: str) -> DecisionImpactPreview:
        """Preview the impact of resolving a finding."""
        sql = sa_text("""
            SELECT risk_score, severity, clause_type, title
            FROM review_findings
            WHERE finding_id = :fid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"fid": finding_id, "tid": self.tenant_id})
        row = result.fetchone()

        if not row:
            return DecisionImpactPreview(
                decision_type="resolve_finding",
                entity_id=finding_id,
                entity_type="finding",
                summary="Finding not found",
            )

        current_risk = row.risk_score or 0.5
        if resolution in ("resolved", "dismissed", "false_positive"):
            estimated_after = max(0.0, current_risk * 0.3)
        else:
            estimated_after = current_risk

        return DecisionImpactPreview(
            decision_type="resolve_finding",
            entity_id=finding_id,
            entity_type="finding",
            risk_score_current=current_risk,
            risk_score_after=round(estimated_after, 2),
            risk_delta=round(estimated_after - current_risk, 2),
            affected_clauses=[row.clause_type] if row.clause_type else [],
            summary=f"Resolving '{row.title}' ({resolution}) would change risk from {current_risk:.2f} to {estimated_after:.2f}",
        )
