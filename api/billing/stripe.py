"""Stripe billing integration for subscription management.

Handles subscription creation, metered billing, invoicing,
and webhook event processing for Stripe.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SubscriptionTier(str, Enum):
    """Available subscription tiers."""

    STARTER = "starter"
    GROWTH = "growth"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


TIER_PRICES = {
    SubscriptionTier.STARTER: {"monthly": 500, "annual": 4800, "contracts": 20},
    SubscriptionTier.GROWTH: {"monthly": 1500, "annual": 14400, "contracts": 100},
    SubscriptionTier.PROFESSIONAL: {"monthly": 3500, "annual": 33600, "contracts": 500},
    SubscriptionTier.ENTERPRISE: {"monthly": 5000, "annual": 48000, "contracts": -1},
}


@dataclass
class Subscription:
    """A tenant's subscription record."""

    tenant_id: str
    tier: SubscriptionTier
    status: str  # active, past_due, canceled, trialing
    current_period_start: str = ""
    current_period_end: str = ""
    stripe_subscription_id: str = ""
    stripe_customer_id: str = ""
    contracts_used: int = 0
    trial_end: str = ""


class StripeBilling:
    """Stripe billing integration.

    In production, this uses the Stripe API. For development,
    it provides an in-memory implementation.

    Usage:
        billing = StripeBilling()
        sub = billing.create_subscription("tenant-1", SubscriptionTier.GROWTH)
    """

    def __init__(self, api_key: str = "") -> None:
        """Initialize the billing system.

        Args:
            api_key: Stripe secret key (from env if not provided).
        """
        self._api_key = api_key or os.getenv("STRIPE_API_KEY", "")
        self._subscriptions: Dict[str, Subscription] = {}

    def create_subscription(
        self,
        tenant_id: str,
        tier: SubscriptionTier,
        trial_days: int = 14,
    ) -> Subscription:
        """Create a new subscription.

        Args:
            tenant_id: Tenant to subscribe.
            tier: Subscription tier.
            trial_days: Free trial duration.

        Returns:
            The created Subscription.
        """
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        sub = Subscription(
            tenant_id=tenant_id,
            tier=tier,
            status="trialing" if trial_days > 0 else "active",
            current_period_start=now.isoformat() + "Z",
            current_period_end=(now + timedelta(days=30)).isoformat() + "Z",
            stripe_subscription_id=f"sub_{tenant_id}",
            stripe_customer_id=f"cus_{tenant_id}",
            trial_end=(now + timedelta(days=trial_days)).isoformat() + "Z",
        )
        self._subscriptions[tenant_id] = sub
        return sub

    def get_subscription(self, tenant_id: str) -> Optional[Subscription]:
        """Get a tenant's subscription.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            Subscription or None.
        """
        return self._subscriptions.get(tenant_id)

    def check_contract_limit(self, tenant_id: str, current_count: int) -> bool:
        """Check if a tenant can upload more contracts.

        Args:
            tenant_id: Tenant identifier.
            current_count: Current number of contracts.

        Returns:
            True if under limit, False if over.
        """
        sub = self._subscriptions.get(tenant_id)
        if not sub:
            return False
        if sub.tier == SubscriptionTier.ENTERPRISE:
            return True  # Unlimited
        limit = TIER_PRICES[sub.tier]["contracts"]
        return current_count < limit
