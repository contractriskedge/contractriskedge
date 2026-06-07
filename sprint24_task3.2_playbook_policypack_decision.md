# Sprint 24 Task 3.2 — Playbook vs Policy Pack Architecture Decision

**Date**: 2026-06-05  
**Objective**: Determine whether Policy Packs should be deprecated or retained as tenant-specific overlays

---

## Decision: Option B — Retain Policy Packs as Tenant-Specific Overlays

**Policy Packs should NOT be deprecated.** They serve a distinct purpose from the Playbook. The correct architecture is:

```
Playbook (Global/Shared Standards)
    │
    ├── Clause Standards (approved/preferred/fallback/forbidden)
    ├── Policy Rules (structured, versioned, jurisdiction-scoped)
    └── Policy Evaluations (per-contract audit trail)
    │
    ▼
Policy Packs (Tenant-Specific Overrides)
    │
    ├── Rule Overrides (modify Playbook rule behavior per tenant)
    ├── Threshold Overrides (customize risk/approval thresholds per tenant)
    └── Clause Overrides (override clause language per tenant)
    │
    ▼
TenantConfigContextProvider (Merged View)
    │
    ├── Playbook standards (base)
    ├── Policy Pack overrides (tenant-specific modifications)
    └── Merged context → AI Pipeline
```

---

## Analysis

### 1. Existing Playbook Architecture

| Feature | Details |
|---------|---------|
| **Tables** | `legal_playbooks`, `playbook_versions`, `clause_standards`, `policy_rules`, `policy_evaluations` |
| **Tenant isolation** | ✅ All tables have `tenant_id` — fully per-tenant |
| **Versioning** | ✅ Full versioning via `playbook_versions` snapshots |
| **Clause types** | `approved`, `preferred`, `fallback`, `forbidden`, `conditional` |
| **Rule types** | `clause_required`, `clause_forbidden`, `deviation`, `approval`, `risk_threshold`, `value_threshold` |
| **Rule effects** | `allow`, `block`, `flag_for_review`, `require_approval`, `require_mandatory_clause`, `recommend_fallback`, `escalate` |
| **AI integration** | ✅ `PlaybookContextProvider` + `AIPolicyInjectionService` already inject into redline prompts |
| **Current data** | 3 playbooks, 4 clause standards, 10 policy rules |
| **API** | Full CRUD at `/api/v1/playbooks/*` |

### 2. Existing Policy Pack Schema

| Feature | Details |
|---------|---------|
| **Table** | `policy_packs` |
| **Tenant isolation** | ✅ `tenant_id` column — per-tenant |
| **Versioning** | ❌ No versioning — single row per pack |
| **Data structure** | JSONB columns: `rule_overrides`, `threshold_overrides`, `clause_overrides` |
| **Scope** | Per-pack scope (tenant, business_unit, deal) |
| **AI integration** | ❌ Disconnected — never read during analysis |
| **Current data** | 0 packs (no tenant has created one yet) |
| **API** | Full CRUD at `/api/v1/tenant-config/policy-packs` |

### 3. Key Distinction: Global Standards vs Tenant Overrides

The fundamental difference:

| Dimension | Playbook | Policy Packs |
|-----------|----------|-------------|
| **Purpose** | Canonical clause standards and policy rules | Tenant-specific modifications to standards |
| **Granularity** | Per-playbook (jurisdiction/practice-area scoped) | Per-pack (tenant/business-unit/deal scoped) |
| **Versioning** | Full version history with published snapshots | No versioning (current state only) |
| **Data model** | Structured columns with typed enums | JSONB (flexible, schema-less) |
| **Creation** | Legal team publishes playbooks | Tenant admin creates overrides |
| **Lifecycle** | Formal publish/archive workflow | Simple CRUD |

**Policy Packs are NOT a duplicate of Playbook.** They are a **simplified, tenant-facing customization layer** that modifies Playbook behavior without requiring tenants to understand Playbook versioning or publish workflows.

### 4. Multi-Tenant Customization Requirements

| Requirement | Playbook | Policy Packs | Solution |
|-------------|----------|-------------|----------|
| Global standards for all tenants | ✅ Yes | ❌ No | Playbook defines the base |
| Tenant-specific overrides | ❌ Would require per-tenant copy | ✅ Yes | Policy Packs modify base |
| Business-unit-level customization | ❌ Not designed for this | ✅ `scope` field supports BU | Policy Packs handle this |
| Deal-level exceptions | ❌ Too granular | ✅ Can create deal-scoped pack | Policy Packs handle this |
| Legal team controls standards | ✅ Yes | ❌ No | Playbook is legal-owned |
| Tenant admin controls overrides | ❌ No | ✅ Yes | Policy Packs are tenant-owned |

### 5. Versioning Requirements

The Playbook's versioning is designed for **legal content that changes infrequently** (quarterly/annually). Policy Packs are designed for **operational configuration that changes frequently** (per-deal, per-business-unit). These are different versioning patterns:

```
Playbook versioning:  v1 (Q1) → v2 (Q2) → v3 (Q3)
                      (legal review, published, immutable snapshots)

Policy Pack versioning:  Pack A → Edit → Edit → Edit
                         (tenant admin, no formal publishing)
```

Merging these would force tenant admins through a legal publishing workflow for simple threshold changes.

### 6. Enterprise Governance Requirements

```
Enterprise hierarchy:
  Legal Team ──→ Playbook (global standards, published)
       │
       ▼
  Tenant Admin ──→ Policy Packs (tenant overrides, simple CRUD)
       │
       ▼
  Reviewer ──→ Per-deal decisions (within Review Workspace)
```

Each layer has different ownership, different workflows, and different UI requirements. Merging them would create a single system that serves neither audience well.

---

## Recommended Architecture

### Source of Truth Hierarchy

```
Priority 1: Policy Pack Overrides (highest precedence)
  └─ Override Playbook standards for this tenant/BU/deal

Priority 2: Playbook Standards (base)
  └─ Fallback when no Policy Pack override exists

Priority 3: App-level defaults
  └─ Fallback when neither Playbook nor Policy Pack is configured
```

### Data Flow

```
TenantConfigContextProvider.get_policy_context(tenant_id, scope)
  │
  ├── 1. Fetch active Playbook for this tenant
  │     └── PlaybookRepository.get_active_playbook(tenant_id)
  │
  ├── 2. Fetch active Policy Packs for this tenant + scope
  │     └── PolicyPackService.list_packs(tenant_id, scope)
  │
  ├── 3. Merge: Apply Policy Pack overrides on top of Playbook standards
  │     ├── rule_overrides → modify matching PolicyRule parameters
  │     ├── threshold_overrides → override risk/approval thresholds
  │     └── clause_overrides → replace ClauseStandard body text
  │
  └── 4. Return merged context → AI Pipeline
        └── AIService._build_risk_analysis_request()
```

### Merge Logic

```python
def merge_policy_context(playbook, policy_packs):
    """Apply Policy Pack overrides on top of Playbook standards."""
    
    # Start with Playbook standards
    merged_clauses = list(playbook.clause_standards)
    merged_rules = list(playbook.policy_rules)
    merged_thresholds = list(playbook.policy_rules.filter(rule_type="risk_threshold"))
    
    for pack in policy_packs:
        # Clause overrides: replace matching clause bodies
        for override in pack.clause_overrides:
            idx = find_clause_by_id(merged_clauses, override.clause_id)
            if idx >= 0:
                merged_clauses[idx].body = override.override_body
                merged_clauses[idx].risk_level = override.override_risk_level
        
        # Rule overrides: modify matching rule parameters
        for override in pack.rule_overrides:
            idx = find_rule_by_id(merged_rules, override.rule_id)
            if idx >= 0:
                merged_rules[idx].effect = override.override_effect
                merged_rules[idx].priority = override.override_priority
        
        # Threshold overrides: replace matching thresholds
        for override in pack.threshold_overrides:
            idx = find_threshold_by_id(merged_thresholds, override.threshold_id)
            if idx >= 0:
                merged_thresholds[idx].min_value = override.override_min_value
                merged_thresholds[idx].max_value = override.override_max_value
                merged_thresholds[idx].approval_role = override.override_approval_role
    
    return PolicyContext(
        clauses=merged_clauses,
        rules=merged_rules,
        thresholds=merged_thresholds,
    )
```

### Integration Point

The `TenantConfigContextProvider` (from Sprint 24 Task 3.0 design) is the correct place to implement this merge:

```
TenantConfigContextProvider
  ├── get_policy_context() → merges Playbook + Policy Packs
  ├── get_scoring_context() → reads Scoring Overrides (separate)
  ├── get_compliance_context() → merges Playbook + Compliance Packs
  └── get_ai_settings() → reads Tenant Settings (separate)
```

---

## Migration Impact

### Data Migration

**None required.** Policy Packs remain in their own table. The merge happens at query time in the `TenantConfigContextProvider`. No schema changes needed.

### UI Impact

**None.** The Settings UI continues to write to `policy_packs` and `compliance_packs` tables. The UI doesn't change — only the AI pipeline's reading behavior changes.

### API Impact

**None.** Existing CRUD APIs remain unchanged. The new `TenantConfigContextProvider` is an internal service, not a new API endpoint.

### Playbook Impact

**None.** Playbook continues to be the canonical source of clause standards and policy rules. Policy Packs simply modify Playbook output at query time.

---

## Architecture Decision Record

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Deprecate Policy Packs? | **No** | They serve a distinct purpose as tenant-specific overlays |
| Merge into Playbook? | **No** | Would force tenant admins through legal publishing workflow |
| Keep separate tables? | **Yes** | Different ownership, different lifecycle, different UI |
| Merge at query time? | **Yes** | `TenantConfigContextProvider` merges Playbook + Policy Packs |
| Playbook is canonical? | **Yes** | Base standards come from Playbook; Policy Packs modify them |
| Policy Packs override Playbook? | **Yes** | Higher precedence — tenant-specific overrides win |

---

## Summary

| Aspect | Option A (Deprecate) | Option B (Retain as Overlay) |
|--------|---------------------|---------------------------|
| **Duplicate data** | Eliminates duplication | Accepts some overlap (different granularity) |
| **Tenant customization** | Must copy entire Playbook per tenant | Lightweight overrides on shared Playbook |
| **Versioning complexity** | Single versioning system | Two versioning patterns (appropriate for each) |
| **Implementation effort** | High (migration + UI changes) | Low (query-time merge only) |
| **Enterprise governance** | Legal controls everything | Legal controls standards, tenant controls overrides |
| **Flexibility** | Less flexible (one-size-fits-all) | More flexible (layered customization) |

**Verdict**: Option B is the correct choice. Policy Packs are retained as lightweight, tenant-specific overlays that modify Playbook behavior at query time. No data migration, no schema changes, no UI changes — just a merge layer in the `TenantConfigContextProvider`.
