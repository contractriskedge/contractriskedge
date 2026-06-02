"""Platform Governance — centralized runtime control for production enterprise AI infrastructure.

This is the consolidation layer that prevents:
- Architectural drift
- Operational inconsistency
- Runtime complexity explosion
- Governance fragmentation

Sub-modules:
- db_governance/ — migration governance, schema validation, rollback safety
- api/ — API versioning, schema registry, OpenAPI governance, deprecation lifecycle
- events/ — Unified event bus, registry, schema versioning, replay
- config/ — Dynamic config registry, feature rollout, audit trail
- data_pipeline/ — CDC streaming, analytics warehouse, event aggregation
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
