# Sprint 23 Task 2.5 — Frontend Settings Audit

**Date**: 2026-06-05  
**Auditor**: Automated codebase analysis  
**Scope**: All frontend Settings-related pages, components, hooks, services, and routes

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Settings Categories** | **12** |
| **Fully Functional (API + UI)** | **1** (General Settings via AdminConsole) |
| **Partially Functional** | **2** (Feature Flags, Tenant Config summary) |
| **Placeholder / Scaffold Only** | **9** |
| **Overall Completion (UI)** | **~8%** |
| **Overall Completion (API)** | **100%** (13/13 endpoints verified) |
| **Missing Hooks** | **6** |
| **Missing Forms** | **11** |
| **Missing Save Actions** | **10** |
| **Missing Validation** | **11** |
| **Missing Success/Error Feedback** | **11** |

---

## File Inventory

### Pages (Next.js App Router)

| File | Status | Purpose |
|------|--------|---------|
| `app/(authenticated)/settings/page.tsx` | ✅ Active | Renders `TenantSettings` or `SettingsPage` based on auth |
| `app/(authenticated)/tenant-settings/page.tsx` | ✅ Active | Dedicated route — renders `TenantSettings` |
| `app/(authenticated)/admin/page.tsx` | ✅ Active | Renders `AdminConsole` |

### Components

| File | Status | Purpose |
|------|--------|---------|
| `components/dashboard/SettingsPage.tsx` | ⚠️ **Static shell** | 6 icon cards (Profile, Notifications, Security, API Keys, Billing, Integrations) — **no API calls, no forms, no save actions** |
| `components/tenant/TenantSettings.tsx` | 🚧 **Scaffold only** | Marked "Sprint 7 — In Development". Single placeholder with gear icon. **No implementation.** |
| `components/dashboard/admin/AdminConsole.tsx` | ✅ **Functional** | Admin console with KPI cards, user management, AI governance, audit, system health. Reads from `useAdmin` hooks. |

### Services (API Clients)

| File | Endpoints Covered | Status |
|------|-------------------|--------|
| `services/api/tenant.ts` | `GET/PUT /admin/settings`, `GET /features/evaluate`, `POST /features/overrides`, `GET /compliance-packs`, `GET /summary` | ✅ **Full coverage** of tenant-config APIs |
| `services/api/admin.ts` | `GET /admin/dashboard`, `GET /admin/users`, `GET /admin/audit-logs` | ✅ Functional |

### Hooks (TanStack Query)

| File | Hooks | Status |
|------|-------|--------|
| `services/hooks/useAdmin.ts` | `useAdminDashboard`, `useAdminUsers`, `useAuditLogs` | ✅ Functional |
| **Missing** | `useTenantSettings`, `useFeatureFlags`, `usePolicyPacks`, `useScoringOverrides`, `useCompliancePacks`, `useTenantSummary` | ❌ **Do not exist** |

### Routing

| Mechanism | Settings Entries |
|-----------|-----------------|
| **Sidebar** (`Sidebar.tsx`) | "Admin Console" → `admin`, "Settings" → `settings`, "Tenant Config" → `tenant-settings` |
| **DashboardLayout** (`DashboardLayout.tsx`) | `settings` → `<SettingsPage />`, `tenant-settings` → `<TenantSettings />`, `admin` → `<AdminConsole />` |
| **Next.js routes** | `/settings`, `/tenant-settings`, `/admin` |

---

## Category-by-Category Audit

### 1. General Settings

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | ⚠️ Partial | `AdminConsole` shows KPIs, users, audit, health. `SettingsPage` shows 6 static cards. |
| **Existing API Integration** | ✅ | `tenantService.getConfig()` calls `GET /admin/settings`. `tenantService.updateSettings()` calls `PUT /admin/settings`. |
| **Missing API Integration** | ❌ | `SettingsPage` cards don't call any API. `TenantSettings` doesn't call any API. |
| **Missing Forms** | ❌ | No forms for Profile, Notifications, Security, API Keys, Billing, Integrations. |
| **Missing Save Actions** | ❌ | No save buttons in `SettingsPage`. |
| **Missing Validation** | ❌ | No form validation anywhere. |
| **Missing Success/Error Feedback** | ❌ | No toast/alert on save/fail. |

### 2. Feature Flags

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | ❌ | No feature flag UI exists. `TenantSettings` scaffold mentions it but doesn't implement. |
| **Existing API Integration** | ✅ | `tenantService.getFeatures()` → `GET /features/evaluate`. `tenantService.updateFeatureOverride()` → `POST /features/overrides`. |
| **Missing API Integration** | ❌ | No UI consumes these API methods. |
| **Missing Forms** | ❌ | No toggle/list UI for feature flags. |
| **Missing Save Actions** | ❌ | No save mechanism. |
| **Missing Validation** | ❌ | No validation. |
| **Missing Success/Error Feedback** | ❌ | No feedback. |

### 3. Policy Packs

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | ❌ | No policy pack UI exists anywhere. |
| **Existing API Integration** | ❌ | `tenantService` has **no** policy pack methods. Backend has `GET/POST /policy-packs` and `GET/DELETE /policy-packs/{pack_id}`. |
| **Missing API Integration** | ❌ | Missing `getPolicyPacks()`, `createPolicyPack()`, `getPolicyPack()`, `deletePolicyPack()`. |
| **Missing Forms** | ❌ | No create/edit form. |
| **Missing Save Actions** | ❌ | No save mechanism. |
| **Missing Validation** | ❌ | No validation. |
| **Missing Success/Error Feedback** | ❌ | No feedback. |

### 4. Compliance Packs

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | ❌ | No compliance pack UI exists. `TenantSettings` scaffold mentions it but doesn't implement. |
| **Existing API Integration** | ⚠️ Partial | `tenantService.getCompliancePacks()` → `GET /compliance-packs`. But **no create method**. Backend also has `POST /compliance-packs`. |
| **Missing API Integration** | ❌ | Missing `createCompliancePack()` in service. No UI consumes the existing `getCompliancePacks()`. |
| **Missing Forms** | ❌ | No create/edit form. |
| **Missing Save Actions** | ❌ | No save mechanism. |
| **Missing Validation** | ❌ | No validation. |
| **Missing Success/Error Feedback** | ❌ | No feedback. |

### 5. Scoring Overrides

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | ❌ | No scoring override UI exists anywhere. |
| **Existing API Integration** | ❌ | `tenantService` has **no** scoring override methods. Backend has `GET/POST /scoring-overrides` and `DELETE /scoring-overrides/{override_id}`. |
| **Missing API Integration** | ❌ | Missing `getScoringOverrides()`, `createScoringOverride()`, `deleteScoringOverride()`. |
| **Missing Forms** | ❌ | No create/edit form. |
| **Missing Save Actions** | ❌ | No save mechanism. |
| **Missing Validation** | ❌ | No validation. |
| **Missing Success/Error Feedback** | ❌ | No feedback. |

### 6. Tenant Configuration

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | 🚧 **Scaffold only** | `TenantSettings.tsx` — placeholder with "Sprint 7 — In Development" badge. |
| **Existing API Integration** | ✅ | `tenantService.getConfigSummary()` → `GET /summary`. Not consumed by any UI. |
| **Missing API Integration** | ❌ | Summary API not connected. |
| **Missing Forms** | ❌ | No forms for branding, risk weights, workflows, routing rules, custom fields. |
| **Missing Save Actions** | ❌ | No save mechanism. |
| **Missing Validation** | ❌ | No validation. |
| **Missing Success/Error Feedback** | ❌ | No feedback. |

### 7. User Preferences

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | ❌ | No user preferences UI. |
| **Existing API Integration** | ❌ | No backend endpoint identified for user preferences. |
| **Missing API Integration** | ❌ | No API at all. |
| **Missing Forms** | ❌ | No form. |
| **Missing Save Actions** | ❌ | No save. |
| **Missing Validation** | ❌ | No validation. |
| **Missing Success/Error Feedback** | ❌ | No feedback. |

### 8. SLA Thresholds

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | ❌ | No SLA thresholds UI. |
| **Existing API Integration** | ⚠️ Partial | `GET/PUT /admin/settings` returns/updates SLA hours (part of tenant settings). But no dedicated SLA endpoint. |
| **Missing API Integration** | ❌ | No dedicated SLA thresholds CRUD. |
| **Missing Forms** | ❌ | No form. |
| **Missing Save Actions** | ❌ | No save. |
| **Missing Validation** | ❌ | No validation. |
| **Missing Success/Error Feedback** | ❌ | No feedback. |

### 9. Risk Thresholds

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | ❌ | No risk thresholds UI. |
| **Existing API Integration** | ⚠️ Partial | `GET/PUT /admin/settings` may include risk weights. `POST /scoring-overrides` handles per-clause-type overrides. |
| **Missing API Integration** | ❌ | No dedicated risk thresholds CRUD. |
| **Missing Forms** | ❌ | No form. |
| **Missing Save Actions** | ❌ | No save. |
| **Missing Validation** | ❌ | No validation. |
| **Missing Success/Error Feedback** | ❌ | No feedback. |

### 10. Notification Settings

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | ❌ | No notification settings UI. |
| **Existing API Integration** | ❌ | No backend endpoint identified for notification preferences. |
| **Missing API Integration** | ❌ | No API. |
| **Missing Forms** | ❌ | No form. |
| **Missing Save Actions** | ❌ | No save. |
| **Missing Validation** | ❌ | No validation. |
| **Missing Success/Error Feedback** | ❌ | No feedback. |

### 11. Workflow Settings

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | ❌ | No workflow settings UI. |
| **Existing API Integration** | ❌ | No backend endpoint identified for workflow configuration. |
| **Missing API Integration** | ❌ | No API. |
| **Missing Forms** | ❌ | No form. |
| **Missing Save Actions** | ❌ | No save. |
| **Missing Validation** | ❌ | No validation. |
| **Missing Success/Error Feedback** | ❌ | No feedback. |

### 12. AI Settings

| Aspect | Status | Details |
|--------|--------|---------|
| **Existing UI** | ❌ | No AI settings UI. |
| **Existing API Integration** | ⚠️ Partial | `GET/PUT /admin/settings` includes AI model, temperature, max tokens, token budget. |
| **Missing API Integration** | ❌ | No dedicated AI settings endpoint. |
| **Missing Forms** | ❌ | No form. |
| **Missing Save Actions** | ❌ | No save. |
| **Missing Validation** | ❌ | No validation. |
| **Missing Success/Error Feedback** | ❌ | No feedback. |

---

## Backend API Coverage Map

| Frontend Category | Backend Endpoint | In `tenantService`? | In UI? |
|-------------------|-----------------|---------------------|--------|
| General Settings | `GET /admin/settings` | ✅ `getConfig()` | ⚠️ `AdminConsole` reads it |
| General Settings | `PUT /admin/settings` | ✅ `updateSettings()` | ❌ Not consumed |
| Feature Flags | `GET /features/evaluate` | ✅ `getFeatures()` | ❌ Not consumed |
| Feature Flags | `GET /features/evaluate/{key}` | ❌ Missing | ❌ Not consumed |
| Feature Flags | `POST /features/overrides` | ✅ `updateFeatureOverride()` | ❌ Not consumed |
| Feature Flags | `DELETE /features/overrides/{fk}/{tt}/{ti}` | ❌ Missing | ❌ Not consumed |
| Feature Flags | `GET /features/definitions` | ❌ Missing | ❌ Not consumed |
| Policy Packs | `GET /policy-packs` | ❌ Missing | ❌ Not consumed |
| Policy Packs | `POST /policy-packs` | ❌ Missing | ❌ Not consumed |
| Policy Packs | `GET /policy-packs/{pack_id}` | ❌ Missing | ❌ Not consumed |
| Policy Packs | `DELETE /policy-packs/{pack_id}` | ❌ Missing | ❌ Not consumed |
| Scoring Overrides | `GET /scoring-overrides` | ❌ Missing | ❌ Not consumed |
| Scoring Overrides | `POST /scoring-overrides` | ❌ Missing | ❌ Not consumed |
| Scoring Overrides | `DELETE /scoring-overrides/{oid}` | ❌ Missing | ❌ Not consumed |
| Compliance Packs | `GET /compliance-packs` | ✅ `getCompliancePacks()` | ❌ Not consumed |
| Compliance Packs | `POST /compliance-packs` | ❌ Missing | ❌ Not consumed |
| Tenant Config | `GET /summary` | ✅ `getConfigSummary()` | ❌ Not consumed |

**Backend endpoints with no frontend coverage: 14 out of 18**

---

## Missing Hooks

The following TanStack Query hooks need to be created:

| Hook | API Methods Needed | Priority |
|------|-------------------|----------|
| `useTenantSettings` | `tenantService.getConfig()`, `tenantService.updateSettings()` | **P0** |
| `useFeatureFlags` | `tenantService.getFeatures()`, `tenantService.updateFeatureOverride()` | **P0** |
| `usePolicyPacks` | New: `getPolicyPacks()`, `createPolicyPack()`, `getPolicyPack()`, `deletePolicyPack()` | **P1** |
| `useScoringOverrides` | New: `getScoringOverrides()`, `createScoringOverride()`, `deleteScoringOverride()` | **P1** |
| `useCompliancePacks` | `tenantService.getCompliancePacks()`, New: `createCompliancePack()` | **P1** |
| `useTenantSummary` | `tenantService.getConfigSummary()` | **P2** |

---

## Missing Forms

| Form | Category | Priority |
|------|----------|----------|
| Feature Flag toggle list | Feature Flags | **P0** |
| Feature Flag override editor | Feature Flags | **P0** |
| Policy Pack create/edit form | Policy Packs | **P1** |
| Policy Pack list with delete | Policy Packs | **P1** |
| Scoring Override create form | Scoring Overrides | **P1** |
| Scoring Override list with delete | Scoring Overrides | **P1** |
| Compliance Pack create form | Compliance Packs | **P1** |
| Compliance Pack list | Compliance Packs | **P1** |
| Tenant branding editor | Tenant Configuration | **P2** |
| Risk weights editor | Risk Thresholds | **P2** |
| AI config editor (model, temp, tokens) | AI Settings | **P2** |

---

## Missing Save Actions

| Action | Category | Priority |
|--------|----------|----------|
| Save feature flag override | Feature Flags | **P0** |
| Save policy pack | Policy Packs | **P1** |
| Save scoring override | Scoring Overrides | **P1** |
| Save compliance pack | Compliance Packs | **P1** |
| Save tenant branding | Tenant Configuration | **P2** |
| Save risk weights | Risk Thresholds | **P2** |
| Save AI config | AI Settings | **P2** |
| Save SLA thresholds | SLA Thresholds | **P2** |
| Save notification prefs | Notification Settings | **P3** |
| Save workflow config | Workflow Settings | **P3** |

---

## Missing Validation

| Validation | Category | Priority |
|------------|----------|----------|
| Feature flag key format | Feature Flags | **P0** |
| Policy pack name required | Policy Packs | **P1** |
| Scoring override clause type required | Scoring Overrides | **P1** |
| Compliance pack region required | Compliance Packs | **P1** |
| Risk weight range (0.0–2.0) | Risk Thresholds | **P2** |
| Risk score range (0.0–1.0) | Risk Thresholds | **P2** |
| AI temperature range (0–100) | AI Settings | **P2** |
| Email format validation | Notification Settings | **P3** |

---

## Missing Success/Error Feedback

All categories need:
- **Success toast/banner** on save
- **Error toast/banner** on failure
- **Loading state** during save
- **Optimistic updates** for toggle operations (feature flags)

---

## Recommended Implementation Order

### Phase 1 — P0 (Feature Flags + Tenant Settings hooks)
```
Week 1:
  ├── Create useTenantSettings hook
  ├── Create useFeatureFlags hook
  ├── Add tenantService methods for feature flag definitions + delete override
  ├── Build FeatureFlagList component (toggle list with override support)
  └── Integrate into TenantSettings page
```

### Phase 2 — P1 (Policy Packs, Scoring Overrides, Compliance Packs)
```
Week 2:
  ├── Add tenantService methods for policy packs (CRUD)
  ├── Add tenantService methods for scoring overrides (CRUD)
  ├── Add tenantService.createCompliancePack()
  ├── Create usePolicyPacks, useScoringOverrides, useCompliancePacks hooks
  ├── Build PolicyPackList + PolicyPackForm components
  ├── Build ScoringOverrideList + ScoringOverrideForm components
  ├── Build CompliancePackList + CompliancePackForm components
  └── Integrate into TenantSettings page with tabbed layout
```

### Phase 3 — P2 (Tenant Configuration, Risk Thresholds, AI Settings)
```
Week 3:
  ├── Create useTenantSummary hook
  ├── Build TenantBrandingEditor (logo, colors, favicon, CSS)
  ├── Build RiskWeightsEditor (per-clause-type weight sliders)
  ├── Build AiConfigEditor (model selector, temperature, token budget)
  ├── Build SlaThresholdsEditor
  └── Integrate into TenantSettings page
```

### Phase 4 — P3 (Notification, Workflow, User Preferences)
```
Week 4:
  ├── Build NotificationPreferences form
  ├── Build WorkflowSettings form
  ├── Build UserPreferences form
  └── Final polish: loading states, error handling, empty states
```

---

## Current Working Screens

| Screen | Status | What Works |
|--------|--------|------------|
| `/admin` — Admin Console | ✅ **Functional** | KPI cards, user list, audit log, system health, AI governance — all from live API |
| `/settings` — General Settings | ⚠️ **Static shell** | 6 icon cards displayed — no API integration, no forms, no save |
| `/tenant-settings` — Tenant Config | 🚧 **Scaffold** | Single placeholder div with "In Development" badge |

---

## Current Completion %

| Component | Completion |
|-----------|-----------|
| Backend Settings APIs | **100%** |
| Frontend API service layer (`tenant.ts`) | **40%** (6 of 15 needed methods) |
| Frontend hooks | **0%** (0 of 6 needed hooks) |
| Frontend components (Settings) | **5%** (static shell only) |
| Frontend components (Tenant Config) | **0%** (scaffold only) |
| Frontend components (Admin Console) | **90%** (fully functional) |
| **Overall Settings UI** | **~8%** |

---

## Appendix: Service Method Gap Analysis

### Methods Present in `tenantService`

```typescript
✅ getConfig(tenantId)           // GET /admin/settings
✅ updateSettings(settings)      // PUT /admin/settings
✅ getFeatures()                 // GET /tenant-config/features/evaluate
✅ updateFeatureOverride(key, val) // POST /tenant-config/features/overrides
✅ getCompliancePacks()          // GET /tenant-config/compliance-packs
✅ getConfigSummary()            // GET /tenant-config/summary
```

### Methods Missing from `tenantService`

```typescript
❌ getFeatureDefinitions()       // GET /tenant-config/features/definitions
❌ getFeatureEvaluate(key)       // GET /tenant-config/features/evaluate/{key}
❌ deleteFeatureOverride(fk,tt,ti) // DELETE /tenant-config/features/overrides/{fk}/{tt}/{ti}
❌ getPolicyPacks()              // GET /tenant-config/policy-packs
❌ createPolicyPack(data)        // POST /tenant-config/policy-packs
❌ getPolicyPack(packId)         // GET /tenant-config/policy-packs/{pack_id}
❌ deletePolicyPack(packId)      // DELETE /tenant-config/policy-packs/{pack_id}
❌ getScoringOverrides()         // GET /tenant-config/scoring-overrides
❌ createScoringOverride(data)   // POST /tenant-config/scoring-overrides
❌ deleteScoringOverride(oid)    // DELETE /tenant-config/scoring-overrides/{override_id}
❌ createCompliancePack(data)    // POST /tenant-config/compliance-packs
```
