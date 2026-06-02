"""Enterprise Marketplace Economy — workflow packs, governance packs, industry packs, benchmark subscriptions, simulation packs, strategy packs, partner extensions.

Ecosystem gravity through a thriving marketplace economy.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PackCategory(str, Enum):
    WORKFLOW = "workflow"
    GOVERNANCE = "governance"
    INDUSTRY = "industry"
    BENCHMARK = "benchmark"
    SIMULATION = "simulation"
    STRATEGY = "strategy"
    EXTENSION = "extension"


class PackPricing(str, Enum):
    FREE = "free"
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    ENTERPRISE = "enterprise"


@dataclass
class MarketplacePack:
    """A pack available in the enterprise marketplace."""
    pack_id: str
    name: str
    description: str
    category: PackCategory
    publisher: str
    version: str = "1.0.0"
    pricing: PackPricing = PackPricing.FREE
    price: float = 0.0
    install_count: int = 0
    rating: float = 0.0
    is_verified: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class MarketplaceSubscription:
    """A subscription to a marketplace pack."""
    subscription_id: str
    tenant_id: str
    pack_id: str
    status: str = "active"  # active, expired, cancelled
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: str = ""
    auto_renew: bool = True


@dataclass
class EcosystemMarketplaceService:
    """Enterprise marketplace economy — ecosystem gravity through marketplace.

    Supports:
    - Workflow packs (pre-built workflow definitions)
    - Governance packs (governance policy bundles)
    - Industry packs (vertical-specific intelligence)
    - Benchmark subscriptions (premium benchmark access)
    - Simulation packs (advanced simulation scenarios)
    - Strategy packs (strategic planning templates)
    - Partner extensions (third-party integrations)
    """

    _packs: dict[str, MarketplacePack] = field(default_factory=dict)
    _subscriptions: dict[str, MarketplaceSubscription] = field(default_factory=dict)

    def __post_init__(self):
        self._seed_default_packs()

    def _seed_default_packs(self) -> None:
        """Seed default marketplace packs."""
        packs = [
            MarketplacePack(pack_id="wf_procurement_standard", name="Standard Procurement Review", description="Complete procurement review workflow with AI analysis and legal approval", category=PackCategory.WORKFLOW, publisher="ContractRiskEdge", pricing=PackPricing.FREE, is_verified=True),
            MarketplacePack(pack_id="wf_high_risk_legal", name="High-Risk Legal Review", description="Elevated legal review with security and compliance stages", category=PackCategory.WORKFLOW, publisher="ContractRiskEdge", pricing=PackPricing.FREE, is_verified=True),
            MarketplacePack(pack_id="gov_soc2", name="SOC2 Governance Pack", description="Complete SOC2 governance controls and evidence collection", category=PackCategory.GOVERNANCE, publisher="ContractRiskEdge", pricing=PackPricing.SUBSCRIPTION, price=999.0, is_verified=True),
            MarketplacePack(pack_id="gov_gdpr", name="GDPR Compliance Pack", description="GDPR compliance automation and evidence collection", category=PackCategory.GOVERNANCE, publisher="ContractRiskEdge", pricing=PackPricing.SUBSCRIPTION, price=799.0, is_verified=True),
            MarketplacePack(pack_id="ind_healthcare", name="Healthcare Intelligence Pack", description="HIPAA compliance, healthcare benchmarks, and regulatory tracking", category=PackCategory.INDUSTRY, publisher="ContractRiskEdge", pricing=PackPricing.SUBSCRIPTION, price=1499.0, is_verified=True),
            MarketplacePack(pack_id="ind_finance", name="Financial Services Pack", description="SOX/SEC compliance, finance benchmarks, and regulatory tracking", category=PackCategory.INDUSTRY, publisher="ContractRiskEdge", pricing=PackPricing.SUBSCRIPTION, price=1499.0, is_verified=True),
            MarketplacePack(pack_id="bm_premium", name="Premium Benchmark Access", description="Advanced industry benchmarks with trend analysis and forecasting", category=PackCategory.BENCHMARK, publisher="ContractRiskEdge", pricing=PackPricing.SUBSCRIPTION, price=499.0, is_verified=True),
            MarketplacePack(pack_id="sim_advanced", name="Advanced Simulation Pack", description="Merger impact, portfolio, and regulatory scenario simulations", category=PackCategory.SIMULATION, publisher="ContractRiskEdge", pricing=PackPricing.SUBSCRIPTION, price=799.0, is_verified=True),
            MarketplacePack(pack_id="strat_executive", name="Executive Strategy Pack", description="Enterprise strategy roadmaps, portfolio optimization, and risk reduction plans", category=PackCategory.STRATEGY, publisher="ContractRiskEdge", pricing=PackPricing.ENTERPRISE, is_verified=True),
            MarketplacePack(pack_id="ext_docusign", name="DocuSign Integration", description="Send contracts for e-signature directly from ContractEdge", category=PackCategory.EXTENSION, publisher="ContractRiskEdge", pricing=PackPricing.FREE, is_verified=True),
            MarketplacePack(pack_id="ext_salesforce", name="Salesforce Sync", description="Sync contract status and obligations with Salesforce", category=PackCategory.EXTENSION, publisher="ContractRiskEdge", pricing=PackPricing.ONE_TIME, price=2999.0, is_verified=True),
        ]
        for pack in packs:
            self._packs[pack.pack_id] = pack

    def list_packs(self, category: PackCategory | None = None) -> list[dict[str, Any]]:
        """List marketplace packs."""
        packs = self._packs.values()
        if category:
            packs = [p for p in packs if p.category == category]
        return [
            {"id": p.pack_id, "name": p.name, "description": p.description, "category": p.category.value,
             "publisher": p.publisher, "pricing": p.pricing.value, "price": p.price,
             "rating": p.rating, "verified": p.is_verified, "installs": p.install_count}
            for p in packs
        ]

    def get_pack(self, pack_id: str) -> MarketplacePack | None:
        """Get a marketplace pack."""
        return self._packs.get(pack_id)

    def subscribe(self, tenant_id: str, pack_id: str) -> MarketplaceSubscription:
        """Subscribe to a marketplace pack."""
        pack = self._packs.get(pack_id)
        if not pack:
            raise ValueError(f"Pack '{pack_id}' not found")

        sub = MarketplaceSubscription(
            subscription_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            pack_id=pack_id,
            expires_at=(datetime.utcnow().replace(year=datetime.utcnow().year + 1)).isoformat() if pack.pricing == PackPricing.SUBSCRIPTION else "",
        )
        self._subscriptions[sub.subscription_id] = sub
        pack.install_count += 1
        return sub

    def get_tenant_subscriptions(self, tenant_id: str) -> list[MarketplaceSubscription]:
        """Get all subscriptions for a tenant."""
        return [s for s in self._subscriptions.values() if s.tenant_id == tenant_id]

    def get_marketplace_summary(self) -> dict[str, Any]:
        """Get marketplace summary."""
        return {
            "total_packs": len(self._packs),
            "by_category": {c.value: sum(1 for p in self._packs.values() if p.category == c) for c in PackCategory},
            "total_subscriptions": len(self._subscriptions),
            "verified_packs": sum(1 for p in self._packs.values() if p.is_verified),
            "free_packs": sum(1 for p in self._packs.values() if p.pricing == PackPricing.FREE),
            "premium_packs": sum(1 for p in self._packs.values() if p.pricing in (PackPricing.SUBSCRIPTION, PackPricing.ONE_TIME, PackPricing.ENTERPRISE)),
        }


# ── Global singleton ───────────────────────────────────────────────

ecosystem_marketplace = EcosystemMarketplaceService()
