"""API & Marketplace Expansion — public API portal, SDKs, extension marketplace, webhook subscriptions, event explorer, connector marketplace.

Future-proofs ecosystem expansion and platform extensibility.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ApiPlan(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class ApiEndpoint:
    """A public API endpoint definition."""
    path: str
    method: str
    description: str
    version: str = "v1"
    auth_required: bool = True
    rate_limit: str = "100/min"
    plan_access: list[ApiPlan] = field(default_factory=lambda: [ApiPlan.STARTER, ApiPlan.PROFESSIONAL, ApiPlan.ENTERPRISE])


@dataclass
class WebhookSubscription:
    """A webhook subscription for event notifications."""
    subscription_id: str
    tenant_id: str
    url: str
    events: list[str] = field(default_factory=list)
    secret: str = ""
    is_active: bool = True
    retry_count: int = 3
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class MarketplaceListing:
    """A listing in the extension marketplace."""
    listing_id: str
    name: str
    description: str
    publisher: str
    version: str = "1.0.0"
    category: str = "integration"
    price: float = 0.0
    install_count: int = 0
    rating: float = 0.0
    is_verified: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class APIMarketplaceService:
    """API and marketplace expansion — ecosystem growth infrastructure.

    Provides:
    - Public API portal with endpoint catalog
    - API key management and rate limiting
    - SDK generation support
    - Extension marketplace listings
    - Webhook subscription management
    - Event explorer for debugging
    - Connector marketplace
    """

    _endpoints: dict[str, ApiEndpoint] = field(default_factory=dict)
    _webhooks: dict[str, WebhookSubscription] = field(default_factory=dict)
    _marketplace: dict[str, MarketplaceListing] = field(default_factory=dict)

    def __post_init__(self):
        self._register_default_endpoints()
        self._register_default_marketplace()

    def _register_default_endpoints(self) -> None:
        """Register default public API endpoints."""
        endpoints = [
            ApiEndpoint(path="/contracts", method="POST", description="Upload a new contract for analysis", version="v1"),
            ApiEndpoint(path="/contracts/{id}", method="GET", description="Get contract analysis results", version="v1"),
            ApiEndpoint(path="/contracts/{id}/findings", method="GET", description="Get contract findings", version="v1"),
            ApiEndpoint(path="/contracts/{id}/redlines", method="GET", description="Get contract redline suggestions", version="v1"),
            ApiEndpoint(path="/search", method="POST", description="Search across contracts", version="v1"),
            ApiEndpoint(path="/reviews", method="GET", description="List contract reviews", version="v1"),
            ApiEndpoint(path="/reviews/{id}", method="GET", description="Get review details", version="v1"),
            ApiEndpoint(path="/reviews/{id}/approve", method="POST", description="Approve a review", version="v1"),
            ApiEndpoint(path="/vendors", method="GET", description="List vendors with intelligence", version="v1"),
            ApiEndpoint(path="/obligations", method="GET", description="List obligations", version="v1"),
            ApiEndpoint(path="/renewals", method="GET", description="Get renewal forecast", version="v1"),
            ApiEndpoint(path="/benchmarks/{clause_type}", method="GET", description="Get clause benchmarks", version="v1"),
            ApiEndpoint(path="/replay/{execution_id}", method="GET", description="Get replay comparison", version="v1", plan_access=[ApiPlan.PROFESSIONAL, ApiPlan.ENTERPRISE]),
            ApiEndpoint(path="/simulation/workflow", method="POST", description="Run workflow simulation", version="v1", plan_access=[ApiPlan.ENTERPRISE]),
            ApiEndpoint(path="/governance/reports", method="GET", description="Get governance reports", version="v1", plan_access=[ApiPlan.ENTERPRISE]),
        ]
        for ep in endpoints:
            self.register_endpoint(ep)

    def _register_default_marketplace(self) -> None:
        """Register default marketplace listings."""
        listings = [
            MarketplaceListing(listing_id="docusign", name="DocuSign Integration", description="Send contracts for e-signature via DocuSign", publisher="ContractRiskEdge", category="integration", is_verified=True),
            MarketplaceListing(listing_id="slack", name="Slack Notifications", description="Receive review notifications in Slack", publisher="ContractRiskEdge", category="integration", is_verified=True),
            MarketplaceListing(listing_id="salesforce", name="Salesforce Sync", description="Sync contract status with Salesforce opportunities", publisher="ContractRiskEdge", category="integration", is_verified=True),
            MarketplaceListing(listing_id="custom_policy", name="Custom Policy Pack SDK", description="Build custom governance policies", publisher="ContractRiskEdge", category="developer_tools", price=0.0),
            MarketplaceListing(listing_id="custom_evaluator", name="Custom AI Evaluator SDK", description="Build custom AI evaluation logic", publisher="ContractRiskEdge", category="developer_tools", price=0.0),
            MarketplaceListing(listing_id="workflow_templates", name="Advanced Workflow Templates", description="Pre-built workflow templates for enterprise scenarios", publisher="ContractRiskEdge", category="workflows", price=499.0),
        ]
        for listing in listings:
            self.register_listing(listing)

    def register_endpoint(self, endpoint: ApiEndpoint) -> None:
        """Register a public API endpoint."""
        key = f"{endpoint.method}:{endpoint.path}"
        self._endpoints[key] = endpoint

    def get_endpoints(self, plan: ApiPlan = ApiPlan.STARTER) -> list[dict[str, Any]]:
        """Get API endpoints accessible for a plan."""
        return [
            {"path": ep.path, "method": ep.method, "description": ep.description, "version": ep.version}
            for ep in self._endpoints.values()
            if plan in ep.plan_access
        ]

    def register_listing(self, listing: MarketplaceListing) -> None:
        """Register a marketplace listing."""
        self._marketplace[listing.listing_id] = listing

    def get_marketplace(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get marketplace listings."""
        listings = self._marketplace.values()
        if category:
            listings = [l for l in listings if l.category == category]
        return [
            {"id": l.listing_id, "name": l.name, "description": l.description, "publisher": l.publisher,
             "category": l.category, "price": l.price, "rating": l.rating, "verified": l.is_verified}
            for l in listings
        ]

    async def create_webhook(self, tenant_id: str, url: str, events: list[str]) -> WebhookSubscription:
        """Create a webhook subscription."""
        import uuid
        import secrets
        sub = WebhookSubscription(
            subscription_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            url=url,
            events=events,
            secret=secrets.token_hex(32),
        )
        self._webhooks[sub.subscription_id] = sub
        return sub

    def get_webhooks(self, tenant_id: str) -> list[WebhookSubscription]:
        """Get webhook subscriptions for a tenant."""
        return [w for w in self._webhooks.values() if w.tenant_id == tenant_id]

    def delete_webhook(self, subscription_id: str) -> None:
        """Delete a webhook subscription."""
        self._webhooks.pop(subscription_id, None)

    def get_api_portal_data(self) -> dict[str, Any]:
        """Get API portal data for documentation generation."""
        return {
            "endpoints": [
                {"path": ep.path, "method": ep.method, "description": ep.description, "version": ep.version,
                 "auth": ep.auth_required, "rate_limit": ep.rate_limit,
                 "plan_access": [p.value for p in ep.plan_access]}
                for ep in self._endpoints.values()
            ],
            "marketplace": self.get_marketplace(),
            "webhook_events": [
                "ai.execution.completed", "ai.execution.failed",
                "review.assigned", "review.completed",
                "workflow.sla_breached", "workflow.escalated",
                "contract.uploaded", "contract.analyzed",
                "obligation.overdue", "renewal.upcoming",
            ],
            "sdks": [
                {"language": "Python", "url": "https://github.com/contractriskedge/sdk-python", "status": "stable"},
                {"language": "JavaScript", "url": "https://github.com/contractriskedge/sdk-js", "status": "beta"},
                {"language": "TypeScript", "url": "https://github.com/contractriskedge/sdk-typescript", "status": "beta"},
            ],
        }


# ── Global singleton ───────────────────────────────────────────────

api_marketplace = APIMarketplaceService()
