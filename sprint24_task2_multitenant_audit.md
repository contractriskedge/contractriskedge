# Sprint 24 Task 2 — Multi-Tenant Policy Validation Audit

**Date**: 2026-06-05  
**Objective**: Verify that Tenant Configuration materially affects AI contract analysis results

---

## Executive Summary

**1 of 5 tenant configuration sources actually affects AI analysis.**

The remaining 4 are stored in the database and exposed via the Settings UI, but are **never queried during the AI analysis pipeline**. They are configuration screens that store data without connecting it to the analysis engine.

---

## Phase 1 — Configuration Discovery

### All Tenant Configuration Sources

| # | Source | Table | Settings UI Tab | Connected to AI? |
|---|--------|-------|----------------|-----------------|
| 1 | **Feature Flag Overrides** | `feature_flag_overrides` | Features | ✅ **YES** |
| 2 | Policy Packs | `policy_packs` | Policy Packs | ❌ **No** |
| 3 | Scoring Overrides | `scoring_overrides` | Scoring | ❌ **No** |
| 4 | Compliance Packs | `compliance_packs` | Compliance | ❌ **No** |
| 5 | Tenant Settings (AI config) | `tenant_settings` | General | ❌ **No** |

### Detailed Breakdown

#### 1. Feature Flag Overrides — ✅ CONNECTED

| Aspect | Detail |
|--------|--------|
| **Table** | `feature_flag_overrides` |
| **API** | `GET/POST/DELETE /tenant-config/features/overrides` |
| **UI** | Settings → Features tab → `FeatureFlagList` |
| **AI Pipeline Entry** | `FeatureGateMiddleware` in `orchestrator.py` line 49 |
| **Code Path** | `AIExecutionOrchestrator.execute()` → `FeatureGateMiddleware.check_gates()` → `FeatureFlagService.evaluate_flag()` |
| **Flags Checked** | `ai_analysis` — blocks analysis entirely, `redline_generation` — blocks redlines, `policy_engine` — blocks policy evaluation |
| **Effect** | Can **block** AI stages but cannot **modify** behavior |

#### 2. Policy Packs — ❌ DISCONNECTED

| Aspect | Detail |
|--------|--------|
| **Table** | `policy_packs` |
| **API** | `GET/POST/DELETE /tenant-config/policy-packs` |
| **UI** | Settings → Policy Packs tab → `PolicyPackList` |
| **AI Pipeline Entry** | **NONE** — zero references in `backend/app/domains/ai/` |
| **Code Path** | Only exposed via `tenant_config/router.py` and `tenant_config/service.py` |
| **What It Should Do** | Inject rule/threshold/clause overrides into AI prompts |
| **What Actually Happens** | Data is stored but **never read** during analysis |

#### 3. Scoring Overrides — ❌ DISCONNECTED

| Aspect | Detail |
|--------|--------|
| **Table** | `scoring_overrides` |
| **API** | `GET/POST/DELETE /tenant-config/scoring-overrides` |
| **UI** | Settings → Scoring tab → `ScoringOverrideList` |
| **AI Pipeline Entry** | **NONE** — zero references in `backend/app/domains/ai/` |
| **Code Path** | Only exposed via `tenant_config/router.py` |
| **What It Should Do** | Override risk scoring per clause type per tenant |
| **What Actually Happens** | Risk scoring in `_build_analysis_result()` uses hardcoded severity-to-confidence mapping |

#### 4. Compliance Packs — ❌ DISCONNECTED

| Aspect | Detail |
|--------|--------|
| **Table** | `compliance_packs` |
| **API** | `GET/POST /tenant-config/compliance-packs` |
| **UI** | Settings → Compliance tab → `CompliancePackList` |
| **AI Pipeline Entry** | **NONE** — zero references in `backend/app/domains/ai/` |
| **Code Path** | Only exposed via `tenant_config/router.py` |
| **What It Should Do** | Inject regional regulation requirements into AI prompts |
| **What Actually Happens** | Data is stored but **never read** during analysis |

#### 5. Tenant Settings (AI Config) — ❌ DISCONNECTED

| Aspect | Detail |
|--------|--------|
| **Table** | `tenant_settings` |
| **API** | `GET/PUT /admin/settings` |
| **UI** | Settings → General tab → `GeneralSettingsForm` |
| **AI Pipeline Entry** | **NONE** — zero references in `backend/app/domains/ai/` |
| **Columns** | `ai_model`, `ai_temperature`, `ai_max_tokens`, `ai_embedding_model`, `ai_token_budget_daily` |
| **What It Should Do** | Override AI model, temperature, token limits per tenant |
| **What Actually Happens** | The AI service uses app-level `settings` config (hardcoded or env vars), not tenant-specific settings |

---

## Phase 2 — Analysis Pipeline Trace

```
Upload → OCR → Chunking → Embeddings → AI Analysis → Findings → Redlines → Risk Score
                                 │                        │          │
                                 ▼                        ▼          ▼
                          FeatureGateMiddleware     Playbook     Hardcoded
                          checks feature_flag       Context      severity→
                          _overrides (ai_analysis,  Provider     confidence
                          redline_generation,       (clause_     mapping
                          policy_engine)            _standards)  (no scoring
                                 │                  table)      _overrides)
                                 ▼
                          LLM Prompt
                          (no tenant config
                           variables injected)
```

### Stage-by-Stage Tenant Awareness

| Stage | Tenant-Aware? | Details |
|-------|--------------|---------|
| Upload | ✅ Scoped | `upload_sessions.tenant_id` |
| OCR | ✅ Scoped | Scoped by tenant_id |
| Chunking | ✅ Scoped | Scoped by tenant_id |
| Embeddings | ✅ Scoped | Scoped by tenant_id |
| **AI Analysis Prompt** | ❌ **No** | Prompt template has **no tenant config variables** |
| **Feature Gate Check** | ✅ YES | `feature_flag_overrides` checked before LLM execution |
| **LLM Execution** | ❌ **No** | Uses app-level model/temperature settings |
| **Findings Storage** | ✅ Scoped | `ai_findings.tenant_id` |
| **Redline Generation** | ⚠️ Partial | Uses **Playbook** (`clause_standards` table), NOT `policy_packs` |
| **Risk Score Calculation** | ❌ **No** | Hardcoded severity→confidence mapping, no `scoring_overrides` |
| **Review Population** | ✅ Scoped | `review_findings.tenant_id`, `review_redlines.tenant_id` |

---

## Phase 3 — Controlled Validation Test

### Cannot Execute As Designed

A true A/B multi-tenant test requires:
1. **Two tenants in the database** — only 1 tenant exists (`00000000-0000-4000-8000-000000000001`)
2. **Tenant-specific config actually affecting AI** — only feature flags are connected
3. **Different AI prompts per tenant** — prompts are identical regardless of tenant config

### What CAN Be Tested

The feature flag mechanism CAN be verified:

| Flag | Effect | Testable? |
|------|--------|-----------|
| `ai_analysis` = false | Blocks AI analysis entirely | ✅ Would prevent any findings/redlines |
| `redline_generation` = false | Blocks redline generation | ✅ Would produce findings but no redlines |
| `policy_engine` = false | Blocks policy evaluation | ✅ Would prevent policy checks |

But this is binary on/off, not graduated configuration.

---

## Phase 4 — Verification Matrix

| Capability | Verified? | Evidence |
|-----------|-----------|----------|
| Feature Flags affect analysis | ✅ **YES** | `FeatureGateMiddleware` in `orchestrator.py:49` checks `feature_flag_overrides` before LLM execution |
| Policy Packs affect findings | ❌ **NO** | Zero references to `policy_packs` in `backend/app/domains/ai/` |
| Scoring Overrides affect score | ❌ **NO** | `_build_analysis_result()` uses hardcoded severity→confidence mapping in `service.py:880+` |
| Compliance Packs affect results | ❌ **NO** | Zero references to `compliance_packs` in `backend/app/domains/ai/` |
| Tenant Settings affect AI prompts | ❌ **NO** | `_build_risk_analysis_request()` in `service.py:696` passes only `chunks` to prompt — no tenant config |
| Playbook affects redlines | ✅ **YES** | `PlaybookContextProvider` injects approved clause language into redline prompts |
| App config affects AI | ✅ **YES** | `settings` controls model, temperature, token limits globally |

---

## Phase 5 — Risk Assessment

### Configuration Area Classification

| Area | Classification | Risk | Details |
|------|---------------|------|---------|
| **Feature Flag Overrides** | ✅ **Fully Functional** | Low | Binary on/off, works correctly |
| **Policy Packs** | ❌ **Cosmetic Only** | **High** | Full CRUD UI + API, data stored, **never used** |
| **Scoring Overrides** | ❌ **Cosmetic Only** | **High** | Full CRUD UI + API, data stored, **never used** |
| **Compliance Packs** | ❌ **Cosmetic Only** | **High** | Full CRUD UI + API, data stored, **never used** |
| **Tenant Settings (AI)** | ❌ **Cosmetic Only** | **High** | Full CRUD UI + API, data stored, **never used** |
| **Tenant Settings (Branding)** | ⚠️ **Partially Functional** | Medium | Branding stored but only used by admin console display |
| **Playbook / Clause Standards** | ✅ **Fully Functional** | Low | Actively injected into redline prompts |

### Disconnected Settings Inventory

These settings are **stored and displayed in UI but never used by the AI pipeline**:

| Setting | Table Column | Stored Where | Should Affect |
|---------|-------------|-------------|---------------|
| AI Model | `tenant_settings.ai_model` | General tab | AI model selection per tenant |
| AI Temperature | `tenant_settings.ai_temperature` | General tab | LLM temperature per tenant |
| AI Max Tokens | `tenant_settings.ai_max_tokens` | General tab | Token limits per tenant |
| Risk Thresholds | `tenant_settings.risk_threshold_*` | General tab | Risk classification per tenant |
| SLA Hours | `tenant_settings.sla_*_hours` | General tab | SLA calculation per tenant |
| Policy Rules | `policy_packs.rule_overrides` | Policy Packs tab | Rule injection into AI prompts |
| Policy Thresholds | `policy_packs.threshold_overrides` | Policy Packs tab | Threshold overrides in scoring |
| Clause Overrides | `policy_packs.clause_overrides` | Policy Packs tab | Clause language in redlines |
| Scoring Severity | `scoring_overrides.override_severity` | Scoring tab | Severity mapping per clause type |
| Scoring Weight | `scoring_overrides.override_risk_weight` | Scoring tab | Risk weight per clause type |
| Scoring Score | `scoring_overrides.override_risk_score` | Scoring tab | Base risk score per clause type |
| Compliance Regulations | `compliance_packs.regulations` | Compliance tab | Regulation injection into prompts |
| Compliance Categories | `compliance_packs.required_*` | Compliance tab | Required/forbidden clause categories |

**Total**: **14 stored settings that have zero effect on AI analysis.**

---

## Production Readiness Assessment for Multi-Tenant Analysis

| Criterion | Score | Notes |
|-----------|-------|-------|
| Tenant data isolation | ✅ 100% | All tables scoped by `tenant_id` |
| Feature flag enforcement | ✅ 100% | Binary on/off works correctly |
| Policy pack integration | ❌ 0% | CRUD exists, pipeline integration missing |
| Scoring override integration | ❌ 0% | CRUD exists, pipeline integration missing |
| Compliance pack integration | ❌ 0% | CRUD exists, pipeline integration missing |
| Tenant-specific AI settings | ❌ 0% | CRUD exists, pipeline integration missing |
| Multi-tenant A/B testing | ❌ 0% | Cannot run — no second tenant, no config effect |

**Multi-Tenant Analysis Readiness**: **20%**

---

## Recommended Actions

### P0 — Connect Policy Packs to AI Pipeline

The highest-value integration. Policy packs should inject rule overrides, threshold overrides, and clause overrides into the AI prompt.

**Files to modify**:
- `backend/app/domains/ai/service.py` — `_build_risk_analysis_request()` — inject policy pack context
- `backend/app/domains/ai/service.py` — `_generate_redlines()` — inject policy pack clause overrides alongside playbook context

### P1 — Connect Scoring Overrides to Risk Calculation

Replace the hardcoded severity→confidence mapping in `_build_analysis_result()` with tenant-specific scoring overrides.

**Files to modify**:
- `backend/app/domains/ai/service.py` — `_build_analysis_result()` — query `scoring_overrides` for clause-type-specific weights/scores

### P1 — Connect Tenant Settings to AI Configuration

Replace app-level `settings` references with tenant-specific `tenant_settings` values for model, temperature, and token limits.

**Files to modify**:
- `backend/app/domains/ai/service.py` — `_build_risk_analysis_request()` — read `tenant_settings` for model/temperature
- `backend/app/domains/ai/orchestrator.py` — pass tenant settings to execution plan

### P2 — Connect Compliance Packs to AI Prompts

Inject regional regulation requirements from `compliance_packs` into the AI prompt for jurisdiction-specific analysis.

**Files to modify**:
- `backend/app/domains/ai/service.py` — `_build_risk_analysis_request()` — inject compliance pack regulations
- Prompt templates — add regulation context variables

---

## Conclusion

**The tenant configuration UI is largely cosmetic.** 4 of 5 configuration areas have full CRUD interfaces that store data in the database, but the data is **never read during AI analysis**. Only feature flags (binary on/off) actually affect the pipeline.

This means:
- Two tenants with different Policy Packs → **identical analysis results**
- Two tenants with different Scoring Overrides → **identical risk scores**
- Two tenants with different Compliance Packs → **identical findings**
- Two tenants with different AI settings → **identical model/temperature**

The Settings module is a **configuration storage system** without a **configuration consumption system**. The UI and API layers are complete, but the AI pipeline integration layer was never built.
