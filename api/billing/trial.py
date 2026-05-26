"""14-day free trial flow with onboarding checklist and upgrade nudges.

Manages trial lifecycle, onboarding progress tracking, and
intelligent upgrade prompts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TrialStatus(str, Enum):
    """Status of a tenant's trial."""

    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"  # Last 3 days
    EXPIRED = "expired"
    CONVERTED = "converted"


class OnboardingStep(str, Enum):
    """Steps in the onboarding checklist."""

    UPLOAD_CONTRACT = "upload_contract"
    REVIEW_RISK_FLAGS = "review_risk_flags"
    ACCEPT_REDLINE = "accept_redline"
    CONFIGURE_PLAYBOOK = "configure_playbook"
    INVITE_TEAMMATE = "invite_teammate"


ONBOARDING_STEPS_ORDER = [
    OnboardingStep.UPLOAD_CONTRACT,
    OnboardingStep.REVIEW_RISK_FLAGS,
    OnboardingStep.ACCEPT_REDLINE,
    OnboardingStep.CONFIGURE_PLAYBOOK,
    OnboardingStep.INVITE_TEAMMATE,
]

ONBOARDING_STEP_LABELS = {
    OnboardingStep.UPLOAD_CONTRACT: "Upload your first contract",
    OnboardingStep.REVIEW_RISK_FLAGS: "Review AI risk flags",
    OnboardingStep.ACCEPT_REDLINE: "Accept your first redline",
    OnboardingStep.CONFIGURE_PLAYBOOK: "Set up your playbook",
    OnboardingStep.INVITE_TEAMMATE: "Invite a teammate",
}


@dataclass
class OnboardingProgress:
    """A tenant's onboarding progress."""

    tenant_id: str
    completed_steps: List[OnboardingStep] = field(default_factory=list)
    started_at: str = ""

    @property
    def total_steps(self) -> int:
        return len(ONBOARDING_STEPS_ORDER)

    @property
    def completed_count(self) -> int:
        return len(self.completed_steps)

    @property
    def progress_percentage(self) -> float:
        return round(self.completed_count / self.total_steps * 100, 1)

    @property
    def next_step(self) -> Optional[OnboardingStep]:
        for step in ONBOARDING_STEPS_ORDER:
            if step not in self.completed_steps:
                return step
        return None

    def is_complete(self) -> bool:
        return self.completed_count >= self.total_steps


@dataclass
class Trial:
    """A tenant's trial record."""

    tenant_id: str
    status: TrialStatus = TrialStatus.ACTIVE
    started_at: str = ""
    expires_at: str = ""
    contracts_uploaded: int = 0
    max_contracts: int = 5
    onboarding: OnboardingProgress = field(default_factory=OnboardingProgress)
    upgrade_nudge_sent_day_7: bool = False
    upgrade_nudge_sent_day_10: bool = False
    upgrade_nudge_sent_day_13: bool = False


class TrialManager:
    """Manages the 14-day free trial lifecycle.

    Handles trial creation, expiry tracking, onboarding progress,
    and upgrade nudges.

    Usage:
        manager = TrialManager()
        trial = manager.start_trial("tenant-1")
        manager.complete_step("tenant-1", OnboardingStep.UPLOAD_CONTRACT)
        nudges = manager.get_pending_nudges("tenant-1")
    """

    def __init__(self) -> None:
        """Initialize the trial manager."""
        self._trials: Dict[str, Trial] = {}

    def start_trial(self, tenant_id: str) -> Trial:
        """Start a 14-day free trial for a tenant.

        Args:
            tenant_id: The tenant to start a trial for.

        Returns:
            The created Trial.
        """
        now = datetime.utcnow()
        trial = Trial(
            tenant_id=tenant_id,
            status=TrialStatus.ACTIVE,
            started_at=now.isoformat() + "Z",
            expires_at=(now + timedelta(days=14)).isoformat() + "Z",
            onboarding=OnboardingProgress(
                tenant_id=tenant_id,
                started_at=now.isoformat() + "Z",
            ),
        )
        self._trials[tenant_id] = trial
        logger.info("Trial started for tenant %s (expires: %s)", tenant_id, trial.expires_at)
        return trial

    def get_trial(self, tenant_id: str) -> Optional[Trial]:
        """Get a tenant's trial.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            Trial or None.
        """
        trial = self._trials.get(tenant_id)
        if trial:
            self._update_status(trial)
        return trial

    def complete_step(self, tenant_id: str, step: OnboardingStep) -> bool:
        """Mark an onboarding step as complete.

        Args:
            tenant_id: Tenant identifier.
            step: The completed step.

        Returns:
            True if step was completed.
        """
        trial = self._trials.get(tenant_id)
        if not trial:
            return False

        if step not in trial.onboarding.completed_steps:
            trial.onboarding.completed_steps.append(step)
            logger.info(
                "Onboarding step '%s' completed for tenant %s (%d/%d)",
                step.value, tenant_id,
                trial.onboarding.completed_count,
                trial.onboarding.total_steps,
            )

        if trial.onboarding.is_complete():
            logger.info("Onboarding complete for tenant %s!", tenant_id)

        return True

    def record_contract_upload(self, tenant_id: str) -> bool:
        """Record a contract upload during trial.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            True if under limit, False if exceeded.
        """
        trial = self._trials.get(tenant_id)
        if not trial:
            return False

        trial.contracts_uploaded += 1
        return trial.contracts_uploaded <= trial.max_contracts

    def get_pending_nudges(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get pending upgrade nudges based on trial state.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            List of nudge payloads to display.
        """
        trial = self._trials.get(tenant_id)
        if not trial:
            return []

        nudges = []
        now = datetime.utcnow()
        expires = datetime.fromisoformat(trial.expires_at.replace("Z", "+00:00"))
        days_remaining = (expires - now).days

        # Day 7 nudge
        if days_remaining <= 7 and not trial.upgrade_nudge_sent_day_7:
            trial.upgrade_nudge_sent_day_7 = True
            nudges.append({
                "type": "banner",
                "message": "You're halfway through your trial — love it so far?",
                "action": {"label": "See Plans", "url": "/settings/billing"},
                "priority": "low",
            })

        # Day 10 nudge
        if days_remaining <= 4 and not trial.upgrade_nudge_sent_day_10:
            trial.upgrade_nudge_sent_day_10 = True
            nudges.append({
                "type": "modal",
                "message": "Unlock unlimited contracts — upgrade to a paid plan",
                "action": {"label": "Upgrade Now", "url": "/settings/billing"},
                "priority": "medium",
            })

        # Day 13 nudge (last day)
        if days_remaining <= 1 and not trial.upgrade_nudge_sent_day_13:
            trial.upgrade_nudge_sent_day_13 = True
            nudges.append({
                "type": "urgent_banner",
                "message": "Your trial ends tomorrow! Upgrade to keep accessing your risk analyses.",
                "action": {"label": "Keep My Data", "url": "/settings/billing"},
                "priority": "high",
            })

        # Contract limit hit nudge
        if trial.contracts_uploaded >= trial.max_contracts:
            nudges.append({
                "type": "blocking_modal",
                "message": f"You've analyzed {trial.max_contracts} contracts — upgrade to continue.",
                "action": {"label": "Upgrade Plan", "url": "/settings/billing"},
                "priority": "critical",
            })

        return nudges

    def convert_to_paid(self, tenant_id: str) -> bool:
        """Convert a trial to a paid subscription.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            True if conversion succeeded.
        """
        trial = self._trials.get(tenant_id)
        if not trial:
            return False

        trial.status = TrialStatus.CONVERTED
        logger.info("Tenant %s converted from trial to paid!", tenant_id)
        return True

    def _update_status(self, trial: Trial) -> None:
        """Update trial status based on current time.

        Args:
            trial: The trial to update.
        """
        if trial.status in (TrialStatus.CONVERTED, TrialStatus.EXPIRED):
            return

        now = datetime.utcnow()
        expires = datetime.fromisoformat(trial.expires_at.replace("Z", "+00:00"))
        days_remaining = (expires - now).days

        if days_remaining < 0:
            trial.status = TrialStatus.EXPIRED
        elif days_remaining <= 3:
            trial.status = TrialStatus.EXPIRING_SOON
        else:
            trial.status = TrialStatus.ACTIVE
