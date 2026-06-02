"""Multi-Region Runtime — region-aware routing, tenant affinity, regional failover, residency enforcement.

Critical for:
- EU customers (GDPR data residency)
- Enterprise compliance (data stays in region)
- Latency reduction (route to nearest region)
- Disaster recovery (regional failover)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Region(str, Enum):
    US_EAST = "us-east"
    US_WEST = "us-west"
    EU_WEST = "eu-west"
    EU_CENTRAL = "eu-central"
    AP_SOUTHEAST = "ap-southeast"
    AP_NORTHEAST = "ap-northeast"
    SA_EAST = "sa-east"
    ME_CENTRAL = "me-central"


class ResidencyPolicy(str, Enum):
    DATA_RESIDENT = "data_resident"       # Data must stay in region
    COMPUTE_ONLY = "compute_only"         # Compute can be remote, data stays
    NO_RESTRICTION = "no_restriction"     # No regional constraints


@dataclass
class RegionalEndpoint:
    """A regional deployment endpoint with health and capacity."""
    region: Region
    endpoint_url: str
    is_active: bool = True
    health_score: float = 1.0
    latency_ms: int = 0
    capacity_pct: float = 0.0  # 0.0-1.0 how full
    last_health_check: str = ""
    supports_providers: list[str] = field(default_factory=lambda: ["openai", "anthropic"])


@dataclass
class RegionRouter:
    """Routes requests to the optimal region based on tenant affinity and policies.

    Routing strategy:
    1. Tenant affinity — route to tenant's home region
    2. Residency policy — enforce data residency requirements
    3. Health — skip unhealthy regions
    4. Latency — prefer lowest latency region
    5. Capacity — avoid overloaded regions
    """

    _endpoints: dict[Region, RegionalEndpoint] = field(default_factory=dict)
    _tenant_affinity: dict[str, Region] = field(default_factory=dict)
    _tenant_residency: dict[str, ResidencyPolicy] = field(default_factory=dict)

    def register_endpoint(self, endpoint: RegionalEndpoint) -> None:
        """Register a regional deployment endpoint."""
        self._endpoints[endpoint.region] = endpoint
        logger.info("Registered regional endpoint: %s (%s)", endpoint.region.value, endpoint.endpoint_url)

    def set_tenant_affinity(self, tenant_id: str, region: Region) -> None:
        """Set a tenant's home region for affinity routing."""
        self._tenant_affinity[tenant_id] = region
        logger.info("Tenant %s affinity set to %s", tenant_id[:8], region.value)

    def set_tenant_residency(self, tenant_id: str, policy: ResidencyPolicy) -> None:
        """Set a tenant's data residency policy."""
        self._tenant_residency[tenant_id] = policy

    def get_optimal_region(
        self,
        tenant_id: str,
        preferred_provider: str = "openai",
        avoid_regions: list[Region] | None = None,
    ) -> tuple[Region, RegionalEndpoint]:
        """Get the optimal region for a tenant's request.

        Args:
            tenant_id: The tenant making the request.
            preferred_provider: Preferred AI provider.
            avoid_regions: Regions to avoid (e.g., during an outage).

        Returns:
            (region, endpoint) for the optimal region.

        Raises:
            ValueError: If no healthy region is available.
        """
        avoids = set(avoid_regions or [])
        residency = self._tenant_residency.get(tenant_id, ResidencyPolicy.NO_RESTRICTION)

        # Start with tenant affinity
        preferred_region = self._tenant_affinity.get(tenant_id)

        # Filter healthy endpoints
        candidates = [
            (r, e) for r, e in self._endpoints.items()
            if e.is_active
            and e.health_score > 0.3
            and r not in avoids
            and preferred_provider in e.supports_providers
        ]

        if not candidates:
            raise ValueError(f"No healthy regional endpoint available for provider {preferred_provider}")

        # If residency requires data to stay in region, filter to that region
        if residency == ResidencyPolicy.DATA_RESIDENT and preferred_region:
            region_candidates = [(r, e) for r, e in candidates if r == preferred_region]
            if region_candidates:
                return region_candidates[0]

        # If tenant has affinity and it's healthy, use it
        if preferred_region:
            for r, e in candidates:
                if r == preferred_region:
                    return r, e

        # Otherwise, pick healthiest
        candidates.sort(key=lambda x: x[1].health_score, reverse=True)
        return candidates[0]

    def get_region_for_failover(
        self,
        failed_region: Region,
        tenant_id: str,
        preferred_provider: str = "openai",
    ) -> tuple[Region, RegionalEndpoint]:
        """Get a failover region when the primary region is down."""
        return self.get_optimal_region(
            tenant_id=tenant_id,
            preferred_provider=preferred_provider,
            avoid_regions=[failed_region],
        )

    def record_health(self, region: Region, health_score: float, latency_ms: int) -> None:
        """Record a health check result for a region."""
        endpoint = self._endpoints.get(region)
        if endpoint:
            endpoint.health_score = health_score
            endpoint.latency_ms = latency_ms
            endpoint.last_health_check = datetime.utcnow().isoformat()
            endpoint.is_active = health_score > 0.3

    def get_regional_status(self) -> dict[str, Any]:
        """Get status of all regions."""
        return {
            r.value: {
                "active": e.is_active,
                "health": e.health_score,
                "latency_ms": e.latency_ms,
                "capacity_pct": e.capacity_pct,
                "providers": e.supports_providers,
            }
            for r, e in self._endpoints.items()
        }


# ── Regional Execution Context ─────────────────────────────────────

@dataclass
class RegionalExecutionContext:
    """Execution context with regional awareness for distributed execution."""
    tenant_id: str
    home_region: Region
    executing_region: Region
    residency_policy: ResidencyPolicy
    data_resident: bool = True
    provider_region: str = ""  # Which region the provider call goes to

    def is_cross_region(self) -> bool:
        """Check if this execution is cross-region."""
        return self.home_region != self.executing_region

    def allows_remote_compute(self) -> bool:
        """Check if remote compute is allowed by residency policy."""
        return self.residency_policy != ResidencyPolicy.DATA_RESIDENT


# ── Global singleton ───────────────────────────────────────────────

region_router = RegionRouter()
