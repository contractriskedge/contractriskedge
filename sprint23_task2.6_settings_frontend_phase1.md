# Sprint 23 Task 2.6 — Settings Frontend Phase 1

**Date**: 2026-06-05  
**Objective**: Convert Settings from static shell to functional UI using verified Settings APIs  
**Scope**: Phase 1 — React Query hooks, tenantService extension, FeatureFlagList component, TenantSettings page rewrite

---

## Deliverables

| # | Deliverable | Files | Status |
|---|-------------|-------|--------|
| 1 | **React Query hooks** | `services/hooks/useTenantSettings.ts` | ✅ Done |
| 2 | **Extended tenantService** | `services/api/tenant.ts` | ✅ Done |
| 3 | **FeatureFlagList component** | `components/tenant/FeatureFlagList.tsx` | ✅ Done |
| 4 | **GeneralSettingsForm component** | `components/tenant/GeneralSettingsForm.tsx` | ✅ Done |
| 5 | **Functional TenantSettings page** | `components/tenant/TenantSettings.tsx` | ✅ Done |
| 6 | **TypeScript verification** | `npx tsc --noEmit` — 0 errors in new files | ✅ Done |
| 7 | **Browser validation** | All API endpoints verified | ✅ Done |

---

## 1. React Query Hooks

**File**: `frontend/services/hooks/useTenantSettings.ts`

### Hooks Created

| Hook | Type | Description |
|------|------|-------------|
| `useTenantSettings()` | Query | Fetches `GET /admin/settings` with 60s stale time |
| `useUpdateTenantSettings()` | Mutation | `PUT /admin/settings` with **optimistic updates** + rollback on error |
| `useFeatureFlagDefinitions()` | Query | Fetches `GET /features/definitions` with 120s stale time |
| `useFeatureFlagEvaluations()` | Query | Fetches `GET /features/evaluate` with 30s stale time |
| `useSetFeatureOverride()` | Mutation | `POST /features/overrides` with cache invalidation |
| `useDeleteFeatureOverride()` | Mutation | `DELETE /features/overrides/{fk}/{tt}/{ti}` with cache invalidation |
| `useFeatureFlagsWithValues()` | Composed | Merges definitions + evaluations into a single array with `refetch()` |

### Key Features

- **Loading states**: All queries return `isLoading` for spinner display
- **Error states**: All queries return `error` for error display with retry button
- **Cache invalidation**: Mutations invalidate related query caches on success
- **Optimistic updates**: `useUpdateTenantSettings` immediately updates cached data, rolls back on error
- **Stale time tuning**: Definitions (rarely change) = 120s, Evaluations (toggle-dependent) = 30s

---

## 2. Extended tenantService

**File**: `frontend/services/api/tenant.ts`

### New Types Added

```typescript
TenantSettingsResponse    — Backend-aligned shape of GET /admin/settings response
TenantSettingsUpdate      — Backend-aligned shape for PUT /admin/settings body
FeatureFlagDefinition     — Backend-aligned shape from GET /features/definitions
FeatureFlagEvaluation     — Backend-aligned shape from GET /features/evaluate
FeatureFlagOverride       — Backend-aligned shape from POST /features/overrides response
FeatureOverrideCreate     — Backend-aligned shape for POST /features/overrides body
```

### New Methods Added

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `getSettings()` | `GET /admin/settings` | Fetch tenant settings |
| `updateSettings(settings)` | `PUT /admin/settings` | Update tenant settings |
| `getFeatureDefinitions()` | `GET /features/definitions` | Fetch all flag definitions |
| `evaluateFeatures()` | `GET /features/evaluate` | Evaluate all flags |
| `evaluateFeature(key)` | `GET /features/evaluate/{key}` | Evaluate single flag |
| `setFeatureOverride(override)` | `POST /features/overrides` | Create/update override |
| `deleteFeatureOverride(fk, tt, ti)` | `DELETE /features/overrides/{fk}/{tt}/{ti}` | Remove override |

### Methods Preserved

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `getCompliancePacks()` | `GET /compliance-packs` | List compliance packs |
| `getConfigSummary()` | `GET /summary` | Get config summary |

---

## 3. FeatureFlagList Component

**File**: `frontend/components/tenant/FeatureFlagList.tsx`

### States Covered

| State | UI |
|-------|-----|
| **Loading** | Centered spinner with "Loading feature flags..." text |
| **Error** | Alert icon + error message + "Retry" button |
| **Empty** | Info icon + "No feature flags defined" |
| **Success** | List of flag cards with toggle, name, description, status badge |
| **Toggling** | Spinner replaces toggle icon during mutation |
| **Success feedback** | Green toast: "Feature X enabled/disabled" (auto-dismiss 3s) |
| **Error feedback** | Red toast: "Failed to update Feature X" (auto-dismiss 5s) |

### Component Props

```typescript
interface FeatureFlagListProps {
  tenantId: string;  // Used as target_id for overrides
}
```

### Visual Features

- **ToggleRight** (green) / **ToggleLeft** (gray) icons for enable/disable
- **"Enabled"/"Disabled"** status badge on each flag
- **"Overridden"** badge when source is not "default"
- **Source info** showing `source` and `reason` from evaluation
- **Dependencies** listed when present
- **Animated** entrance with framer-motion

---

## 4. GeneralSettingsForm Component

**File**: `frontend/components/tenant/GeneralSettingsForm.tsx`

### Sections

| Section | Fields | Control Type |
|---------|--------|-------------|
| **Branding** | Brand Name, Primary Color, Accent Color | Text input + color picker |
| **AI Configuration** | AI Model, Temperature, Max Tokens | Select + range slider + select |
| **Risk Thresholds** | Critical, High, Medium | Range sliders (0-100) |
| **SLA Thresholds** | Critical, High, Medium, Low hours | Number inputs |
| **Email Redirect** | Enable toggle, Redirect To email | Checkbox + email input |

### States Covered

| State | UI |
|-------|-----|
| **Loading** | Centered spinner with "Loading settings..." |
| **Error** | Alert icon + error message + "Retry" button |
| **Empty** | "No settings available" |
| **Dirty detection** | Save button disabled when no changes made |
| **Saving** | Spinner in save button + "Saving..." text |
| **Save disabled** | Grayed out button + "No changes to save" hint |
| **Success feedback** | Green toast: "Settings saved successfully" (3s) |
| **Error feedback** | Red toast: "Failed to save: ..." (5s) |

---

## 5. TenantSettings Page

**File**: `frontend/components/tenant/TenantSettings.tsx`

### Before (Scaffold)
- Single placeholder div with gear icon
- "Sprint 7 — In Development" badge
- No API calls, no forms, no functionality

### After (Functional)
- **Header** with title and description
- **Tabbed layout** with two tabs:
  - **General** → `GeneralSettingsForm` (branding, AI, risk, SLA, email)
  - **Features** → `FeatureFlagList` (flag toggles with overrides)
- **Animated** tab transitions with framer-motion
- **Extensible** tab architecture for Phase 2+ additions

---

## 6. API Validation Results

| # | Endpoint | Method | Status | Verified |
|---|----------|--------|--------|----------|
| 1 | `/admin/settings` | GET | 200 | Returns brand_name, features_enabled, risk thresholds, SLA |
| 2 | `/admin/settings` | PUT | 200 | Updates persist across GET after write |
| 3 | `/features/definitions` | GET | 200 | Returns 14 flag definitions |
| 4 | `/features/evaluate` | GET | 200 | Returns 14 flag evaluations |
| 5 | `/features/evaluate/{key}` | GET | 200 | Single flag evaluation |
| 6 | `/features/overrides` | POST | 201 | Override created with correct tenant_id |
| 7 | `/features/overrides/{fk}/{tt}/{ti}` | DELETE | 200 | Override removed successfully |

### Key Finding
Feature flag overrides require `target_id` to match the tenant's actual UUID (from JWT `tenant_id` claim), not a generic string like `"default"`. The `FeatureFlagList` component receives `tenantId` as a prop and passes it correctly.

---

## 7. Files Changed

| File | Change |
|------|--------|
| `frontend/services/api/tenant.ts` | Added 7 new types, 7 new methods, updated query keys |
| `frontend/services/api/index.ts` | Updated barrel exports to match renamed types |
| `frontend/services/hooks/useTenantSettings.ts` | **NEW** — 7 hooks (4 queries, 2 mutations, 1 composed) |
| `frontend/components/tenant/FeatureFlagList.tsx` | **NEW** — Feature flag toggle list with full state coverage |
| `frontend/components/tenant/GeneralSettingsForm.tsx` | **NEW** — General settings form with 5 sections |
| `frontend/components/tenant/TenantSettings.tsx` | **REWRITTEN** — Replaced scaffold with tabbed functional UI |

---

## 8. Implementation Notes

### No New Backend APIs
All frontend code consumes the **existing 13 verified Settings endpoints** from Sprint 23 Task 2.4.

### No Database Changes
The frontend uses the existing database schema — no migrations were created.

### No Mock Data
All components use live API data via React Query. No hardcoded defaults or mock imports.

### TypeScript Safety
All new code is fully typed with backend-aligned interfaces. Zero TypeScript errors.

### Cache Strategy
- Settings: 60s stale time (moderately fresh)
- Flag definitions: 120s stale time (rarely change)
- Flag evaluations: 30s stale time (toggle-dependent)
- Mutations: Invalidate related caches on success
- Settings mutation: Optimistic update with rollback on error
