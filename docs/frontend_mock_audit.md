# Frontend Mock Data Audit — Elimination Plan

**Date:** 2026-05-27
**Status:** FINAL

---

## Summary

| Metric | Count |
|--------|-------|
| **mockData.ts files** | 16 (2,958 lines) |
| **Components importing mockData** | 20 |
| **PlaceholderView usages** | 5 (compliance, clause-library, obligations, negotiation, workflows) |
| **Inline hardcoded data arrays** | 2 (LegalReview MOCK_QUEUE, AnomalyFeedWidget MOCK_ANOMALIES) |
| **Dead/unused components** | 20+ (never imported by any active component) |

---

## Phase 1: REPLACE NOW (14 components)

These are actively rendered in `DashboardLayout.tsx` and must be wired to real APIs immediately.

| # | Component | mockData File | Lines | API Hooks Available | Complexity |
|---|-----------|---------------|-------|-------------------|------------|
| 1 | `ContractsPage.tsx` | `contracts/mockData.ts` | 221 | ✅ `useContracts`, `useContractKpis`, `useSavedViews` | MEDIUM |
| 2 | `ProcurementDashboard.tsx` | `procurement/mockData.ts` | 176 | ✅ `useProcurementDashboard`, `useSuppliers` | HIGH (7 data sources) |
| 3 | `ComplianceCenter.tsx` | `compliance/mockData.ts` | 215 | ✅ `useComplianceDashboard`, `useComplianceFindings` | MEDIUM |
| 4 | `ComplianceDetailDrawer.tsx` | `compliance/mockData.ts` | (shared) | ✅ `useComplianceFindings` | LOW |
| 5 | `WorkflowCenter.tsx` | `workflows/mockData.ts` | 126 | ✅ `useWorkflowDashboard`, `useWorkflows` | MEDIUM |
| 6 | `BenchmarkPage.tsx` | `benchmarks/mockData.ts` | 270 | ✅ `useBenchmarkDashboard`, `useIndustryBenchmarks` | HIGH |
| 7 | `AdminConsole.tsx` | `admin/mockData.ts` | 440 | ✅ `useAdminDashboard`, `useAdminUsers`, `useAuditLogs` | HIGH |
| 8 | `PortfolioDashboard.tsx` | `portfolio/mockData.ts` | 131 | ⚠️ Needs new hook | MEDIUM |
| 9 | `ContractDetailWorkspace.tsx` | `contract-detail/mockData.ts` | 191 | ✅ `useContractById` | MEDIUM |
| 10 | `CfoRiskCenter.tsx` | `cfo/mockData.ts` | 145 | ⚠️ Needs new hook | MEDIUM |
| 11 | `CfoDetailDrawer.tsx` | `cfo/mockData.ts` | (shared) | ⚠️ Needs new hook | LOW |
| 12 | `RelationshipGraph.tsx` | `relationship-graph/mockData.ts` | 165 | ⚠️ Needs new hook | MEDIUM |
| 13 | `ClauseLibrary.tsx` | `clause-library/mockData.ts` | 183 | ⚠️ Needs new hook | MEDIUM |
| 14 | `ObligationCenter.tsx` | `obligations/mockData.ts` | 119 | ⚠️ Needs new hook | MEDIUM |

## Phase 2: REPLACE NOW (Negotiation + Search — 6 components)

These are rendered conditionally but still critical.

| # | Component | mockData File | Lines | API Hooks Available | Complexity |
|---|-----------|---------------|-------|-------------------|------------|
| 15 | `NegotiationCenter.tsx` | `negotiation/mockData.ts` | 217 | ⚠️ Needs new hook | HIGH |
| 16 | `SearchBar.tsx` | `search/mockData.ts` | 131 | ✅ `useSearch` exists | LOW |
| 17 | `SearchLeftSidebar.tsx` | `search/mockData.ts` | (shared) | ✅ `useSearch` exists | LOW |
| 18 | `SearchRightPanel.tsx` | `search/mockData.ts` | (shared) | ✅ `useSearch` exists | LOW |
| 19 | `QuickPreviewDrawer.tsx` | `search/mockData.ts` | (shared) | ✅ `useSearch` exists | LOW |
| 20 | `PreviewDrawer.tsx` | `contracts/mockData.ts` | (shared) | ✅ `useContractById` | LOW |

---

## Phase 3: DELETE (16 mockData.ts files)

After all components are migrated, delete these files entirely.

| File | Lines | Status |
|------|-------|--------|
| `contracts/mockData.ts` | 221 | DELETE after ContractsPage + PreviewDrawer migrated |
| `procurement/mockData.ts` | 176 | DELETE after ProcurementDashboard migrated |
| `compliance/mockData.ts` | 215 | DELETE after ComplianceCenter migrated |
| `workflows/mockData.ts` | 126 | DELETE after WorkflowCenter migrated |
| `benchmarks/mockData.ts` | 270 | DELETE after BenchmarkPage migrated |
| `admin/mockData.ts` | 440 | DELETE after AdminConsole migrated |
| `portfolio/mockData.ts` | 131 | DELETE after PortfolioDashboard migrated |
| `contract-detail/mockData.ts` | 191 | DELETE after ContractDetailWorkspace migrated |
| `cfo/mockData.ts` | 145 | DELETE after CfoRiskCenter migrated |
| `relationship-graph/mockData.ts` | 165 | DELETE after RelationshipGraph migrated |
| `clause-library/mockData.ts` | 183 | DELETE after ClauseLibrary migrated |
| `obligations/mockData.ts` | 119 | DELETE after ObligationCenter migrated |
| `negotiation/mockData.ts` | 217 | DELETE after NegotiationCenter migrated |
| `search/mockData.ts` | 131 | DELETE after Search components migrated |
| `analytics/mockData.ts` | 109 | ⚠️ Check if AnalyticsCenter still uses it |
| `ingestion/mockData.ts` | 119 | ⚠️ Check if IngestionCenter still uses it |

---

## Phase 4: ELIMINATE INLINE HARDCODED DATA

| Component | Issue | Fix |
|-----------|-------|-----|
| `legal-review/LegalReview.tsx` | `MOCK_QUEUE` inline array | Replace with `useReviews` hook |
| `command-center/widgets/AnomalyFeedWidget.tsx` | `MOCK_ANOMALIES` inline array | Replace with analytics API |

---

## Phase 5: REMOVE DEAD COMPONENTS (20+)

These components are never imported by any active component. Delete or archive.

| Component | Directory |
|-----------|-----------|
| `LegalReview.tsx` | `legal-review/` |
| `FilterDropdown.tsx` | `legal-review/` |
| `SuggestionList.tsx` | `legal-review/` |
| `AnalyticsCharts.tsx` | `analytics/` |
| `DashboardGrid.tsx` | `analytics/` |
| `AnalyticsContext.tsx` | `analytics/` |
| `WidgetPickerModal.tsx` | `analytics/` |
| `ExecutiveNarrative.tsx` | `analytics/` |
| `SavedViews.tsx` | `analytics/` |
| `RecommendationsEngine.tsx` | `analytics/` |
| `MetadataReview.tsx` | `ingestion/` |
| `BatchUploadPanel.tsx` | `ingestion/` |

---

## Execution Order

```
Session 2a: ContractsPage + PreviewDrawer + ContractDetailWorkspace
Session 2b: ProcurementDashboard + ComplianceCenter + ComplianceDetailDrawer
Session 2c: WorkflowCenter + BenchmarkPage + AdminConsole
Session 2d: PortfolioDashboard + CfoRiskCenter + CfoDetailDrawer
Session 2e: RelationshipGraph + ClauseLibrary + ObligationCenter
Session 2f: NegotiationCenter + Search components
Session 2g: Delete all mockData.ts files + dead components
Session 2h: Create Next.js route structure
```

---

## Success Gates

- [ ] All 20 components use real API hooks
- [ ] 0 `from "./mockData"` imports remain
- [ ] 0 `MOCK_` inline arrays exist
- [ ] All 16 `mockData.ts` files deleted
- [ ] Loading states visible in all components
- [ ] Error states visible in all components
- [ ] Empty states visible in all components
