"""Compliance domain service — CRUD for frameworks, controls, assessments, findings, exceptions, evidence."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.compliance.models import (
    ComplianceFrameworkModel,
    ComplianceControlModel,
    ComplianceAssessmentModel,
    ComplianceFindingModel,
    ComplianceExceptionModel,
    ComplianceEvidenceModel,
)

logger = logging.getLogger(__name__)


class ComplianceRepository:
    """Data access for compliance domain entities."""

    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    # ── Frameworks ─────────────────────────────────────────────────

    async def list_frameworks(self, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        stmt = select(ComplianceFrameworkModel).where(
            ComplianceFrameworkModel.tenant_id == self.tenant_id
        ).order_by(ComplianceFrameworkModel.name.asc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = [self._framework_to_dict(f) for f in result.scalars().all()]

        count_stmt = select(func.count()).select_from(ComplianceFrameworkModel).where(
            ComplianceFrameworkModel.tenant_id == self.tenant_id
        )
        total = (await self.session.execute(count_stmt)).scalar() or 0
        return items, total

    async def create_framework(self, data: dict) -> dict:
        framework = ComplianceFrameworkModel(
            framework_id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            **data,
        )
        self.session.add(framework)
        await self.session.flush()
        return self._framework_to_dict(framework)

    def _framework_to_dict(self, f: ComplianceFrameworkModel) -> dict:
        return {
            "framework_id": str(f.framework_id),
            "tenant_id": str(f.tenant_id),
            "name": f.name,
            "version": f.version,
            "description": f.description,
            "category": f.category,
            "is_active": f.is_active,
            "control_count": f.control_count,
            "extra_metadata": f.extra_metadata or {},
            "created_by": f.created_by,
            "created_at": f.created_at,
            "updated_at": f.updated_at,
        }

    # ── Controls ───────────────────────────────────────────────────

    async def list_controls(self, framework_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        stmt = select(ComplianceControlModel).where(
            ComplianceControlModel.tenant_id == self.tenant_id
        )
        if framework_id:
            stmt = stmt.where(ComplianceControlModel.framework_id == framework_id)
        stmt = stmt.order_by(ComplianceControlModel.sort_order.asc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = [self._control_to_dict(c) for c in result.scalars().all()]

        count_stmt = select(func.count()).select_from(ComplianceControlModel).where(
            ComplianceControlModel.tenant_id == self.tenant_id
        )
        if framework_id:
            count_stmt = count_stmt.where(ComplianceControlModel.framework_id == framework_id)
        total = (await self.session.execute(count_stmt)).scalar() or 0
        return items, total

    async def create_control(self, data: dict) -> dict:
        control = ComplianceControlModel(
            control_id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            **data,
        )
        self.session.add(control)
        await self.session.flush()

        # Update framework control count
        fw_id = data.get("framework_id")
        if fw_id:
            count_stmt = select(func.count()).select_from(ComplianceControlModel).where(
                ComplianceControlModel.framework_id == fw_id,
                ComplianceControlModel.tenant_id == self.tenant_id,
            )
            count = (await self.session.execute(count_stmt)).scalar() or 0
            await self.session.execute(
                update(ComplianceFrameworkModel).where(
                    ComplianceFrameworkModel.framework_id == fw_id,
                    ComplianceFrameworkModel.tenant_id == self.tenant_id,
                ).values(control_count=count)
            )

        return self._control_to_dict(control)

    def _control_to_dict(self, c: ComplianceControlModel) -> dict:
        return {
            "control_id": str(c.control_id),
            "framework_id": str(c.framework_id),
            "tenant_id": str(c.tenant_id),
            "control_id_str": c.control_id_str,
            "name": c.name,
            "description": c.description,
            "category": c.category,
            "risk_level": c.risk_level,
            "is_active": c.is_active,
            "sort_order": c.sort_order,
            "extra_metadata": c.extra_metadata or {},
            "created_by": c.created_by,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }

    # ── Assessments ────────────────────────────────────────────────

    async def list_assessments(self, framework_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        stmt = select(ComplianceAssessmentModel).where(
            ComplianceAssessmentModel.tenant_id == self.tenant_id
        )
        if framework_id:
            stmt = stmt.where(ComplianceAssessmentModel.framework_id == framework_id)
        stmt = stmt.order_by(ComplianceAssessmentModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = [self._assessment_to_dict(a) for a in result.scalars().all()]

        count_stmt = select(func.count()).select_from(ComplianceAssessmentModel).where(
            ComplianceAssessmentModel.tenant_id == self.tenant_id
        )
        if framework_id:
            count_stmt = count_stmt.where(ComplianceAssessmentModel.framework_id == framework_id)
        total = (await self.session.execute(count_stmt)).scalar() or 0
        return items, total

    async def create_assessment(self, data: dict) -> dict:
        assessment = ComplianceAssessmentModel(
            assessment_id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            **data,
        )
        self.session.add(assessment)
        await self.session.flush()
        return self._assessment_to_dict(assessment)

    def _assessment_to_dict(self, a: ComplianceAssessmentModel) -> dict:
        return {
            "assessment_id": str(a.assessment_id),
            "framework_id": str(a.framework_id),
            "tenant_id": str(a.tenant_id),
            "name": a.name,
            "description": a.description,
            "status": a.status,
            "score": a.score,
            "total_controls": a.total_controls,
            "passed_controls": a.passed_controls,
            "failed_controls": a.failed_controls,
            "compliance_percentage": a.compliance_percentage,
            "started_at": a.started_at,
            "completed_at": a.completed_at,
            "extra_metadata": a.extra_metadata or {},
            "created_by": a.created_by,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
        }

    # ── Findings ───────────────────────────────────────────────────

    async def list_findings(self, assessment_id: Optional[str] = None, status: Optional[str] = None,
                            severity: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        stmt = select(ComplianceFindingModel).where(
            ComplianceFindingModel.tenant_id == self.tenant_id
        )
        if assessment_id:
            stmt = stmt.where(ComplianceFindingModel.assessment_id == assessment_id)
        if status:
            stmt = stmt.where(ComplianceFindingModel.status == status)
        if severity:
            stmt = stmt.where(ComplianceFindingModel.severity == severity)
        stmt = stmt.order_by(ComplianceFindingModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = [self._finding_to_dict(f) for f in result.scalars().all()]

        count_stmt = select(func.count()).select_from(ComplianceFindingModel).where(
            ComplianceFindingModel.tenant_id == self.tenant_id
        )
        if assessment_id:
            count_stmt = count_stmt.where(ComplianceFindingModel.assessment_id == assessment_id)
        if status:
            count_stmt = count_stmt.where(ComplianceFindingModel.status == status)
        if severity:
            count_stmt = count_stmt.where(ComplianceFindingModel.severity == severity)
        total = (await self.session.execute(count_stmt)).scalar() or 0
        return items, total

    async def create_finding(self, data: dict) -> dict:
        finding = ComplianceFindingModel(
            finding_id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            **data,
        )
        self.session.add(finding)
        await self.session.flush()
        return self._finding_to_dict(finding)

    def _finding_to_dict(self, f: ComplianceFindingModel) -> dict:
        return {
            "finding_id": str(f.finding_id),
            "assessment_id": str(f.assessment_id),
            "control_id": str(f.control_id) if f.control_id else None,
            "tenant_id": str(f.tenant_id),
            "title": f.title,
            "description": f.description,
            "severity": f.severity,
            "status": f.status,
            "risk_score": f.risk_score,
            "due_date": f.due_date,
            "assigned_to": f.assigned_to,
            "remediation_notes": f.remediation_notes,
            "extra_metadata": f.extra_metadata or {},
            "created_by": f.created_by,
            "created_at": f.created_at,
            "updated_at": f.updated_at,
        }

    # ── Exceptions ─────────────────────────────────────────────────

    async def list_exceptions(self, status: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        stmt = select(ComplianceExceptionModel).where(
            ComplianceExceptionModel.tenant_id == self.tenant_id
        )
        if status:
            stmt = stmt.where(ComplianceExceptionModel.status == status)
        stmt = stmt.order_by(ComplianceExceptionModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = [self._exception_to_dict(e) for e in result.scalars().all()]

        count_stmt = select(func.count()).select_from(ComplianceExceptionModel).where(
            ComplianceExceptionModel.tenant_id == self.tenant_id
        )
        if status:
            count_stmt = count_stmt.where(ComplianceExceptionModel.status == status)
        total = (await self.session.execute(count_stmt)).scalar() or 0
        return items, total

    async def create_exception(self, data: dict) -> dict:
        exception = ComplianceExceptionModel(
            exception_id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            **data,
        )
        self.session.add(exception)
        await self.session.flush()
        return self._exception_to_dict(exception)

    def _exception_to_dict(self, e: ComplianceExceptionModel) -> dict:
        return {
            "exception_id": str(e.exception_id),
            "control_id": str(e.control_id),
            "tenant_id": str(e.tenant_id),
            "title": e.title,
            "justification": e.justification,
            "risk_assessment": e.risk_assessment,
            "status": e.status,
            "approved_by": e.approved_by,
            "approved_at": e.approved_at,
            "expires_at": e.expires_at,
            "extra_metadata": e.extra_metadata or {},
            "created_by": e.created_by,
            "created_at": e.created_at,
            "updated_at": e.updated_at,
        }

    # ── Evidence ───────────────────────────────────────────────────

    async def list_evidence(self, framework: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        stmt = select(ComplianceEvidenceModel).where(
            ComplianceEvidenceModel.tenant_id == self.tenant_id
        )
        if framework:
            stmt = stmt.where(ComplianceEvidenceModel.framework == framework)
        stmt = stmt.order_by(ComplianceEvidenceModel.collected_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = [self._evidence_to_dict(e) for e in result.scalars().all()]

        count_stmt = select(func.count()).select_from(ComplianceEvidenceModel).where(
            ComplianceEvidenceModel.tenant_id == self.tenant_id
        )
        if framework:
            count_stmt = count_stmt.where(ComplianceEvidenceModel.framework == framework)
        total = (await self.session.execute(count_stmt)).scalar() or 0
        return items, total

    async def create_evidence(self, data: dict) -> dict:
        evidence = ComplianceEvidenceModel(
            tenant_id=self.tenant_id,
            **data,
        )
        self.session.add(evidence)
        await self.session.flush()
        return self._evidence_to_dict(evidence)

    def _evidence_to_dict(self, e: ComplianceEvidenceModel) -> dict:
        return {
            "evidence_id": e.evidence_id,
            "tenant_id": str(e.tenant_id),
            "evidence_type": e.evidence_type,
            "framework": e.framework,
            "control_id": e.control_id,
            "description": e.description,
            "status": e.status,
            "data": e.data or {},
            "checksum": e.checksum,
            "collected_at": e.collected_at,
            "expires_at": e.expires_at,
            "validated_by": e.validated_by,
            "validated_at": e.validated_at,
            "storage_path": e.storage_path,
            "created_at": e.created_at,
            "updated_at": e.updated_at,
        }

    # ── Scan / Evaluation Engine ──────────────────────────────────

    async def run_scan(self, created_by: str = "system") -> dict:
        """Run a compliance scan across all active frameworks.

        For each framework, creates or updates an assessment, evaluates
        control coverage, generates findings for gaps, and returns a
        summary of what happened.

        Idempotent: will NOT create duplicate findings. Only one open
        finding per control is allowed at any time. If a finding already
        exists for a control, it is updated in place.
        """
        now = datetime.now(timezone.utc)

        # 1. Fetch all active frameworks with their controls
        frameworks, fw_total = await self.list_frameworks(page_size=100)
        total_controls = 0
        new_findings = 0
        updated_findings = 0
        framework_results = []

        for fw in frameworks:
            fw_id = fw["framework_id"]
            controls, ctrl_total = await self.list_controls(framework_id=fw_id, page_size=200)
            total_controls += ctrl_total

            # 2. Reuse existing assessment for this framework — never create duplicates
            existing_assessments, _ = await self.list_assessments(framework_id=fw_id, page_size=1)
            if existing_assessments:
                assessment = existing_assessments[0]
                assessment_id = assessment["assessment_id"]
                # Reset to in_progress for this scan
                stmt_reset = (
                    update(ComplianceAssessmentModel)
                    .where(ComplianceAssessmentModel.assessment_id == assessment_id)
                    .values(status="in_progress", started_at=now, completed_at=None)
                )
                await self.session.execute(stmt_reset)
            else:
                assessment = await self.create_assessment({
                    "framework_id": fw_id,
                    "name": f"Automated Scan — {fw['name']} ({now.strftime('%Y-%m-%d %H:%M')})",
                    "description": f"Automated compliance scan for {fw['name']} v{fw['version']}",
                    "status": "in_progress",
                    "created_by": created_by,
                })
                assessment_id = assessment["assessment_id"]

            # 3. Evaluate each control — check if there's evidence
            passed = 0
            failed = 0
            for ctrl in controls:
                ctrl_id = ctrl["control_id"]
                ctrl_id_str = ctrl["control_id_str"]

                # Check if there's validated evidence for this control
                evidence_list, _ = await self.list_evidence(framework=fw["name"], page_size=200)
                has_validated_evidence = any(
                    ev["control_id"] == ctrl_id_str and ev["status"] == "validated"
                    for ev in evidence_list
                )

                # Check for existing open finding for this control across ALL assessments
                # Uses raw query to find any open/in_progress finding by control_id
                stmt_existing = (
                    select(ComplianceFindingModel)
                    .where(
                        ComplianceFindingModel.control_id == ctrl_id,
                        ComplianceFindingModel.tenant_id == self.tenant_id,
                        ComplianceFindingModel.status.in_(["open", "in_progress"]),
                    )
                    .limit(1)
                )
                result = await self.session.execute(stmt_existing)
                existing_finding = result.scalar_one_or_none()

                if has_validated_evidence:
                    passed += 1
                    # Close any open finding for this control
                    if existing_finding:
                        stmt = (
                            update(ComplianceFindingModel)
                            .where(ComplianceFindingModel.finding_id == existing_finding.finding_id)
                            .values(
                                status="remediated",
                                assessment_id=assessment_id,
                                extra_metadata={
                                    **(existing_finding.extra_metadata or {}),
                                    "resolved_by_scan": True,
                                    "resolved_at": now.isoformat(),
                                },
                            )
                        )
                        await self.session.execute(stmt)
                        updated_findings += 1
                else:
                    failed += 1
                    if existing_finding:
                        # Update existing finding — refresh its assessment link and timestamp
                        stmt = (
                            update(ComplianceFindingModel)
                            .where(ComplianceFindingModel.finding_id == existing_finding.finding_id)
                            .values(
                                assessment_id=assessment_id,
                                extra_metadata={
                                    **(existing_finding.extra_metadata or {}),
                                    "last_scanned_at": now.isoformat(),
                                    "scan_count": (existing_finding.extra_metadata or {}).get("scan_count", 0) + 1,
                                },
                            )
                        )
                        await self.session.execute(stmt)
                        updated_findings += 1
                    else:
                        # Create new finding for uncovered control
                        await self.create_finding({
                            "assessment_id": assessment_id,
                            "control_id": ctrl_id,
                            "title": f"Control {ctrl_id_str} — {ctrl['name']} lacks validated evidence",
                            "description": f"Control '{ctrl['name']}' ({ctrl_id_str}) has no validated evidence. Risk level: {ctrl['risk_level']}. Category: {ctrl['category']}.",
                            "severity": "high" if ctrl["risk_level"] in ("critical", "high") else "medium",
                            "status": "open",
                            "risk_score": 7.5 if ctrl["risk_level"] == "critical" else 5.0 if ctrl["risk_level"] == "high" else 3.0,
                            "assigned_to": None,
                            "created_by": created_by,
                        })
                        new_findings += 1

            # 4. Update assessment with results
            total = passed + failed
            score = round((passed / total) * 100, 1) if total > 0 else 0
            stmt = (
                update(ComplianceAssessmentModel)
                .where(ComplianceAssessmentModel.assessment_id == assessment_id)
                .values(
                    status="completed",
                    score=score,
                    total_controls=total,
                    passed_controls=passed,
                    failed_controls=failed,
                    compliance_percentage=score,
                    completed_at=now,
                )
            )
            await self.session.execute(stmt)

            framework_results.append({
                "framework_id": fw_id,
                "framework_name": fw["name"],
                "controls_total": total,
                "controls_passed": passed,
                "controls_failed": failed,
                "score": score,
            })

        await self.session.commit()

        # Compute overall compliance score
        scores = [r["score"] for r in framework_results if r["controls_total"] > 0]
        overall_score = round(sum(scores) / len(scores), 1) if scores else 0

        return {
            "frameworks_scanned": len(framework_results),
            "controls_evaluated": total_controls,
            "new_findings": new_findings,
            "updated_findings": updated_findings,
            "compliance_score": overall_score,
            "frameworks": framework_results,
        }
