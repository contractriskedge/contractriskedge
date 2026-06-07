# Policy Pack Override References — Key Matching Strategy Audit

**Date**: 2026-06-05  
**Objective**: Verify that Policy Pack overrides contain stable references to Playbook entities, and propose a matching strategy

---

## Current State: The Three Override Types

### 1. `PolicyPackClauseOverride`

| Field | Type | Purpose | References Playbook? |
|-------|------|---------|---------------------|
| `clause_id` | `str` | Which clause standard to override | ✅ **Intended to match `clause_standards.clause_id`** |
| `override_body` | `Optional[str]` | Replacement clause text | N/A |
| `override_risk_level` | `Optional[str]` | Override risk classification | N/A |
| `is_active` | `Optional[bool]` | Toggle override | N/A |

**Reference stability**: `clause_id` is intended to be a UUID matching `clause_standards.clause_id`. However, the schema defines it as `str`, not `UUID`. This means:
- ✅ UUID format works (36 chars, hyphenated)
- ⚠️ Non-UUID strings could be stored (human-readable names, slugs)
- ⚠️ No foreign key constraint exists — orphan references are possible

### 2. `PolicyPackRuleOverride`

| Field | Type | Purpose | References Playbook? |
|-------|------|---------|---------------------|
| `rule_id` | `str` | Which policy rule to override | ✅ **Intended to match `policy_rules.rule_id`** |
| `override_effect` | `Optional[str]` | Override rule effect | N/A |
| `override_priority` | `Optional[int]` | Override evaluation priority | N/A |
| `is_active` | `Optional[bool]` | Toggle override | N/A |
| `effect_config_overrides` | `Optional[dict]` | Override effect configuration | N/A |

**Reference stability**: Same as clause overrides — `rule_id` is `str`, not `UUID`. Same risks apply.

### 3. `PolicyPackThresholdOverride`

| Field | Type | Purpose | References Playbook? |
|-------|------|---------|---------------------|
| `threshold_id` | `str` | Which approval threshold to override | ✅ **Intended to match `approval_thresholds.threshold_id`** |
| `override_min_value` | `Optional[float]` | Override minimum threshold | N/A |
| `override_max_value` | `Optional[float]` | Override maximum threshold | N/A |
| `override_approval_role` | `Optional[str]` | Override required approval role | N/A |
| `override_approval_level` | `Optional[int]` | Override escalation level | N/A |

**Reference stability**: Same pattern — `threshold_id` is `str`, not `UUID`.

---

## Playbook Entity Primary Keys

| Table | PK Column | Type | Format | Example |
|-------|-----------|------|--------|---------|
| `clause_standards` | `clause_id` | `uuid` | UUID v4 | `39880cc3-1eb8-4e03-ba32-7f58fcd351f5` |
| `policy_rules` | `rule_id` | `uuid` | UUID v4 | `ab07de98-1eb8-4e03-ba32-7f58fcd351f5` |
| `approval_thresholds` | `threshold_id` | `uuid` | UUID v4 | (same format) |

All three Playbook tables use **UUID v4** as their primary key. The Policy Pack override schemas store these references as `str`, which is compatible with UUID string representation.

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Override references orphaned Playbook entity (deleted) | **High** | Medium | Validate references at query time; skip unresolved overrides |
| Override references wrong entity type (e.g., `rule_id` in `clause_id` field) | **Medium** | Low | Validate target table at query time |
| Non-UUID string stored as reference (e.g., human-readable name) | **Medium** | Low | Attempt UUID parse; fall back to name-based matching |
| Cross-tenant reference (Pack from Tenant A references Playbook from Tenant B) | **Low** | Low | All queries scoped by `tenant_id` |

---

## Matching Strategy

### Primary Strategy: UUID Key Matching

At query time, the `TenantConfigContextProvider` resolves overrides by matching `clause_id` / `rule_id` / `threshold_id` against Playbook PKs:

```python
async def _resolve_clause_overrides(self, playbook_clauses, policy_packs):
    """Apply Policy Pack clause overrides to Playbook clause standards."""
    clause_map = {str(c.clause_id): c for c in playbook_clauses}
    
    for pack in policy_packs:
        for override in pack.clause_overrides:
            target = clause_map.get(override.clause_id)
            if target is None:
                # Try name-based fallback
                target = self._find_clause_by_name(playbook_clauses, override.clause_id)
            if target is None:
                logger.warning("Unresolved clause override: %s", override.clause_id)
                continue
            
            # Apply override
            if override.override_body is not None:
                target.body = override.override_body
            if override.override_risk_level is not None:
                target.risk_level = override.override_risk_level
    
    return playbook_clauses
```

### Fallback Strategy: Name-Based Matching

For cases where the UI might store a human-readable name instead of a UUID:

```python
def _find_clause_by_name(self, clauses, name_or_id):
    """Match by UUID first, then by name/category fallback."""
    # Try UUID match
    try:
        uuid.UUID(name_or_id)
        return None  # Valid UUID but not found — truly orphaned
    except ValueError:
        pass
    
    # Try name match
    for c in clauses:
        if c.title.lower() == name_or_id.lower():
            return c
        if c.category.value.lower() == name_or_id.lower():
            return c
    
    return None
```

### Rule and Threshold Resolution

Same pattern for rules and thresholds:

```python
async def _resolve_rule_overrides(self, playbook_rules, policy_packs):
    rule_map = {str(r.rule_id): r for r in playbook_rules}
    for pack in policy_packs:
        for override in pack.rule_overrides:
            target = rule_map.get(override.rule_id)
            if target is None:
                target = self._find_rule_by_name(playbook_rules, override.rule_id)
            if target is None:
                continue
            if override.override_effect is not None:
                target.effect = override.override_effect
            if override.override_priority is not None:
                target.priority = override.override_priority

async def _resolve_threshold_overrides(self, playbook_thresholds, policy_packs):
    threshold_map = {str(t.threshold_id): t for t in playbook_thresholds}
    for pack in policy_packs:
        for override in pack.threshold_overrides:
            target = threshold_map.get(override.threshold_id)
            if target is None:
                continue
            if override.override_min_value is not None:
                target.min_value = override.override_min_value
            if override.override_max_value is not None:
                target.max_value = override.override_max_value
            if override.override_approval_role is not None:
                target.approval_role = override.override_approval_role
```

---

## Schema Change Requirements

### Required: None

The existing schema supports the matching strategy without changes:
- `clause_standards.clause_id` is `uuid` — Policy Pack `clause_id` (str) can store its string representation
- `policy_rules.rule_id` is `uuid` — Policy Pack `rule_id` (str) can store its string representation
- `approval_thresholds.threshold_id` is `uuid` — Policy Pack `threshold_id` (str) can store its string representation

### Recommended: Foreign Key Constraints (Future)

Adding foreign key constraints would prevent orphan references:

```sql
-- Option 1: Change column types to UUID
ALTER TABLE policy_packs ALTER COLUMN rule_overrides 
  SET DATA TYPE jsonb;  -- already jsonb, but validate UUID format in app

-- Option 2: Add check constraints (PostgreSQL can't enforce JSONB FK)
-- Not possible — JSONB columns can't have foreign key constraints
```

Since `rule_overrides`, `threshold_overrides`, and `clause_overrides` are **JSONB arrays**, PostgreSQL cannot enforce foreign key constraints on nested JSON fields. Validation must happen at the application layer.

### Recommended: Index on `playbook_id` in `policy_packs`

The `policy_packs` table already has a `playbook_id` column. An index on this column would speed up the merge query:

```sql
CREATE INDEX ix_policy_packs_playbook_id ON policy_packs (playbook_id);
```

This is a **non-breaking, additive change** that can be applied without downtime.

---

## Summary

| Aspect | Status | Action |
|--------|--------|--------|
| Override ID fields match Playbook PKs | ✅ Compatible | UUIDs stored as strings in JSONB |
| Foreign key enforcement | ❌ Not possible | JSONB prevents FK constraints |
| Orphan reference risk | ⚠️ Medium | Handle gracefully at query time (skip unresolved) |
| Name-based fallback | ✅ Recommended | UUID match first, name match second |
| Schema changes needed | ❌ **None** | Existing schema supports the strategy |
| Recommended index | ⚠️ Optional | `CREATE INDEX ix_policy_packs_playbook_id` |

**The existing schema supports the merge strategy without changes.** The three override types (`clause_id`, `rule_id`, `threshold_id`) are compatible with Playbook UUID primary keys. The `TenantConfigContextProvider` should:
1. Attempt UUID key matching first
2. Fall back to name-based matching
3. Gracefully skip unresolved references with a warning log
