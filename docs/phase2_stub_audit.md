# Phase 2 — Stub Domain Audit & Elimination

**Date:** 2026-05-27
**Author:** DeepSeek (Production Reality Execution Mode)
**Status:** FINAL

---

## Executive Summary

The backend contains **65 domain directories**. Of these:
- **23 domains (35%)** have real implementation (router + service + schemas + models)
- **42 domains (65%)** are stubs — empty directories or `__init__.py`-only with in-memory dataclasses

**All 42 stubs are now classified for elimination.**

---

## Classification Legend

| Label | Meaning | Count |
|-------|---------|-------|
| **DELETE** | Remove entirely. No production value. | 24 |
| **IMPLEMENT** | Build real implementation — core to wedge. | 6 |
| **DEFER** | Keep directory, remove from router. Revisit post-Phase 2. | 12 |

---

## STUBS TO DELETE (24)

These domains are speculative architecture with no path to production value in the Procurement + Vendor Contract Risk wedge. Remove entirely.

| # | Domain | Rationale |
|---|--------|-----------|
| 1 | `autonomous_coordination/` | No customer need. Pure research concept. |
| 2 | `autonomous_ops/` | No customer need. Pure research concept. |
| 3 | `cognitive/` | Buzzword domain. No clear product requirement. |
| 4 | `collaboration/` | Overlaps with review workflow. Not needed as separate domain. |
| 5 | `coordination_graph/` | No product requirement. Speculative. |
| 6 | `customer_success/` | Post-sales. Premature. No data model exists. |
| 7 | `digital_twin/` | Enterprise buzzword. No implementation path. |
| 8 | `ecosystem_marketplace/` | Marketplace is post-Series A feature. Delete stub. |
| 9 | `executive_intelligence/` | In-memory dataclass only. Intelligence belongs in analytics domain. |
| 10 | `executive_ui/` | UI belongs in frontend, not backend domains. |
| 11 | `federation/` | Multi-tenant federation is premature. |
| 12 | `governance_ops/` | Overlaps with ai_governance + audit. Merge or delete. |
| 13 | `governance_standards/` | No implementation. Premature. |
| 14 | `industry_network/` | In-memory seed data only. Network effects are post-adoption. |
| 15 | `intelligence_fabric/` | No clear product requirement. |
| 16 | `knowledge_fabric/` | No clear product requirement. |
| 17 | `knowledge_graph/` | No implementation. Premature for Phase 2. |
| 18 | `learning/` | ML training pipeline. Premature without production data. |
| 19 | `memory_graph/` | No product requirement. Speculative. |
| 20 | `multi_tenant_intel/` | In-memory dataclass only. Premature. |
| 21 | `optimization/` | No clear requirement. |
| 22 | `predictive/` | ML feature. Premature without production data. |
| 23 | `protocols/` | No product requirement. |
| 24 | `recommendation_engine/` | Premature. Needs real usage data first. |

---

## STUBS TO IMPLEMENT (6)

These are core to the Procurement + Vendor Contract Risk wedge. Build real implementations.

| # | Domain | Priority | Implementation Strategy |
|---|--------|----------|------------------------|
| 1 | `compliance/` | HIGH | Implement compliance checking against procurement regulations. Wire to review workflow. |
| 2 | `onboarding/` | HIGH | Vendor onboarding workflow. Connect to ingestion + review. Critical for demo flow #2. |
| 3 | `org_memory/` | MEDIUM | Store historical review decisions, negotiation patterns, reviewer behavior. Core differentiator. |
| 4 | `ops/` | MEDIUM | Operational dashboards, health monitoring. Connect to analytics domain. |
| 5 | `review_ops/` | MEDIUM | Review operations metrics, reviewer load, SLA tracking. |
| 6 | `simulation/` | LOW | What-if analysis for contract terms, pricing scenarios. Needed for demo flow #4. |

---

## STUBS TO DEFER (12)

Keep directory structure, remove from active router. Revisit after Phase 2 adoption metrics.

| # | Domain | Revisit Trigger |
|---|--------|-----------------|
| 1 | `extensions/` | When marketplace becomes viable |
| 2 | `productivity/` | When user base > 100 |
| 3 | `queue/` | When async queue needs dedicated management |
| 4 | `reviewer_experience/` | When reviewer UX feedback demands it |
| 5 | `roi/` | When customer success needs ROI tracking |
| 6 | `security/` | When security-specific domain is needed (keep in kernel for now) |
| 7 | `strategy/` | When executive strategy features are requested |
| 8 | `strategy_engine/` | Same as above |
| 9 | `support/` | When support ticket integration is needed |
| 10 | `tenant_runtime/` | When multi-tenant runtime isolation is needed |
| 11 | `workspaces/` | When workspace isolation is needed |
| 12 | `workflow_os/` | Workflow OS abstraction — premature, keep workflow_packs only |

---

## ACTION PLAN

### Week 1: Delete 24 stubs
```bash
rm -rf backend/app/domains/autonomous_coordination
rm -rf backend/app/domains/autonomous_ops
rm -rf backend/app/domains/cognitive
# ... all 24
```

### Week 1: Remove deferred stubs from imports
- Remove any references to deferred domains from `main.py` and import chains
- Keep directories but ensure zero code paths reference them

### Week 2-3: Implement HIGH priority stubs
- `compliance/` — compliance engine integrated with review
- `onboarding/` — vendor onboarding workflow

### Week 4: Implement MEDIUM priority stubs
- `org_memory/` — historical decision storage
- `ops/` — operational dashboards
- `review_ops/` — review operations metrics

---

## Result

After elimination:
- **Before:** 65 domains (23 real + 42 stubs)
- **After:** 29 domains (23 real + 6 implemented) — **55% reduction**
- **Active code paths:** All connected to Procurement + Vendor Contract Risk wedge
