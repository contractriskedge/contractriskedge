# Clause Guidance, Redline Generation & Policy Enforcement — Overlap Audit

**Date**: 2026-06-05  
**Objective**: Identify duplicate concepts across Playbook, Policy Engine, Policy Packs, and Compliance Packs  
**Goal**: Recommend a single source of truth for clause guidance, redline generation, and policy enforcement

---

## The Four Systems

| # | System | Table(s) | Purpose | Connected to AI? |
|---|--------|----------|---------|-----------------|
| 1 | **Playbook** | `legal_playbooks`, `playbook_versions`, `clause_standards`, `policy_rules`, `policy_evaluations` | Versioned clause standards + policy rules for clause evaluation | ✅ **Yes** — `PlaybookContextProvider` injects into redline prompts |
| 2 | **Policy Engine** | (app config + feature_flag_overrides) | Pre-execution governance: feature flags, model allowlist, region restrictions, PII detection | ✅ **Yes** — `AIPolicyEngine.validate()` runs before every LLM call |
| 3 | **Policy Packs** | `policy_packs` | Tenant-specific rule/threshold/clause overrides as JSONB | ❌ **No** — stored but never read |
| 4 | **Compliance Packs** | `compliance_packs` | Regional compliance packs with regulations and required/forbidden clauses | ❌ **No** — stored but never read |

---

## Overlap Analysis

### Overlap 1: Clause Language Guidance (3 systems)

| Concept | Playbook (`clause_standards`) | Policy Packs (`policy_packs.clause_overrides`) | Compliance Packs (`compliance_packs`) |
|---------|------------------------------|----------------------------------------------|--------------------------------------|
| **Approved clause text** | ✅ `ClauseStandard.body` where `clause_type=approved` | ✅ `PolicyPackClauseOverride.override_body` | ❌ Not present |
| **Preferred clause text** | ✅ `ClauseStandard.body` where `clause_type=preferred` | ❌ Not present | ❌ Not present |
| **Fallback clause text** | ✅ `ClauseStandard.body` where `clause_type=fallback` | ❌ Not present | ❌ Not present |
| **Forbidden clause text** | ✅ `ClauseStandard.body` where `clause_type=forbidden` | ❌ Not present | ❌ Not present |
| **Clause risk level** | ✅ `ClauseStandard.risk_level` | ✅ `PolicyPackClauseOverride.override_risk_level` | ❌ Not present |
| **Required clause categories** | ✅ `PolicyRule` with `effect=require_mandatory_clause` | ❌ Not present | ✅ `compliance_packs.required_clause_categories` |
| **Forbidden clause categories** | ✅ `PolicyRule` with `effect=block` | ❌ Not present | ✅ `compliance_packs.forbidden_clause_categories` |
| **Jurisdiction** | ✅ `ClauseStandard.applicable_jurisdictions` | ✅ `PolicyPackCreate.jurisdiction` | ✅ `compliance_packs.region` |
| **Industry** | ✅ `ClauseStandard.applicable_industries` | ✅ `PolicyPackCreate.industry` | ❌ Not present |
| **Contract value thresholds** | ✅ `ClauseStandard.min/max_contract_value` | ✅ `PolicyPackThresholdOverride` | ❌ Not present |

**Verdict**: **Significant overlap.** Three different systems store clause guidance data with different schemas. The Playbook (`clause_standards`) is the most mature with versioning, fallback chains, and structured policy rules. Policy Packs and Compliance Packs store simpler, unversioned versions of the same concepts.

### Overlap 2: Policy Rules / Rule Overrides (2 systems)

| Concept | Playbook (`policy_rules`) | Policy Packs (`policy_packs.rule_overrides`) |
|---------|--------------------------|---------------------------------------------|
| **Rule conditions** | ✅ Structured JSONB with operators, fields, values | ✅ `PolicyPackRuleOverride` with `effect_config_overrides` |
| **Rule effects** | ✅ Enum: allow, block, flag_for_review, require_approval, etc. | ✅ `override_effect` (string, less structured) |
| **Rule priority** | ✅ `priority` column (integer, lower=first) | ✅ `override_priority` (integer) |
| **Rule activation** | ✅ `is_active` column | ✅ `is_active` field |
| **Rule type** | ✅ `rule_type` column (clause_required, forbidden, deviation, etc.) | ❌ Not present |
| **Rule versioning** | ✅ Linked to playbook versions | ❌ No versioning |
| **Evaluation history** | ✅ `policy_evaluations` table tracks per-contract results | ❌ No evaluation tracking |

**Verdict**: **Partial overlap.** Policy Packs' `rule_overrides` is a simplified subset of Playbook's `policy_rules`. The Playbook's `policy_rules` has structured types, versioning, and evaluation history. Policy Packs' rules are untyped, unversioned JSONB.

### Overlap 3: Threshold Overrides (2 systems)

| Concept | Playbook (`policy_rules` with `rule_type=risk_threshold`) | Policy Packs (`policy_packs.threshold_overrides`) |
|---------|----------------------------------------------------------|--------------------------------------------------|
| **Value thresholds** | ✅ Via `conditions` JSONB with `greater_than`/`less_than` operators | ✅ `PolicyPackThresholdOverride.override_min/max_value` |
| **Approval routing** | ✅ Via `effect=require_approval` + `effect_config.approval_role` | ✅ `override_approval_role`, `override_approval_level` |

**Verdict**: **Partial overlap.** Same concept, different storage. Playbook's approach is more flexible (any operator, any field). Policy Packs' approach is simpler but limited to min/max values.

### Overlap 4: Compliance/Regulation Requirements (2 systems)

| Concept | Playbook (`policy_rules` with `applicable_jurisdictions`) | Compliance Packs (`compliance_packs`) |
|---------|----------------------------------------------------------|--------------------------------------|
| **Jurisdiction scoping** | ✅ `applicable_jurisdictions` array | ✅ `region` column |
| **Required clauses** | ✅ Via `effect=require_mandatory_clause` | ✅ `required_clause_categories` JSONB array |
| **Forbidden clauses** | ✅ Via `effect=block` | ✅ `forbidden_clause_categories` JSONB array |
| **Regulation references** | ❌ Not present | ✅ `regulations` JSONB array with `regulation_key`, `provisions` |
| **Jurisdiction rules** | ❌ Not present | ✅ `jurisdiction_rules` JSONB with clause category mappings |

**Verdict**: **Complementary.** Compliance Packs have regulation references that Playbook doesn't have. Playbook has structured rule evaluation that Compliance Packs don't have. These could be merged.

---

## Architecture Diagram: Current State

```
                    ┌─────────────────────────────────────────────┐
                    │           Tenant Settings UI                │
                    │  (General, Features, Policy Packs,          │
                    │   Scoring, Compliance, Summary)              │
                    └──────┬──────┬──────┬──────┬──────┬─────────┘
                           │      │      │      │      │
              ┌────────────┘      │      │      │      └────────────┐
              ▼                   ▼      ▼      ▼                   ▼
     ┌────────────────┐   ┌──────────┐ ┌────┐ ┌──────────┐  ┌──────────────┐
     │ feature_flag   │   │ policy   │ │scor│ │compliance│  │ tenant       │
     │ _overrides     │   │ _packs   │ │_over│ │_packs    │  │ _settings    │
     │ (table)        │   │ (table)  │ │rides│ │ (table)  │  │ (table)      │
     └────────┬───────┘   └────┬─────┘ └──┬──┘ └────┬─────┘  └──────┬───────┘
              │                │          │         │               │
              ▼                ▼          ▼         ▼               ▼
     ┌────────────────┐   ┌──────────┐ ┌────┐ ┌──────────┐  ┌──────────────┐
     │ AIPolicyEngine │   │  NOT     │ │NOT │ │  NOT     │  │  NOT         │
     │ (reads flags)  │   │CONNECTED │ │CONN │ │CONNECTED │  │  CONNECTED   │
     └────────────────┘   └──────────┘ └────┘ └──────────┘  └──────────────┘
              │
              ▼
     ┌────────────────┐   ┌──────────────────────────────┐
     │  AI Analysis   │   │  PlaybookContextProvider     │
     │  Pipeline      │   │  (reads clause_standards)    │
     │  (service.py)  │   └──────────┬───────────────────┘
     └────────────────┘              │
              │                      ▼
              ▼              ┌────────────────┐
     ┌────────────────┐      │  Redline       │
     │  Findings      │      │  Generation    │
     │  Generation    │      │  (prompts)     │
     └────────────────┘      └────────────────┘
```

---

## Recommended Single Source of Truth

### Principle: The Playbook is the canonical system

The **Playbook** (`legal_playbooks` + `clause_standards` + `policy_rules`) is already the most mature system with:
- Versioned playbooks with published snapshots
- Structured clause standards (approved/preferred/fallback/forbidden)
- Structured policy rules with typed effects and conditions
- Evaluation history tracking
- Active connection to the AI pipeline via `PlaybookContextProvider`

### What to Do With Each System

| System | Recommendation | Rationale |
|--------|---------------|-----------|
| **Playbook** (`clause_standards` + `policy_rules`) | ✅ **KEEP as canonical source** | Most mature, versioned, already connected to AI pipeline |
| **Policy Packs** (`policy_packs`) | ➡️ **DEPRECATE** — migrate data to Playbook | `rule_overrides` → `policy_rules`, `clause_overrides` → `clause_standards`, `threshold_overrides` → `policy_rules` with `rule_type=risk_threshold` |
| **Compliance Packs** (`compliance_packs`) | ➡️ **MERGE** into Playbook | `regulations` → new `clause_standards` field or new `compliance_regulations` table linked to playbook; `required/forbidden_clause_categories` → `policy_rules` |
| **Policy Engine** (`AIPolicyEngine`) | ✅ **KEEP separate** | Different concern: pre-execution governance (feature flags, model allowlist, PII). Not clause guidance. |
| **Scoring Overrides** (`scoring_overrides`) | ✅ **KEEP separate** | Different concern: risk scoring math, not clause language or policy rules |

### Migration Path

```
Phase 1: Policy Packs → Playbook
  - Map PolicyPackRuleOverride → PolicyRule (rule_type=deviation or custom)
  - Map PolicyPackClauseOverride → ClauseStandard (clause_type=approved)
  - Map PolicyPackThresholdOverride → PolicyRule (rule_type=risk_threshold)
  - Add `policy_packs.pack_id` as `source_policy_pack_id` on migrated records for traceability
  
Phase 2: Compliance Packs → Playbook
  - Add `regulations` JSONB column to `clause_standards` (or new `compliance_regulations` table)
  - Map `required_clause_categories` → `PolicyRule(effect=require_mandatory_clause)`
  - Map `forbidden_clause_categories` → `PolicyRule(effect=block)`
  - Map `jurisdiction_rules` → `PolicyRule` with `applicable_jurisdictions`

Phase 3: Connect TenantConfigContextProvider to Playbook
  - Instead of reading policy_packs/compliance_packs directly,
    TenantConfigContextProvider reads from playbook tables
  - The Settings UI still writes to policy_packs/compliance_packs (legacy)
    but the AI pipeline reads from playbook (canonical)
```

### Future State Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │           Tenant Settings UI                │
                    │  (writes to legacy tables for now)          │
                    └──────┬──────┬──────┬──────┬──────┬─────────┘
                           │      │      │      │      │
              ┌────────────┘      │      │      │      └────────────┐
              ▼                   ▼      ▼      ▼                   ▼
     ┌────────────────┐   ┌──────────┐ ┌────┐ ┌──────────┐  ┌──────────────┐
     │ feature_flag   │   │ policy   │ │scor│ │compliance│  │ tenant       │
     │ _overrides     │   │ _packs   │ │_over│ │_packs    │  │ _settings    │
     │ (table)        │   │ (legacy) │ │rides│ │ (legacy) │  │ (table)      │
     └────────┬───────┘   └────┬─────┘ └──┬──┘ └────┬─────┘  └──────┬───────┘
              │                │          │         │               │
              │         ┌──────┘          │         └──────┐        │
              │         ▼                  ▼                ▼        │
              │   ┌──────────────────────────────────────────┐       │
              │   │         Playbook (CANONICAL)             │       │
              │   │  ┌─────────────┐  ┌──────────────────┐   │       │
              │   │  │ clause      │  │ policy_rules     │   │       │
              │   │  │ _standards  │  │ (structured,     │   │       │
              │   │  │ (versioned) │  │  versioned,      │   │       │
              │   │  │             │  │  with eval history│   │       │
              │   │  └─────────────┘  └──────────────────┘   │       │
              │   └──────────────────────────────────────────┘       │
              │                │          │                          │
              ▼                ▼          ▼                          ▼
     ┌────────────────┐   ┌──────────────────────┐           ┌──────────────┐
     │ AIPolicyEngine │   │ PlaybookContextProvider│          │ TenantConfig │
     │ (feature flags)│   │ (reads clause_standards│          │ Context      │
     └────────────────┘   │  + policy_rules)       │          │ Provider     │
                          └──────────┬─────────────┘          │ (reads       │
                                     │                        │  scoring +   │
                                     ▼                        │  settings)   │
                            ┌────────────────┐                └──────────────┘
                            │  AI Analysis   │
                            │  Pipeline      │
                            │  (service.py)  │
                            └────────────────┘
```

---

## Summary

| System | Current State | Recommended State | Effort |
|--------|--------------|-------------------|--------|
| **Playbook** (`clause_standards` + `policy_rules`) | ✅ Canonical, connected | ✅ Keep as-is | — |
| **Policy Packs** (`policy_packs`) | ❌ Disconnected, overlapping | ➡️ Deprecate, migrate to Playbook | Medium |
| **Compliance Packs** (`compliance_packs`) | ❌ Disconnected, partially overlapping | ➡️ Merge regulations into Playbook | Medium |
| **Scoring Overrides** (`scoring_overrides`) | ❌ Disconnected, unique | ✅ Keep separate, connect to risk calculation | Small |
| **Policy Engine** (`AIPolicyEngine`) | ✅ Connected, unique | ✅ Keep separate | — |

**Key insight**: The Playbook already has the infrastructure for versioned clause standards and policy rules. Policy Packs and Compliance Packs are simpler, unversioned duplicates of Playbook concepts. Rather than building a new integration layer for each, the correct long-term approach is to **deprecate Policy Packs and Compliance Packs in favor of the Playbook**, and build the `TenantConfigContextProvider` to read from the Playbook.
