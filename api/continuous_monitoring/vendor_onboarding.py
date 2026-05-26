"""Vendor onboarding workflow (V2-035).

Provides an approval-stage vendor onboarding workflow with AI risk
gate reviews and risk scoring at each stage.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OnboardingStage(str, Enum):
    """Stages in the vendor onboarding workflow."""

    INITIATED = "initiated"
    DUE_DILIGENCE = "due_diligence"
    AI_RISK_REVIEW = "ai_risk_review"
    LEGAL_REVIEW = "legal_review"
    PROCUREMENT_APPROVAL = "procurement_approval"
    FINANCE_APPROVAL = "finance_approval"
    FINAL_APPROVAL = "final_approval"
    ONBOARDED = "onboarded"
    REJECTED = "rejected"
    ON_HOLD = "on_hold"


@dataclass
class VendorOnboarding:
    """A vendor onboarding request."""

    onboarding_id: str
    tenant_id: str
    vendor_name: str
    vendor_email: str
    vendor_type: str  # supplier, contractor, partner, consultant
    contract_value: float = 0.0
    currency: str = "USD"
    current_stage: OnboardingStage = OnboardingStage.INITIATED
    status: str = "active"  # active, completed, rejected, on_hold
    stage_history: List[Dict[str, Any]] = field(default_factory=list)
    ai_risk_score: Optional[float] = None
    ai_risk_level: Optional[str] = None
    ai_review_notes: str = ""
    legal_approval: Optional[bool] = None
    procurement_approval: Optional[bool] = None
    finance_approval: Optional[bool] = None
    final_approval: Optional[bool] = None
    created_by: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    days_in_stage: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "onboarding_id": self.onboarding_id,
            "tenant_id": self.tenant_id,
            "vendor_name": self.vendor_name,
            "vendor_email": self.vendor_email,
            "vendor_type": self.vendor_type,
            "contract_value": self.contract_value,
            "currency": self.currency,
            "current_stage": self.current_stage.value if isinstance(self.current_stage, OnboardingStage) else self.current_stage,
            "status": self.status,
            "stage_history": self.stage_history,
            "ai_risk_score": round(self.ai_risk_score, 2) if self.ai_risk_score is not None else None,
            "ai_risk_level": self.ai_risk_level,
            "ai_review_notes": self.ai_review_notes,
            "legal_approval": self.legal_approval,
            "procurement_approval": self.procurement_approval,
            "finance_approval": self.finance_approval,
            "final_approval": self.final_approval,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "days_in_stage": self.days_in_stage,
            "progress_percent": self._compute_progress(),
        }

    def _compute_progress(self) -> int:
        """Compute onboarding progress percentage.

        Returns:
            Progress 0-100.
        """
        stages = list(OnboardingStage)
        if self.current_stage in stages:
            current_idx = stages.index(self.current_stage)
            # Exclude terminal states from progress calculation
            terminal_stages = {OnboardingStage.ONBOARDED, OnboardingStage.REJECTED}
            if self.current_stage in terminal_stages:
                return 100
            return min(95, int((current_idx / (len(stages) - 3)) * 100))
        return 0


class VendorOnboardingWorkflow:
    """Vendor onboarding workflow with AI risk gate.

    Manages the multi-stage vendor onboarding process with AI-powered
    risk assessment at the due diligence stage.

    Usage:
        workflow = VendorOnboardingWorkflow()
        onboarding = await workflow.initiate_onboarding(data)
        result = await workflow.run_ai_risk_gate(onboarding_id)
    """

    def __init__(self, db_pool: Optional[Any] = None) -> None:
        """Initialize the vendor onboarding workflow.

        Args:
            db_pool: Optional database pool.
        """
        self._db_pool = db_pool
        self._onboardings: Dict[str, VendorOnboarding] = {}

    async def initiate_onboarding(
        self,
        tenant_id: str,
        vendor_name: str,
        vendor_email: str,
        vendor_type: str = "supplier",
        contract_value: float = 0.0,
        currency: str = "USD",
        created_by: Optional[str] = None,
    ) -> VendorOnboarding:
        """Initiate a new vendor onboarding request.

        Args:
            tenant_id: The tenant identifier.
            vendor_name: Vendor name.
            vendor_email: Vendor email.
            vendor_type: Vendor type.
            contract_value: Expected contract value.
            currency: Currency.
            created_by: User who initiated.

        Returns:
            The created VendorOnboarding.
        """
        onboarding = VendorOnboarding(
            onboarding_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            vendor_name=vendor_name,
            vendor_email=vendor_email,
            vendor_type=vendor_type,
            contract_value=contract_value,
            currency=currency,
            current_stage=OnboardingStage.INITIATED,
            stage_history=[{
                "stage": OnboardingStage.INITIATED.value,
                "entered_at": datetime.utcnow().isoformat(),
                "action": "initiated",
                "performed_by": created_by or "system",
            }],
            created_by=created_by,
        )

        self._onboardings[onboarding.onboarding_id] = onboarding
        logger.info("Initiated vendor onboarding for %s (%s)", vendor_name, vendor_email)
        return onboarding

    async def advance_stage(
        self,
        onboarding_id: str,
        approved: bool = True,
        performed_by: Optional[str] = None,
        notes: str = "",
    ) -> Optional[VendorOnboarding]:
        """Advance the onboarding to the next stage.

        Args:
            onboarding_id: The onboarding identifier.
            approved: Whether the current stage is approved.
            performed_by: User who performed the action.
            notes: Review notes.

        Returns:
            Updated VendorOnboarding or None.
        """
        onboarding = self._onboardings.get(onboarding_id)
        if not onboarding:
            return None

        stages = list(OnboardingStage)
        current_idx = stages.index(onboarding.current_stage)

        if not approved:
            if current_idx >= stages.index(OnboardingStage.LEGAL_REVIEW):
                onboarding.status = "rejected"
                onboarding.current_stage = OnboardingStage.REJECTED
                onboarding.completed_at = datetime.utcnow().isoformat()
            else:
                onboarding.current_stage = OnboardingStage.ON_HOLD
                onboarding.status = "on_hold"
        elif current_idx < len(stages) - 1:
            next_stage = stages[current_idx + 1]
            onboarding.current_stage = next_stage
            onboarding.stage_history.append({
                "stage": next_stage.value,
                "entered_at": datetime.utcnow().isoformat(),
                "action": "approved" if approved else "rejected",
                "performed_by": performed_by or "system",
                "notes": notes,
            })

            # Record approvals at specific stages
            if next_stage == OnboardingStage.LEGAL_REVIEW:
                onboarding.legal_approval = approved
            elif next_stage == OnboardingStage.PROCUREMENT_APPROVAL:
                onboarding.procurement_approval = approved
            elif next_stage == OnboardingStage.FINANCE_APPROVAL:
                onboarding.finance_approval = approved
            elif next_stage == OnboardingStage.FINAL_APPROVAL:
                onboarding.final_approval = approved

            if next_stage == OnboardingStage.ONBOARDED:
                onboarding.status = "completed"
                onboarding.completed_at = datetime.utcnow().isoformat()

        onboarding.days_in_stage = 0
        logger.info("Vendor %s advanced to stage %s (approved=%s)",
                     onboarding.vendor_name,
                     onboarding.current_stage.value if isinstance(onboarding.current_stage, OnboardingStage) else onboarding.current_stage,
                     approved)
        return onboarding

    async def run_ai_risk_gate(
        self,
        onboarding_id: str,
        vendor_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run the AI risk gate review for a vendor.

        Analyzes vendor data and assigns a risk score.

        Args:
            onboarding_id: The onboarding identifier.
            vendor_data: Optional additional vendor data.

        Returns:
            Dict with AI risk assessment results.
        """
        onboarding = self._onboardings.get(onboarding_id)
        if not onboarding:
            return None

        data = vendor_data or {}

        # Compute AI risk score based on available data
        risk_score = self._compute_vendor_risk_score(onboarding, data)

        onboarding.ai_risk_score = risk_score
        onboarding.ai_risk_level = self._risk_level_from_score(risk_score)
        onboarding.ai_review_notes = self._generate_review_notes(
            risk_score, onboarding, data
        )

        # Auto-advance or flag for review based on risk level
        if risk_score < 4.0:
            await self.advance_stage(
                onboarding_id, approved=True,
                performed_by="ai_risk_gate",
                notes=f"AI risk gate passed (score: {risk_score:.1f}). Low risk vendor."
            )
        elif risk_score < 7.0:
            await self.advance_stage(
                onboarding_id, approved=True,
                performed_by="ai_risk_gate",
                notes=f"AI risk gate passed with caution (score: {risk_score:.1f}). Medium risk - recommended for enhanced due diligence."
            )
        else:
            # High risk - flag for manual review
            onboarding.current_stage = OnboardingStage.ON_HOLD
            onboarding.status = "on_hold"
            onboarding.stage_history.append({
                "stage": OnboardingStage.ON_HOLD.value,
                "entered_at": datetime.utcnow().isoformat(),
                "action": "flagged",
                "performed_by": "ai_risk_gate",
                "notes": f"AI risk gate flagged (score: {risk_score:.1f}). High risk vendor - requires manual review.",
            })

        logger.info(
            "AI risk gate for vendor %s: score=%.2f, level=%s",
            onboarding.vendor_name, risk_score, onboarding.ai_risk_level,
        )

        return {
            "onboarding_id": onboarding_id,
            "vendor_name": onboarding.vendor_name,
            "risk_score": risk_score,
            "risk_level": onboarding.ai_risk_level,
            "review_notes": onboarding.ai_review_notes,
            "auto_approved": risk_score < 7.0,
        }

    def _compute_vendor_risk_score(
        self,
        onboarding: VendorOnboarding,
        data: Dict[str, Any],
    ) -> float:
        """Compute vendor risk score based on available data.

        Args:
            onboarding: The vendor onboarding.
            data: Additional vendor data.

        Returns:
            Risk score 0-10.
        """
        score = 3.0  # Base score

        # Contract value risk
        if onboarding.contract_value > 1_000_000:
            score += 2.0
        elif onboarding.contract_value > 500_000:
            score += 1.0
        elif onboarding.contract_value > 100_000:
            score += 0.5

        # Vendor type risk
        high_risk_types = ["contractor", "consultant"]
        if onboarding.vendor_type in high_risk_types:
            score += 1.0

        # Jurisdiction risk (if provided)
        jurisdiction = data.get("jurisdiction", "").lower()
        high_risk_jurisdictions = ["china", "russia", "iran", "north korea", "syria"]
        if any(j in jurisdiction for j in high_risk_jurisdictions):
            score += 2.0

        # Industry risk
        industry = data.get("industry", "").lower()
        high_risk_industries = ["defense", "gambling", "cryptocurrency", "adult"]
        if any(ind in industry for ind in high_risk_industries):
            score += 1.5

        # Sanctions check (simulated)
        sanctions_flag = data.get("sanctions_flag", False)
        if sanctions_flag:
            score += 3.0

        return min(10.0, max(0.0, score))

    def _risk_level_from_score(self, score: float) -> str:
        """Convert risk score to level.

        Args:
            score: Risk score.

        Returns:
            Risk level string.
        """
        if score >= 7.0:
            return "high"
        elif score >= 4.0:
            return "medium"
        else:
            return "low"

    def _generate_review_notes(
        self,
        score: float,
        onboarding: VendorOnboarding,
        data: Dict[str, Any],
    ) -> str:
        """Generate AI review notes.

        Args:
            score: Risk score.
            onboarding: Vendor onboarding.
            data: Additional vendor data.

        Returns:
            Review notes string.
        """
        notes = []

        if score < 4.0:
            notes.append("Vendor passes AI risk gate with low risk score.")
        elif score < 7.0:
            notes.append("Vendor passes AI risk gate with moderate risk.")
        else:
            notes.append("VENDOR FLAGGED: High risk score requires manual review.")

        if onboarding.contract_value > 500_000:
            notes.append(f"High contract value (${onboarding.contract_value:,.2f}) - recommend enhanced financial due diligence.")

        jurisdiction = data.get("jurisdiction")
        if jurisdiction:
            notes.append(f"Jurisdiction: {jurisdiction}.")

        return " ".join(notes)

    async def get_onboarding(self, onboarding_id: str) -> Optional[Dict[str, Any]]:
        """Get onboarding details.

        Args:
            onboarding_id: The onboarding identifier.

        Returns:
            Onboarding dict or None.
        """
        onboarding = self._onboardings.get(onboarding_id)
        return onboarding.to_dict() if onboarding else None

    async def get_pipeline_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Get onboarding pipeline summary.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with pipeline summary.
        """
        tenant_onboardings = [
            o for o in self._onboardings.values()
            if o.tenant_id == tenant_id
        ]

        by_stage: Dict[str, int] = {}
        total_value = 0.0
        high_risk_count = 0

        for o in tenant_onboardings:
            stage = o.current_stage.value if isinstance(o.current_stage, OnboardingStage) else o.current_stage
            by_stage[stage] = by_stage.get(stage, 0) + 1
            total_value += o.contract_value
            if o.ai_risk_level == "high":
                high_risk_count += 1

        return {
            "tenant_id": tenant_id,
            "total_onboardings": len(tenant_onboardings),
            "active_onboardings": sum(1 for o in tenant_onboardings if o.status == "active"),
            "completed_onboardings": sum(1 for o in tenant_onboardings if o.status == "completed"),
            "rejected_onboardings": sum(1 for o in tenant_onboardings if o.status == "rejected"),
            "by_stage": by_stage,
            "total_contract_value": total_value,
            "high_risk_vendors": high_risk_count,
            "average_risk_score": round(
                sum(o.ai_risk_score or 0 for o in tenant_onboardings if o.ai_risk_score is not None) /
                max(sum(1 for o in tenant_onboardings if o.ai_risk_score is not None), 1), 2
            ),
        }
