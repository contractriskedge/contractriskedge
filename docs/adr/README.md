# Architecture Decision Records — ContractRiskEdge Platform
# =============================================================================
# Each ADR documents a significant architectural decision with context,
# options considered, and rationale.
# =============================================================================

# ══════════════════════════════════════════════════════════════════════════════
# ADR-001: Hybrid Vector Partition Strategy
# ══════════════════════════════════════════════════════════════════════════════

## Status
Accepted

## Context
The platform needs to serve both small tenants (developer/starter) and large
enterprise tenants with different isolation and performance requirements.
A single shared vector collection would create noisy-neighbor problems at scale.
Per-tenant dedicated collections for all tenants would be cost-prohibitive.

## Decision
Use a hybrid strategy:
- Small tenants (developer, starter, professional) → shared collection with
  metadata tenant_id filters
- Large tenants (enterprise, platform) → dedicated per-tenant collections

## Consequences
Positive:
- Cost-efficient for small tenants
- Performance isolation for enterprise tenants
- Graduated upgrade path as tenants grow

Negative:
- Shared collections require metadata filter enforcement
- Collection migration needed when tenant upgrades tier
- Monitoring complexity for two strategies

## Implementation
`RetrievalPartitionManager.resolve_collection()` in
`domains/vectors/partition/__init__.py`


# ══════════════════════════════════════════════════════════════════════════════
# ADR-002: Replay Immutability Rules
# ══════════════════════════════════════════════════════════════════════════════

## Status
Accepted

## Context
AI execution reproducibility is critical for audit compliance and drift detection.
Without frozen retrieval context, the same execution_id may produce different
results if the vector DB has been updated.

## Decision
Every AI execution that involves retrieval MUST:
1. Create a RetrievalSnapshot before execution (freezing chunk IDs, scores,
   embedding model version, reranker version)
2. Store the snapshot_id in the execution context
3. Verify snapshot integrity before replay

## Consequences
Positive:
- Deterministic replay — same execution_id always produces identical context
- Tamper-evident audit trail for AI decisions
- Drift detection between original and replayed runs

Negative:
- Storage overhead for frozen chunk text in snapshots
- Additional latency to create snapshot before execution

## Implementation
`RetrievalSnapshotService` in `domains/ai/snapshots/`
`ReplayAIExecutionService` in `domains/ai/replay/`


# ══════════════════════════════════════════════════════════════════════════════
# ADR-003: Event Versioning Strategy
# ══════════════════════════════════════════════════════════════════════════════

## Status
Accepted

## Context
The platform uses events for async communication. Without versioning, schema
changes to events will break subscribers. Multiple event schemas may coexist
during migration periods.

## Decision
Use semantic versioning for event schemas:
- Each event type has a registered schema with version
- Breaking changes increment major version
- Backward-compatible changes increment minor version
- Subscribers declare which version they support
- Event bus validates payloads against schema before publishing

## Consequences
Positive:
- Safe schema evolution
- Subscriber compatibility checking
- Event replay across versions

Negative:
- Schema registration overhead
- Version resolution complexity

## Implementation
`UnifiedEventBus` in `domains/platform/events/`


# ══════════════════════════════════════════════════════════════════════════════
# ADR-004: Tenant Isolation Levels
# ══════════════════════════════════════════════════════════════════════════════

## Status
Accepted

## Context
Multi-tenant isolation is the #1 architectural risk. Different tenants have
different isolation requirements based on compliance needs and data sensitivity.

## Decision
Define three isolation levels:
1. SHARED — All tenants share infrastructure, isolated by tenant_id metadata
   filters. Suitable for developer/starter tiers.
2. DEDICATED_COLLECTIONS — Per-tenant vector collections, shared compute.
   Suitable for professional tier.
3. DEDICATED_INFRA — Per-tenant compute and storage. Suitable for enterprise tier.

All levels enforce:
- tenant_id required on every query (fail-closed if missing)
- JWT-derived tenant context (never from client headers)
- Tenant-scoped repositories via BaseRepository.filter_tenant()

## Consequences
Positive:
- Graduated isolation that matches tenant value
- Clear upgrade path
- Fail-closed behavior prevents data leaks

Negative:
- More complex deployment topology for dedicated infra
- Cross-tenant query requires admin:system permission with audit log

## Implementation
`TenantContextResolver`, `TenantQuotaManager` in `domains/tenant_runtime/`
`BaseRepository.filter_tenant()` in `kernel/repository/base.py`


# ══════════════════════════════════════════════════════════════════════════════
# ADR-005: Provider Routing Policy
# ══════════════════════════════════════════════════════════════════════════════

## Status
Accepted

## Context
The platform supports multiple AI providers (OpenAI, Anthropic). Provider
selection affects cost, latency, quality, and availability. A static provider
assignment is insufficient for enterprise reliability.

## Decision
Implement a tiered routing strategy:
1. Primary: Use preferred provider/model from execution plan
2. Fallback chain: Try providers in priority order if primary fails
3. Circuit breaker: Auto-disable providers with >30% failure rate
4. Cost-aware: Route to cheaper model if tenant budget is constrained
5. Tenant override: Enterprise tenants can pin specific providers

## Consequences
Positive:
- Automatic failover on provider outage
- Cost optimization per tenant tier
- Circuit breaker prevents cascading failures

Negative:
- Routing complexity increases with more providers
- Different model outputs may cause consistency issues during failover

## Implementation
`LLMProviderRegistry` in `domains/ai/providers/registry.py`
`IntelligentRouter` in `domains/cost_governance/`
