# Sprint 24 Task 3.0 — AI Configuration Consumption Layer: Design & Implementation Plan

**Date**: 2026-06-05  
**Objective**: Design the missing integration layer between Tenant Configuration and the AI Analysis Pipeline  
**Status**: Design only — no code written

---

## Current State

```
Tenant Configuration (storage layer)          AI Pipeline (execution layer)
══════════════════════════════════             ════════════════════════════

Feature Flag Overrides ──✅──→ AIPolicyEngine.validate()
  (feature_flag_overrides)       (binary on/off only)

Policy Packs ─────────────────── ❌ (never read)
  (policy_packs)

Scoring Overrides ────────────── ❌ (never read)
  (scoring_overrides)

Compliance Packs ─────────────── ❌ (never read)
  (compliance_packs)

Tenant Settings ──────────────── ❌ (never read)
  (tenant_settings)
```

---

## Phase 1 — Architecture Design

### 1.1 Policy Packs → AI Pipeline Integration

**Goal**: Inject policy pack rule overrides, threshold overrides, and clause overrides into the AI prompt and post-processing.

```
PolicyPackService.get_active_packs(tenant_id)
  │
  ├── rule_overrides ──→ Risk Analysis Prompt (inject as "company policy rules")
  │                        File: ai/service.py → _build_risk_analysis_request()
  │                        Effect: LLM sees tenant-specific policy rules when evaluating clauses
  │
  ├── threshold_overrides ──→ Risk Score Calculation (override severity thresholds)
  │                             File: ai/service.py → _build_analysis_result()
  │                             Effect: Custom risk thresholds per clause type
  │
  └── clause_overrides ──→ Redline Generation (inject preferred clause language)
                             File: ai/service.py → _generate_redlines()
                             Effect: Tenant-specific clause language alongside Playbook context
```

**Integration Point**: `AIService._build_risk_analysis_request()`  
**New Dependency**: `PolicyPackService` injected into `AIService.__init__()`  
**Prompt Variable**: `{{ policy_context }}` added to `risk_analysis` template

#### Prompt Injection: Policy Context

```
COMPANY POLICY RULES:
- Liability cap must not exceed [X] (from rule_overrides)
- Indemnification must cover [Y] (from rule_overrides)
- Governing law must be [Z] (from rule_overrides)

THRESHOLD OVERRIDES:
- Clause type "indemnification": severity threshold = critical (from threshold_overrides)
- Clause type "liability": severity threshold = high (from threshold_overrides)
```

### 1.2 Scoring Overrides → Risk Calculation

**Goal**: Replace hardcoded severity→confidence mapping with tenant-specific scoring overrides.

```
ScoringOverrideService.get_overrides(tenant_id)
  │
  ├── override_severity ──→ Finding severity assignment
  │                           File: ai/service.py → _build_analysis_result()
  │                           Logic: Override severity for specific clause types
  │
  ├── override_risk_weight ──→ Risk contribution per clause type
  │                              File: ai/service.py → _build_analysis_result()
  │                              Logic: Weight each finding's contribution to overall risk
  │
  └── override_risk_score ──→ Base risk score per clause type
                                File: ai/service.py → _build_analysis_result()
                                Logic: Override the LLM's risk_score with tenant-specific baseline
```

**Integration Point**: `AIService._build_analysis_result()`  
**New Dependency**: `ScoringOverrideService` injected into `AIService.__init__()`  
**Current Code**: Lines 920-960 use hardcoded `conf_map = {"critical": 0.95, "high": 0.85, ...}`

#### Scoring Algorithm (After Integration)

```
For each finding:
  base_score = LLM risk_score (0.0-1.0)
  
  # Check for tenant override
  override = scoring_overrides.get(clause_type)
  if override:
      if override.override_risk_score is not None:
          base_score = override.override_risk_score
      if override.override_risk_weight is not None:
          contribution_weight = override.override_risk_weight
      if override.override_severity is not None:
          severity = override.override_severity
  
  overall_risk = weighted_average(all_findings, weights=contribution_weights)
```

### 1.3 Compliance Packs → AI Pipeline

**Goal**: Inject regional compliance requirements into AI prompts.

```
CompliancePackService.get_packs(tenant_id, region)
  │
  ├── regulations ──→ Risk Analysis Prompt (inject as "compliance requirements")
  │                      File: ai/service.py → _build_risk_analysis_request()
  │                      Effect: LLM checks contract against specific regulations
  │
  ├── required_clause_categories ──→ Findings validation
  │                                     File: ai/service.py → post_analysis validation
  │                                     Effect: Flag missing required clauses
  │
  └── forbidden_clause_categories ──→ Findings validation
                                        File: ai/service.py → post_analysis validation
                                        Effect: Flag forbidden clauses
```

**Integration Point**: `AIService._build_risk_analysis_request()` + new `_validate_compliance()` method  
**New Dependency**: `CompliancePackService` injected into `AIService.__init__()`  
**Prompt Variable**: `{{ compliance_context }}` added to `risk_analysis` template

#### Prompt Injection: Compliance Context

```
COMPLIANCE REQUIREMENTS (Jurisdiction: US_FEDERAL):
- Must comply with GDPR Article 5 (data_privacy)
- Must comply with CCPA (data_privacy)
- Required clauses: data_protection, breach_notification
- Forbidden clauses: unlimited_data_usage
```

### 1.4 Tenant Settings → AI Configuration

**Goal**: Use tenant-specific AI model, temperature, and token limits instead of app-level defaults.

```
TenantSettingsService.get_settings(tenant_id)
  │
  ├── ai_model ──→ LLMRequest.model
  │                   File: ai/service.py → _build_risk_analysis_request()
  │                   File: ai/service.py → _generate_redlines()
  │
  ├── ai_temperature ──→ LLMRequest.temperature
  │                        File: ai/service.py → _build_risk_analysis_request()
  │
  └── ai_max_tokens ──→ LLMRequest.max_tokens
                          File: ai/service.py → _build_risk_analysis_request()
```

**Integration Point**: `AIService._build_risk_analysis_request()`  
**New Dependency**: Direct SQL query on `tenant_settings` table (no service class exists for reads)  
**Fallback**: App-level `settings` config if tenant settings are null

---

## Phase 2 — Data Flow Mapping

### Policy Packs

| Layer | Component | File | Method | Status |
|-------|-----------|------|--------|--------|
| **Table** | `policy_packs` | — | — | ✅ Exists |
| **Repository** | `TenantConfigRepository` (inline SQL) | `tenant_config/service.py` | `list_packs()` | ✅ Exists |
| **Service** | `PolicyPackService` | `tenant_config/service.py` | `list_packs()`, `get_pack()` | ✅ Exists |
| **API** | `tenant_config/router.py` | `router.py` | `GET /policy-packs` | ✅ Exists |
| **AI Consumer** | **MISSING** | `ai/service.py` | `_build_risk_analysis_request()` | ❌ **Needs creation** |

### Scoring Overrides

| Layer | Component | File | Method | Status |
|-------|-----------|------|--------|--------|
| **Table** | `scoring_overrides` | — | — | ✅ Exists |
| **Repository** | `TenantConfigRepository` (inline SQL) | `tenant_config/service.py` | `list_overrides()` | ✅ Exists |
| **Service** | `ScoringOverrideService` | `tenant_config/service.py` | `list_overrides()` | ✅ Exists |
| **API** | `tenant_config/router.py` | `router.py` | `GET /scoring-overrides` | ✅ Exists |
| **AI Consumer** | **MISSING** | `ai/service.py` | `_build_analysis_result()` | ❌ **Needs creation** |

### Compliance Packs

| Layer | Component | File | Method | Status |
|-------|-----------|------|--------|--------|
| **Table** | `compliance_packs` | — | — | ✅ Exists |
| **Repository** | `TenantConfigRepository` (inline SQL) | `tenant_config/service.py` | `list_packs()` | ✅ Exists |
| **Service** | `CompliancePackService` | `tenant_config/service.py` | `list_packs()` | ✅ Exists |
| **API** | `tenant_config/router.py` | `router.py` | `GET /compliance-packs` | ✅ Exists |
| **AI Consumer** | **MISSING** | `ai/service.py` | `_build_risk_analysis_request()` | ❌ **Needs creation** |

### Tenant Settings

| Layer | Component | File | Method | Status |
|-------|-----------|------|--------|--------|
| **Table** | `tenant_settings` | — | — | ✅ Exists |
| **Repository** | `AdminRepository` | `admin/repository.py` | `get_settings()` | ✅ Exists |
| **Service** | `AdminService` | `admin/service.py` | `get_settings()` | ✅ Exists |
| **API** | `admin/router.py` | `admin/router.py` | `GET /admin/settings` | ✅ Exists |
| **AI Consumer** | **MISSING** | `ai/service.py` | `_build_risk_analysis_request()` | ❌ **Needs creation** |

---

## Phase 3 — Implementation Plan

### 3.1 Files to Modify

| # | File | Changes | Risk |
|---|------|---------|------|
| 1 | `backend/app/domains/ai/service.py` | Inject tenant config into `_build_risk_analysis_request()`, `_build_analysis_result()`, `_generate_redlines()` | Medium |
| 2 | `backend/app/domains/ai/prompts/__init__.py` | Add `{{ policy_context }}` and `{{ compliance_context }}` to `risk_analysis` template | Low |
| 3 | `backend/app/domains/ai/policy.py` | Extend `AIPolicyContext` with policy pack and compliance references | Low |

### 3.2 Files to Create

| # | File | Purpose | Risk |
|---|------|---------|------|
| 1 | `backend/app/domains/tenant_config/context_provider.py` | Unified provider that fetches all tenant config for AI pipeline injection | Medium |

### 3.3 New Service: `TenantConfigContextProvider`

```python
class TenantConfigContextProvider:
    """Fetches all tenant configuration for AI pipeline injection.
    
    Combines Policy Packs, Scoring Overrides, Compliance Packs,
    and Tenant Settings into a unified context object.
    """
    
    def __init__(self, session, tenant_id):
        self.session = session
        self.tenant_id = tenant_id
    
    async def get_policy_context(self) -> PolicyContext:
        """Fetch active policy packs and merge their rule/threshold/clause overrides."""
        # Query policy_packs WHERE tenant_id AND is_active = true
        # Merge all rule_overrides, threshold_overrides, clause_overrides
        # Return PolicyContext(rule_overrides=[...], threshold_overrides=[...], clause_overrides=[...])
    
    async def get_scoring_context(self) -> ScoringContext:
        """Fetch scoring overrides for risk calculation."""
        # Query scoring_overrides WHERE tenant_id
        # Return ScoringContext(overrides={clause_type: {...}})
    
    async def get_compliance_context(self, region: str) -> ComplianceContext:
        """Fetch compliance packs for a region."""
        # Query compliance_packs WHERE tenant_id AND region
        # Return ComplianceContext(regulations=[...], required=[...], forbidden=[...])
    
    async def get_ai_settings(self) -> AISettings:
        """Fetch tenant-specific AI model settings."""
        # Query tenant_settings WHERE tenant_id
        # Return AISettings(model, temperature, max_tokens) or defaults from app.settings
```

### 3.4 Dependency Order

```
Phase 3a: TenantConfigContextProvider (new service)
  └─ No dependencies — pure data fetcher
  └─ Effort: 2-3 hours

Phase 3b: Tenant Settings → AI Configuration
  └─ Depends on: 3a
  └─ Modify: AIService._build_risk_analysis_request()
  └─ Effort: 1 hour

Phase 3c: Policy Packs → AI Prompts
  └─ Depends on: 3a
  └─ Modify: AIService._build_risk_analysis_request(), prompt template
  └─ Effort: 2-3 hours

Phase 3d: Scoring Overrides → Risk Calculation
  └─ Depends on: 3a
  └─ Modify: AIService._build_analysis_result()
  └─ Effort: 2-3 hours

Phase 3e: Compliance Packs → AI Prompts
  └─ Depends on: 3a
  └─ Modify: AIService._build_risk_analysis_request(), prompt template, new validation method
  └─ Effort: 2-3 hours
```

### 3.5 Migration Requirements

**None.** All configuration data already exists in the database. No schema changes needed. The integration is purely about reading existing data and passing it to the AI pipeline.

---

## Phase 4 — Validation Strategy

### 4.1 How to Prove Tenant A ≠ Tenant B

```
Setup:
  1. Create Tenant A with Strict Policy Pack
  2. Create Tenant B with Relaxed Policy Pack
  3. Upload SAME contract to both tenants
  4. Run AI analysis for both

Expected:
  Tenant A (Strict):
    - More findings (lower tolerance)
    - Higher risk scores
    - More redlines (stricter clause requirements)
    - More "critical" severity findings
  
  Tenant B (Relaxed):
    - Fewer findings (higher tolerance)
    - Lower risk scores
    - Fewer redlines
    - Fewer "critical" findings
```

### 4.2 Test Contract

Use a contract with known issues (e.g., unlimited liability clause, missing indemnification):

```
Contract: "MSA with unlimited liability and no data privacy clause"
Expected from Strict Pack:
  - Finding: "Unlimited liability" → severity=critical, risk_score=0.95
  - Finding: "Missing data privacy clause" → severity=high, risk_score=0.80
  - Finding: "No GDPR compliance" → severity=critical, risk_score=0.90
  - Redline: Add liability cap of $1M
  - Redline: Add data privacy clause (GDPR-compliant)

Expected from Relaxed Pack:
  - Finding: "Unlimited liability" → severity=medium, risk_score=0.50
  - Finding: "Missing data privacy clause" → NOT flagged (not required)
  - Redline: None (acceptable risk)
```

### 4.3 Validation Metrics

| Metric | Tenant A (Strict) | Tenant B (Relaxed) | Expected Difference |
|--------|-------------------|-------------------|-------------------|
| Total findings | Higher | Lower | ≥ 2x |
| Critical findings | More | Fewer | ≥ 3x |
| Average risk score | Higher | Lower | ≥ 0.2 |
| Redlines generated | More | Fewer | ≥ 2x |
| Risk level | Higher | Lower | At least 1 level |

### 4.4 Automated Validation Script

A Python script that:
1. Creates two tenant contexts
2. Uploads the same contract
3. Waits for analysis completion
4. Compares findings, scores, redlines
5. Reports PASS/FAIL for each metric

---

## Effort Summary

| Phase | Description | Effort | Risk |
|-------|-------------|--------|------|
| 3a | TenantConfigContextProvider | 2-3h | Low |
| 3b | Tenant Settings → AI Config | 1h | Low |
| 3c | Policy Packs → AI Prompts | 2-3h | Medium |
| 3d | Scoring Overrides → Risk Calc | 2-3h | Medium |
| 3e | Compliance Packs → AI Prompts | 2-3h | Medium |
| **Total** | | **~10-13h** | |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Policy pack data is complex JSONB — parsing errors | Medium | Medium | Add validation + fallback to empty context |
| Scoring overrides change risk profile unexpectedly | Medium | High | A/B test with known contract before production |
| Compliance packs increase prompt size beyond token limits | Low | Medium | Limit to 5 most relevant regulations |
| Tenant settings override breaks model compatibility | Low | High | Validate model name against allowed list |
| Feature flag evaluation conflicts with new config | Low | Low | Feature gates run before config injection |

---

## Success Criteria

The integration is complete when:

1. **Policy Packs**: Two tenants with different packs produce different findings for the same contract
2. **Scoring Overrides**: Two tenants with different overrides produce different risk scores for the same findings
3. **Compliance Packs**: Two tenants with different regional packs produce different compliance-related findings
4. **Tenant Settings**: Two tenants with different AI models/temperatures use different LLM configurations
5. **No regressions**: All existing tests pass, existing reviews remain unchanged
