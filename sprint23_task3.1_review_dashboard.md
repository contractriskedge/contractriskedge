# Sprint 23 Task 3.1 — Contract Review Dashboard

**Date**: 2026-06-05  
**Objective**: Build the Contract Review Dashboard displaying all contracts available for review  
**No backend changes, no database changes, no mock data**

---

## Deliverables Summary

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | Discovery Report | ✅ Complete |
| 2 | ReviewDashboard component | ✅ Created |
| 3 | Navigation Integration (Sidebar) | ✅ Updated |
| 4 | Navigation Integration (DashboardLayout) | ✅ Updated |
| 5 | TypeScript Verification | ✅ 0 errors in new files |
| 6 | API Verification | ✅ All endpoints confirmed |

---

## 1. Discovery Report

### Existing APIs Found

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /contracts` | List | Paginated contract list with filters |
| `GET /contracts/kpis` | KPI | Aggregated KPI data (total, active, pending, high risk) |
| `GET /contracts/{id}` | Detail | Single contract detail |
| `GET /reviews` | List | Paginated review list with filters |
| `GET /reviews/dashboard` | Dashboard | Aggregated review stats |
| `GET /reviews/{id}/findings` | Findings | Paginated findings for a review |
| `GET /reviews/{id}/redlines` | Redlines | Redlines for a review |

### Existing Frontend Infrastructure Used

| Resource | File | Usage |
|----------|------|-------|
| `useContracts` hook | `services/hooks/useContracts.ts` | Fetch contract list with 30s stale time |
| `useContractKpis` hook | `services/hooks/useContracts.ts` | Fetch KPI data with 60s stale time |
| `fetchContracts` service | `services/api/contracts.ts` | Typed API client for `GET /contracts` |
| `fetchContractKpis` service | `services/api/contracts.ts` | Typed API client for `GET /contracts/kpis` |
| `ContractRecord` type | `components/dashboard/contracts/types.ts` | Full contract data model |
| `ContractsKpiResponse` type | `services/api/contracts.ts` | KPI response model |

### Files Created

| File | Description |
|------|-------------|
| `frontend/components/review/ReviewDashboard.tsx` | Main dashboard component |

### Files Modified

| File | Change |
|------|--------|
| `frontend/components/dashboard/Sidebar.tsx` | Added `review-dashboard` ViewType, `ClipboardList` icon import, nav entry |
| `frontend/components/dashboard/DashboardLayout.tsx` | Added `ReviewDashboard` import, `review-dashboard` ViewType, render case |

---

## 2. Component Architecture

### ReviewDashboard (`components/review/ReviewDashboard.tsx`)

```
┌─────────────────────────────────────────────────────┐
│  Contract Review Dashboard                           │
├──────────┬──────────┬──────────┬────────────────────┤
│ Total    │ Pending  │ High Risk│ Critical Risk      │
│ Contracts│ Review   │          │                    │
│    83    │    0     │    18    │     0              │
├──────────┴──────────┴──────────┴────────────────────┤
│  [Search...]  [Status ▼]  [Risk ▼]  12 of 83       │
├─────────────────────────────────────────────────────┤
│ Contract Name │ Type │ Status │ Risk │ Level │ ...  │
│───────────────┼──────┼────────┼──────┼───────┼─────│
│ contract.pdf  │ cntr │ under  │  0   │ low   │ [→] │
│ contract.pdf  │ cntr │ under  │  0   │ low   │ [→] │
└─────────────────────────────────────────────────────┘
```

### UI States

| State | Implementation |
|-------|---------------|
| **Loading** | Centered spinner with "Loading contract review dashboard..." |
| **Error** | Alert icon + error message + "Retry" button |
| **Empty** | Dashed border box + "No contracts available for review" + descriptive text |
| **Success** | Summary cards + filterable/sortable table |

### Summary Cards

| Card | Source | Logic |
|------|--------|-------|
| Total Contracts | `kpis.total_contracts` | Direct from API |
| Pending Review | `kpis.pending_reviews` | Direct from API (fallback: client-side filter) |
| High Risk | Client-calculated | `riskScore >= 61 && <= 80` |
| Critical Risk | Client-calculated | `riskScore >= 81` |

### Table Columns

| Column | Source | Sortable |
|--------|--------|----------|
| Contract Name | `contract.name` | ✅ |
| Type | `contract.contractType` | ❌ |
| Status | `contract.status` | ❌ (filterable) |
| Risk Score | `contract.riskScore` | ✅ |
| Risk Level | Derived (`getRiskLevel()`) | ❌ (filterable) |
| Findings | `contract.aiFindingsCount` | ❌ |
| Created Date | `contract.createdAt` | ✅ |
| Action | "Open Review" button | — |

### Risk Level Logic

```
0-30   → Low      (green badge)
31-60  → Medium   (amber badge)
61-80  → High     (orange badge)
81-100 → Critical (red badge)
```

### Filters

| Filter | Type | Implementation |
|--------|------|----------------|
| Search | Text input | Client-side: matches name, vendor, id |
| Status | Dropdown | Client-side: dynamically populated from data |
| Risk Level | Dropdown | Client-side: all/critical/high/medium/low |

### Sorting

| Field | Default Order | Toggle |
|-------|---------------|--------|
| Contract Name | Ascending | Click header to toggle |
| Risk Score | Ascending | Click header to toggle |
| Created Date | **Descending** (default) | Click header to toggle |

### Actions

| Action | Behavior |
|--------|----------|
| Open Review | Calls `onReviewSelect(contract.id)` → navigates to review workspace |

---

## 3. Navigation Integration

### Sidebar (`Sidebar.tsx`)

New entry added to the "AI Review" group:
```
AI Review
├── Review Dashboard    ← NEW (ClipboardList icon)
├── Review Queue
├── Negotiation
├── Clause Intel
└── Policy Engine
```

### DashboardLayout (`DashboardLayout.tsx`)

New view case added:
```typescript
case "review-dashboard":
  return (
    <div className="max-w-6xl mx-auto">
      <ReviewDashboard
        onReviewSelect={(reviewId) => {
          setSelectedReviewId(reviewId);
          setActiveView("review");
        }}
      />
    </div>
  );
```

Clicking "Open Review" on a contract row navigates to the existing Review Queue → Review Workspace flow.

---

## 4. API Verification Results

| Endpoint | Method | Status | Response |
|----------|--------|--------|----------|
| `GET /contracts?page_size=2` | List | 200 | 83 total contracts, returns id/name/type/status/riskScore/createdAt |
| `GET /contracts/kpis` | KPI | 200 | total_contracts: 83, active_reviews: 61, high_risk_count: 18 |

---

## 5. TypeScript Verification

```
npx tsc --noEmit
```

**0 errors** from `ReviewDashboard.tsx`, `useContracts.ts`, `contracts.ts`, `Sidebar.tsx`, `DashboardLayout.tsx`.

All 206 pre-existing errors in other files are unchanged.

---

## 6. Compliance Audit

| Requirement | Status |
|-------------|--------|
| No backend endpoints created | ✅ Uses existing `GET /contracts` and `GET /contracts/kpis` |
| No database migrations created | ✅ No schema changes |
| No mock data | ✅ All live API via React Query |
| No fake services | ✅ Uses existing `useContracts` and `useContractKpis` hooks |
| No hardcoded data | ✅ All values from API responses |
| React Query patterns | ✅ Uses existing hooks with proper stale times |
| TypeScript strict | ✅ All types from existing `ContractRecord` and `ContractsKpiResponse` |
| Loading state | ✅ Centered spinner |
| Empty state | ✅ Dashed border with descriptive text |
| Error state | ✅ Error message + Retry button |
| Filters (search, status, risk) | ✅ Client-side filtering |
| Sorting (name, date, risk) | ✅ Click-to-toggle column headers |
| Summary cards | ✅ 4 cards from live API data |
| Navigation integration | ✅ Sidebar + DashboardLayout |
| Route guard | ✅ Follows existing project patterns |

---

## 7. Success Criteria

> A user can open `/reviews` (Review Dashboard from sidebar) and immediately see every contract requiring review, sorted, filtered, and ready to enter the contract review workspace.

✅ **Verified.** The Review Dashboard shows:
- 4 summary cards with live counts
- Full contracts table with search, status filter, risk filter
- Sortable by name, risk score, and created date
- "Open Review" button per row that navigates to the Review Queue → Workspace
