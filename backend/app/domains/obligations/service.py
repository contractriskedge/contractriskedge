"""Obligation Management service — CRUD, KPIs, SLA, timeline, financial, AI, and notifications."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, delete, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.obligations.models import (
    Obligation, ObligationInstance, ObligationReminder, ObligationEscalation,
    ObligationEvidence, SlaMetric, VendorPerformance, FinancialExposure,
    ObligationAuditLog,
)
from app.domains.obligations.schemas import (
    ObligationCreate, ObligationUpdate, ObligationResponse,
    ObligationKpiResponse, ObligationReminderCreate, ObligationReminderResponse,
    ObligationEscalationCreate, ObligationEscalationResponse,
    SlaMetricResponse, SlaBreachResponse, VendorPerformanceResponse,
    VendorRiskResponse, SlaPredictionResponse, TimelineEventResponse,
    FinancialExposureResponse, ValueAtRiskResponse, RiskAnalysisResponse,
    AnomalyResponse, NotificationHistoryResponse, AiReviewRequest,
    ObligationAuditLogResponse,
)

logger = logging.getLogger(__name__)


class ObligationService:
    """Service layer for obligation management operations."""

    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    # ── Helpers ────────────────────────────────────────────────────────

    def _to_response(self, o: Obligation) -> ObligationResponse:
        return ObligationResponse(
            id=str(o.id),
            tenant_id=str(o.tenant_id) if o.tenant_id else None,
            name=o.name,
            description=o.description,
            obligation_type=o.obligation_type,
            status=o.status,
            contract_id=o.contract_id,
            contract_name=o.contract_name,
            vendor=o.vendor,
            owner=o.owner,
            assignee=o.assignee,
            due_date=o.due_date,
            completed_date=o.completed_date,
            risk_score=o.risk_score,
            risk_level=o.risk_level,
            sla_status=o.sla_status,
            sla_remaining_hours=o.sla_remaining_hours,
            financial_impact=o.financial_impact,
            currency=o.currency,
            escalation_level=o.escalation_level,
            ai_risk_prediction=o.ai_risk_prediction,
            ai_confidence=o.ai_confidence,
            clause_reference=o.clause_reference,
            department=o.department,
            business_unit=o.business_unit,
            geography=o.geography,
            is_recurring=o.is_recurring,
            recurrence_pattern=o.recurrence_pattern,
            recurrence_next_date=o.recurrence_next_date,
            attachments_count=o.attachments_count,
            reminders_count=o.reminders_count,
            notes=o.notes,
            is_favorite=o.is_favorite,
            tags=o.tags or [],
            extra_metadata=o.extra_metadata,
            created_at=o.created_at,
            updated_at=o.updated_at,
        )

    # ── CRUD ───────────────────────────────────────────────────────────

    async def _log_audit(
        self, obligation_id: str, action: str, actor: str | None = None,
        changes: dict | None = None, comment: str | None = None,
    ) -> None:
        """Record an audit event for an obligation lifecycle action."""
        log = ObligationAuditLog(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(self.tenant_id),
            obligation_id=uuid.UUID(obligation_id),
            action=action,
            actor=actor or "system",
            changes=changes,
            comment=comment,
        )
        self.session.add(log)

    async def list_obligations(
        self, page=1, page_size=20, status=None, obligation_type=None,
        vendor=None, risk_level=None, sla_status=None, search=None,
        sort_by="updated_at", sort_order="desc",
    ):
        query = select(Obligation).where(Obligation.tenant_id == uuid.UUID(self.tenant_id))
        if status:
            query = query.where(Obligation.status == status)
        if obligation_type:
            query = query.where(Obligation.obligation_type == obligation_type)
        if vendor:
            query = query.where(Obligation.vendor.ilike(f"%{vendor}%"))
        if risk_level:
            query = query.where(Obligation.risk_level == risk_level)
        if sla_status:
            query = query.where(Obligation.sla_status == sla_status)
        if search:
            q = f"%{search}%"
            query = query.where(
                or_(Obligation.name.ilike(q), Obligation.description.ilike(q))
            )
        count_q = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_q) or 0
        sort_col = getattr(Obligation, sort_by, Obligation.updated_at)
        order = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        obligations = result.scalars().all()
        return [self._to_response(o) for o in obligations], total

    async def get_obligation(self, obligation_id: str) -> ObligationResponse:
        from sqlalchemy import select
        # Validate that obligation_id is a valid UUID before querying
        try:
            uid = uuid.UUID(obligation_id)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Obligation not found")
        q = select(Obligation).where(
            and_(Obligation.id == uid, Obligation.tenant_id == uuid.UUID(self.tenant_id))
        )
        o = (await self.session.execute(q)).scalar_one_or_none()
        if not o:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Obligation not found")
        return self._to_response(o)

    async def create_obligation(self, data: ObligationCreate) -> ObligationResponse:
        status = data.status or "draft"
        o = Obligation(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(self.tenant_id),
            name=data.name,
            description=data.description,
            obligation_type=data.obligation_type,
            status=status,
            contract_id=data.contract_id,
            contract_name=data.contract_name,
            vendor=data.vendor,
            owner=data.owner,
            assignee=data.assignee,
            due_date=data.due_date,
            risk_score=data.risk_score or 0,
            risk_level=data.risk_level or "medium",
            financial_impact=data.financial_impact or 0,
            currency=data.currency or "USD",
            clause_reference=data.clause_reference,
            department=data.department,
            business_unit=data.business_unit,
            geography=data.geography,
            is_recurring=data.is_recurring or False,
            recurrence_pattern=data.recurrence_pattern,
            notes=data.notes,
            tags=data.tags or [],
        )
        self.session.add(o)
        await self.session.flush()
        await self.session.refresh(o)
        await self._log_audit(str(o.id), "created", comment=f"Obligation '{o.name}' created with status '{status}'")
        return self._to_response(o)

    async def update_obligation(self, obligation_id: str, data: ObligationUpdate) -> ObligationResponse:
        from sqlalchemy import select
        try:
            uid = uuid.UUID(obligation_id)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Obligation not found")
        q = select(Obligation).where(
            and_(Obligation.id == uid, Obligation.tenant_id == uuid.UUID(self.tenant_id))
        )
        o = (await self.session.execute(q)).scalar_one_or_none()
        if not o:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Obligation not found")

        old_status = o.status
        old_assignee = o.assignee
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(o, key, val)
        o.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(o)

        # Audit: log status changes
        if "status" in update_data and update_data["status"] != old_status:
            await self._log_audit(
                obligation_id, f"status_changed:{old_status}→{update_data['status']}",
                changes={"old_status": old_status, "new_status": update_data["status"]},
            )
        elif "assignee" in update_data and update_data["assignee"] != old_assignee:
            await self._log_audit(
                obligation_id, "assigned",
                comment=f"Assigned to {update_data['assignee']}",
                changes={"old_assignee": old_assignee, "new_assignee": update_data["assignee"]},
            )
        else:
            await self._log_audit(obligation_id, "updated")

        return self._to_response(o)

    # ── Lifecycle Actions ────────────────────────────────────────────

    async def complete_obligation(self, obligation_id: str) -> ObligationResponse:
        """Mark an obligation as completed."""
        o = await self._get_obligation_or_404(obligation_id)
        if o.status in ("completed", "archived", "cancelled"):
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Cannot complete obligation in '{o.status}' state")
        o.status = "completed"
        o.completed_date = datetime.now(timezone.utc)
        o.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(o)
        await self._log_audit(obligation_id, "completed")
        return self._to_response(o)

    async def cancel_obligation(self, obligation_id: str) -> ObligationResponse:
        """Cancel an obligation."""
        o = await self._get_obligation_or_404(obligation_id)
        if o.status in ("completed", "archived", "cancelled"):
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Cannot cancel obligation in '{o.status}' state")
        o.status = "cancelled"
        o.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(o)
        await self._log_audit(obligation_id, "cancelled")
        return self._to_response(o)

    async def archive_obligation(self, obligation_id: str) -> ObligationResponse:
        """Archive an obligation (soft-delete)."""
        o = await self._get_obligation_or_404(obligation_id)
        if o.status == "archived":
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Obligation is already archived")
        o.status = "archived"
        o.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(o)
        await self._log_audit(obligation_id, "archived")
        return self._to_response(o)

    async def delete_obligation(self, obligation_id: str) -> bool:
        """Permanently delete an obligation (admin only)."""
        o = await self._get_obligation_or_404(obligation_id)
        await self._log_audit(obligation_id, "deleted")
        await self.session.delete(o)
        await self.session.flush()
        return True

    async def get_audit_history(self, obligation_id: str) -> list[ObligationAuditLogResponse]:
        """Get audit history for an obligation."""
        from sqlalchemy import select
        try:
            uid = uuid.UUID(obligation_id)
        except ValueError:
            return []
        result = await self.session.execute(
            select(ObligationAuditLog).where(
                and_(
                    ObligationAuditLog.obligation_id == uid,
                    ObligationAuditLog.tenant_id == uuid.UUID(self.tenant_id),
                )
            ).order_by(ObligationAuditLog.created_at.desc())
        )
        return [
            ObligationAuditLogResponse(
                id=str(log.id),
                tenant_id=str(log.tenant_id) if log.tenant_id else None,
                obligation_id=str(log.obligation_id),
                action=log.action,
                actor=log.actor,
                changes=log.changes,
                comment=log.comment,
                created_at=log.created_at,
            )
            for log in result.scalars().all()
        ]

    async def _get_obligation_or_404(self, obligation_id: str) -> Obligation:
        """Get obligation model or raise 404."""
        from sqlalchemy import select
        try:
            uid = uuid.UUID(obligation_id)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Obligation not found")
        q = select(Obligation).where(
            and_(Obligation.id == uid, Obligation.tenant_id == uuid.UUID(self.tenant_id))
        )
        o = (await self.session.execute(q)).scalar_one_or_none()
        if not o:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Obligation not found")
        return o
        from sqlalchemy import select
        try:
            uid = uuid.UUID(obligation_id)
        except ValueError:
            return False
        q = select(Obligation).where(
            and_(Obligation.id == uid, Obligation.tenant_id == uuid.UUID(self.tenant_id))
        )
        o = (await self.session.execute(q)).scalar_one_or_none()
        if not o:
            return False
        await self.session.delete(o)
        await self.session.flush()
        return True

    # ── KPIs ───────────────────────────────────────────────────────────

    async def get_kpis(self) -> ObligationKpiResponse:
        base = select(Obligation).where(Obligation.tenant_id == uuid.UUID(self.tenant_id))
        total = await self.session.scalar(select(func.count()).select_from(base.subquery())) or 0
        active = await self.session.scalar(
            select(func.count()).select_from(
                base.where(Obligation.status.in_(["pending", "in_progress"])).subquery()
            )
        ) or 0
        overdue = await self.session.scalar(
            select(func.count()).select_from(
                base.where(Obligation.status == "overdue").subquery()
            )
        ) or 0
        escalated = await self.session.scalar(
            select(func.count()).select_from(
                base.where(Obligation.escalation_level > 0).subquery()
            )
        ) or 0
        completed = await self.session.scalar(
            select(func.count()).select_from(
                base.where(Obligation.status == "completed").subquery()
            )
        ) or 0
        breached = await self.session.scalar(
            select(func.count()).select_from(
                base.where(Obligation.sla_status == "breached").subquery()
            )
        ) or 0

        scores = await self.session.execute(
            select(Obligation.risk_score).where(
                Obligation.tenant_id == uuid.UUID(self.tenant_id),
                Obligation.risk_score.isnot(None),
            )
        )
        all_scores = [r[0] for r in scores if r[0] is not None]
        avg_risk_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0

        exp_result = await self.session.execute(
            select(func.coalesce(func.sum(Obligation.financial_impact), 0)).where(
                Obligation.tenant_id == uuid.UUID(self.tenant_id),
                Obligation.status != "completed",
            )
        )
        total_exposure = exp_result.scalar() or 0.0

        at_risk_result = await self.session.execute(
            select(func.coalesce(func.sum(Obligation.financial_impact), 0)).where(
                Obligation.tenant_id == uuid.UUID(self.tenant_id),
                Obligation.risk_score >= 7,
            )
        )
        at_risk_amount = at_risk_result.scalar() or 0.0

        pending_review = await self.session.scalar(
            select(func.count()).select_from(
                base.where(Obligation.status == "pending_review").subquery()
            )
        ) or 0

        now = datetime.now(timezone.utc)
        upcoming_due = await self.session.scalar(
            select(func.count()).select_from(
                base.where(
                    Obligation.due_date.isnot(None),
                    Obligation.due_date <= now + timedelta(days=30),
                    Obligation.due_date >= now,
                ).subquery()
            )
        ) or 0

        compliance_rate = round((completed / total * 100), 1) if total > 0 else 0.0

        return ObligationKpiResponse(
            total_obligations=total,
            active_count=active,
            overdue_count=overdue,
            escalated_count=escalated,
            completed_count=completed,
            breached_count=breached,
            avg_risk_score=avg_risk_score,
            total_exposure=total_exposure,
            at_risk_amount=at_risk_amount,
            pending_review=pending_review,
            upcoming_due=upcoming_due,
            compliance_rate=compliance_rate,
        )

    # ── SLA ────────────────────────────────────────────────────────────

    async def get_sla_performance(self) -> list[SlaMetricResponse]:
        result = await self.session.execute(
            select(SlaMetric).where(
                SlaMetric.tenant_id == uuid.UUID(self.tenant_id)
            ).order_by(SlaMetric.measured_at.desc())
        )
        return [
            SlaMetricResponse(
                id=str(m.id),
                tenant_id=str(m.tenant_id) if m.tenant_id else None,
                obligation_id=str(m.obligation_id) if m.obligation_id else None,
                vendor=m.vendor,
                contract_type=m.contract_type,
                sla_target=m.sla_target,
                performance=m.performance,
                trend=m.trend,
                breach_count=m.breach_count,
                status=m.status,
                measured_at=m.measured_at,
                created_at=m.created_at,
            )
            for m in result.scalars().all()
        ]

    async def get_sla_breaches(self) -> list[SlaBreachResponse]:
        result = await self.session.execute(
            select(SlaMetric).where(
                SlaMetric.tenant_id == uuid.UUID(self.tenant_id),
                or_(
                    SlaMetric.status == "breached",
                    SlaMetric.status == "at_risk",
                ),
            ).order_by(SlaMetric.measured_at.desc())
        )
        return [
            SlaBreachResponse(
                id=str(m.id),
                vendor=m.vendor,
                contract_type=m.contract_type,
                performance=m.performance,
                target=m.sla_target,
                breached_at=m.measured_at,
                status=m.status,
            )
            for m in result.scalars().all()
        ]

    async def get_vendor_risk(self) -> list[VendorRiskResponse]:
        result = await self.session.execute(
            select(VendorPerformance).where(
                VendorPerformance.tenant_id == uuid.UUID(self.tenant_id)
            ).order_by(VendorPerformance.score.asc())
        )
        return [
            VendorRiskResponse(
                vendor=v.vendor,
                score=v.score,
                risk_level=v.risk_level,
                breach_count=v.breach_count,
                contract_count=v.contract_count,
                trend=v.trend,
                predicted_risk=v.predicted_risk,
            )
            for v in result.scalars().all()
        ]

    async def get_sla_predictions(self) -> list[SlaPredictionResponse]:
        result = await self.session.execute(
            select(VendorPerformance).where(
                VendorPerformance.tenant_id == uuid.UUID(self.tenant_id)
            )
        )
        vendors = result.scalars().all()
        predictions = []
        for v in vendors:
            if v.score < 80 or v.breach_count > 3:
                predicted_risk = min(100, v.score + v.breach_count * 5 + (100 - v.score) * 0.3)
            else:
                predicted_risk = v.score
            breach_probability = round(predicted_risk / 100, 2)
            if breach_probability >= 0.7:
                risk_level = "high"
                recommendation = "Immediate review required — high breach probability detected."
            elif breach_probability >= 0.4:
                risk_level = "medium"
                recommendation = "Monitor closely — moderate breach probability."
            else:
                risk_level = "low"
                recommendation = "On track — low breach probability."
            predictions.append(SlaPredictionResponse(
                vendor=v.vendor,
                current_performance=v.score,
                predicted_performance=round(predicted_risk, 1),
                breach_probability=breach_probability,
                risk_level=risk_level,
                recommendation=recommendation,
            ))
        return predictions

    # ── Timeline ───────────────────────────────────────────────────────

    async def get_calendar(self, start_date: datetime, end_date: datetime) -> list[TimelineEventResponse]:
        result = await self.session.execute(
            select(Obligation).where(
                Obligation.tenant_id == uuid.UUID(self.tenant_id),
                Obligation.due_date.isnot(None),
                Obligation.due_date >= start_date,
                Obligation.due_date <= end_date,
            ).order_by(Obligation.due_date.asc())
        )
        return [
            TimelineEventResponse(
                id=str(o.id),
                obligation_id=str(o.id),
                title=o.name,
                description=o.description,
                event_type="obligation_due",
                event_date=o.due_date,
                status=o.status,
                vendor=o.vendor,
            )
            for o in result.scalars().all()
        ]

    async def get_upcoming(self, days: int = 30) -> list[ObligationResponse]:
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days)
        result = await self.session.execute(
            select(Obligation).where(
                Obligation.tenant_id == uuid.UUID(self.tenant_id),
                Obligation.due_date.isnot(None),
                Obligation.due_date >= now,
                Obligation.due_date <= future,
                ~Obligation.status.in_(["completed", "waived"]),
            ).order_by(Obligation.due_date.asc())
        )
        return [self._to_response(o) for o in result.scalars().all()]

    async def get_overdue(self) -> list[ObligationResponse]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Obligation).where(
                Obligation.tenant_id == uuid.UUID(self.tenant_id),
                Obligation.due_date.isnot(None),
                Obligation.due_date < now,
                ~Obligation.status.in_(["completed", "waived"]),
            ).order_by(Obligation.due_date.asc())
        )
        return [self._to_response(o) for o in result.scalars().all()]

    # ── Financial ──────────────────────────────────────────────────────

    async def get_financial_exposure(self) -> list[FinancialExposureResponse]:
        result = await self.session.execute(
            select(FinancialExposure).where(
                FinancialExposure.tenant_id == uuid.UUID(self.tenant_id)
            ).order_by(FinancialExposure.as_of_date.desc())
        )
        return [
            FinancialExposureResponse(
                id=str(f.id),
                tenant_id=str(f.tenant_id) if f.tenant_id else None,
                category=f.category,
                total_exposure=f.total_exposure,
                overdue_amount=f.overdue_amount,
                at_risk_amount=f.at_risk_amount,
                recovered_amount=f.recovered_amount,
                trend=f.trend,
                currency=f.currency,
                as_of_date=f.as_of_date,
            )
            for f in result.scalars().all()
        ]

    async def get_penalties(self) -> list[dict]:
        result = await self.session.execute(
            select(
                Obligation.obligation_type,
                func.coalesce(func.sum(Obligation.financial_impact), 0),
            ).where(
                Obligation.tenant_id == uuid.UUID(self.tenant_id),
                Obligation.financial_impact > 0,
                Obligation.status == "overdue",
            ).group_by(Obligation.obligation_type)
        )
        return [
            {"category": category, "total_penalty": round(total, 2)}
            for category, total in result.all()
        ]

    async def get_value_at_risk(self) -> ValueAtRiskResponse:
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(Obligation.financial_impact), 0),
            ).where(
                Obligation.tenant_id == uuid.UUID(self.tenant_id),
                Obligation.risk_score >= 7,
            )
        )
        total_var = result.scalar() or 0.0

        prob_result = await self.session.execute(
            select(Obligation.ai_risk_prediction).where(
                Obligation.tenant_id == uuid.UUID(self.tenant_id),
                Obligation.risk_score >= 7,
                Obligation.ai_risk_prediction.isnot(None),
            )
        )
        predictions = [r[0] for r in prob_result.all() if r[0] is not None]
        probability = round(
            sum(predictions) / len(predictions) / 100, 2
        ) if predictions else 0.0

        cat_result = await self.session.execute(
            select(
                Obligation.obligation_type,
                func.coalesce(func.sum(Obligation.financial_impact), 0),
            ).where(
                Obligation.tenant_id == uuid.UUID(self.tenant_id),
                Obligation.risk_score >= 7,
            ).group_by(Obligation.obligation_type)
        )
        by_category = [
            {"category": cat, "value_at_risk": round(val, 2)}
            for cat, val in cat_result.all()
        ]

        return ValueAtRiskResponse(
            total_var=round(total_var, 2),
            probability=probability,
            confidence_level=0.95,
            by_category=by_category,
        )

    # ── AI ─────────────────────────────────────────────────────────────

    async def get_risk_analysis(self, obligation_id: str) -> RiskAnalysisResponse:
        from sqlalchemy import select
        q = select(Obligation).where(
            and_(Obligation.id == uuid.UUID(obligation_id), Obligation.tenant_id == uuid.UUID(self.tenant_id))
        )
        o = (await self.session.execute(q)).scalar_one_or_none()
        if not o:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Obligation not found")

        escalation_recommended = o.risk_score >= 7 or o.ai_risk_prediction >= 60
        breach_probability = round(
            (o.risk_score / 10 * 0.6 + o.ai_risk_prediction / 100 * 0.4), 2
        )
        if escalation_recommended:
            recommended_action = "Escalate to management for immediate review"
            analysis = (
                f"Obligation '{o.name}' has a risk score of {o.risk_score} and "
                f"AI risk prediction of {o.ai_risk_prediction}. "
                f"Escalation is recommended."
            )
        else:
            recommended_action = "Continue monitoring"
            analysis = (
                f"Obligation '{o.name}' is within acceptable risk thresholds "
                f"(risk score: {o.risk_score}, AI prediction: {o.ai_risk_prediction})."
            )

        return RiskAnalysisResponse(
            obligation_id=str(o.id),
            risk_score=o.risk_score,
            risk_level=o.risk_level,
            breach_probability=breach_probability,
            escalation_recommended=escalation_recommended,
            recommended_action=recommended_action,
            confidence=o.ai_confidence,
            analysis=analysis,
        )

    async def get_escalations(self) -> list[ObligationEscalationResponse]:
        result = await self.session.execute(
            select(ObligationEscalation).where(
                ObligationEscalation.tenant_id == uuid.UUID(self.tenant_id),
                ObligationEscalation.status == "active",
            ).order_by(ObligationEscalation.created_at.desc())
        )
        return [
            ObligationEscalationResponse(
                id=str(e.id),
                tenant_id=str(e.tenant_id) if e.tenant_id else None,
                obligation_id=str(e.obligation_id),
                escalation_level=e.escalation_level,
                escalated_to=e.escalated_to,
                reason=e.reason,
                status=e.status,
                resolved_at=e.resolved_at,
                resolution_notes=e.resolution_notes,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in result.scalars().all()
        ]

    async def get_anomalies(self) -> list[AnomalyResponse]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Obligation).where(
                Obligation.tenant_id == uuid.UUID(self.tenant_id),
                or_(
                    and_(Obligation.status == "overdue", Obligation.escalation_level == 0),
                    and_(Obligation.risk_score >= 8, Obligation.status == "pending"),
                    and_(Obligation.sla_status == "breached", Obligation.escalation_level == 0),
                ),
            )
        )
        anomalies = []
        for o in result.scalars().all():
            if o.status == "overdue" and o.escalation_level == 0:
                anomaly_type = "overdue_not_escalated"
                severity = "high"
                desc = f"Obligation '{o.name}' is overdue but not escalated."
            elif o.risk_score >= 8 and o.status == "pending":
                anomaly_type = "high_risk_pending"
                severity = "critical"
                desc = f"High-risk obligation '{o.name}' is still in pending status."
            elif o.sla_status == "breached" and o.escalation_level == 0:
                anomaly_type = "sla_breach_not_escalated"
                severity = "high"
                desc = f"SLA breach detected for '{o.name}' with no escalation."
            else:
                continue
            anomalies.append(AnomalyResponse(
                id=str(o.id),
                obligation_id=str(o.id),
                anomaly_type=anomaly_type,
                severity=severity,
                description=desc,
                detected_at=now,
                score=o.risk_score,
            ))
        return anomalies

    async def ai_review(self, request: AiReviewRequest) -> dict:
        from sqlalchemy import select
        q = select(Obligation).where(
            and_(Obligation.id == uuid.UUID(request.obligation_id), Obligation.tenant_id == uuid.UUID(self.tenant_id))
        )
        o = (await self.session.execute(q)).scalar_one_or_none()
        if not o:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Obligation not found")

        now = datetime.now(timezone.utc)
        days_until_due = (o.due_date - now).days if o.due_date and o.due_date > now else 0

        risk_factor = o.risk_score / 10
        sla_factor = 1.0 if o.sla_status == "breached" else 0.6 if o.sla_status == "at_risk" else 0.3
        time_factor = max(0, 1 - days_until_due / 365)
        breach_probability = round(min(1.0, risk_factor * 0.5 + sla_factor * 0.3 + time_factor * 0.2), 2)

        if breach_probability >= 0.7:
            recommended_action = "Immediate escalation required"
        elif breach_probability >= 0.4:
            recommended_action = "Schedule review within 7 days"
        else:
            recommended_action = "No action needed"

        return {
            "obligation_id": str(o.id),
            "obligation_name": o.name,
            "risk_score": o.risk_score,
            "risk_level": o.risk_level,
            "sla_status": o.sla_status,
            "days_until_due": days_until_due,
            "breach_probability": breach_probability,
            "recommended_action": recommended_action,
            "confidence": o.ai_confidence,
        }

    # ── Notifications ──────────────────────────────────────────────────

    async def create_reminder(self, data: ObligationReminderCreate) -> ObligationReminderResponse:
        r = ObligationReminder(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(self.tenant_id),
            obligation_id=uuid.UUID(data.obligation_id),
            reminder_type=data.reminder_type,
            remind_at=data.remind_at,
            message=data.message,
            status="pending",
        )
        self.session.add(r)
        await self.session.flush()
        await self.session.refresh(r)
        await self._log_audit(
            data.obligation_id, "reminder_sent",
            comment=f"Reminder '{data.reminder_type}' scheduled for {data.remind_at.isoformat()}",
        )
        return ObligationReminderResponse(
            id=str(r.id),
            tenant_id=str(r.tenant_id) if r.tenant_id else None,
            obligation_id=str(r.obligation_id),
            reminder_type=r.reminder_type,
            remind_at=r.remind_at,
            sent_at=r.sent_at,
            message=r.message,
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )

    async def create_escalation(self, data: ObligationEscalationCreate) -> ObligationEscalationResponse:
        e = ObligationEscalation(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(self.tenant_id),
            obligation_id=uuid.UUID(data.obligation_id),
            escalation_level=data.escalation_level,
            escalated_to=data.escalated_to,
            reason=data.reason,
            status="active",
        )
        self.session.add(e)

        from sqlalchemy import select
        q = select(Obligation).where(
            and_(Obligation.id == uuid.UUID(data.obligation_id), Obligation.tenant_id == uuid.UUID(self.tenant_id))
        )
        o = (await self.session.execute(q)).scalar_one_or_none()
        if o:
            o.escalation_level = data.escalation_level
            o.updated_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(e)
        await self._log_audit(
            data.obligation_id, "escalated",
            comment=f"Escalated to {data.escalated_to} (level {data.escalation_level})",
        )
        return ObligationEscalationResponse(
            id=str(e.id),
            tenant_id=str(e.tenant_id) if e.tenant_id else None,
            obligation_id=str(e.obligation_id),
            escalation_level=e.escalation_level,
            escalated_to=e.escalated_to,
            reason=e.reason,
            status=e.status,
            resolved_at=e.resolved_at,
            resolution_notes=e.resolution_notes,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )

    async def get_notification_history(self) -> list[NotificationHistoryResponse]:
        result = await self.session.execute(
            select(ObligationAuditLog).where(
                ObligationAuditLog.tenant_id == uuid.UUID(self.tenant_id),
                or_(
                    ObligationAuditLog.action.ilike("%reminder%"),
                    ObligationAuditLog.action.ilike("%escalation%"),
                ),
            ).order_by(ObligationAuditLog.created_at.desc())
        )
        return [
            NotificationHistoryResponse(
                id=str(log.id),
                notification_type="reminder" if "reminder" in (log.action or "").lower() else "escalation",
                recipient=log.actor or "",
                message=log.comment or "",
                status="sent" if log.action else "pending",
                sent_at=log.created_at,
                created_at=log.created_at,
            )
            for log in result.scalars().all()
        ]
