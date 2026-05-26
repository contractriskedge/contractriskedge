# ContractRiskEdge — Frontend Integration Audit

**Date:** May 17, 2026  
**Author:** Automated Code Audit  
**Status:** ❌ FAIL — 0/22 pages pass

---

## Executive Summary

A complete frontend integration audit was performed across all 22 dashboard pages and modules. The application currently relies on **17 dedicated mock data files** and **7+ inline static data sources**. Only **3 domains** (Uploads, AI Analysis, Contract Review) have full React Query hooks + typed service layers. The remaining **12+ dashboard pages** render entirely from mock data with zero backend API calls.

**Key finding:** 21 of 22 pages FAIL the audit. The only PARTIAL pass is the DashboardLayout which uses some real hooks but lacks loading/error states. No page fully passes.

---

## Methodology

The audit was conducted across 6 phases:

| Phase | Description |
|-------|-------------|
| **Phase 1 — Codebase Scan** | Searched all frontend files for `mock`, `fake`, `dummy`, `sample`, `fixtures`, `placeholder`, `hardcoded`, `static`, `demo`, `seed` patterns |
| **Phase 2 — API Layer Inventory** | Mapped all API services (`services/api/`), React Query hooks (`services/hooks/`), and legacy API (`lib/api.ts`) |
| **Phase 3 — Backend Endpoint Map** | Read all backend router files to catalog every registered API endpoint |
| **Phase 4 — Page-by-Page Validation** | Checked each page for: real data, loading state, empty state, error state, mutations, pagination, filtering |
| **Phase 5 — Gap Analysis** | Compared what each page renders vs what backend endpoints exist |
| **Phase 6 — Remediation Planning** | Prioritized by backend readiness (existing endpoints first, new backend domains second) |

---

## Integration Matrix

| # | Page / Module | File(s) | Backend API Available | React Query Hooks | Real Data | Loading | Empty | Error | Mutations | Status |
|---|--------------|---------|:--------------------:|:-----------------:|:---------:|:-------:|:-----:|:-----:|:---------:|:------:|
| 1 | Ingestion Center | `ingestion/IngestionCenter.tsx` | ✅ 6 endpoints | ✅ `useUploads` | ❌ Mock | ❌ | ❌ | ❌ | ✅ (unwired) | **FAIL** |
| 2 | Review Workspace | `review/ReviewWorkspace.tsx` | ✅ 20 endpoints | ✅ `useReviews` | ❌ Mock | ❌ | ❌ | ❌ | ✅ (unwired) | **FAIL** |
| 3 | Search Hub | `search/SearchHub.tsx` | ✅ 7 endpoints | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 4 | Analytics Center | `analytics/AnalyticsCenter.tsx` | ✅ 5 endpoints | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 5 | Compliance Center | `compliance/ComplianceCenter.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 6 | Portfolio Dashboard | `PortfolioDashboard.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 7 | CFO View | `CfoView.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 8 | Contracts Repository | `ContractsPage.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 9 | Negotiation Center | `negotiation/NegotiationCenter.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 10 | Clause Library | `clause-library/ClauseLibrary.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 11 | Obligation Center | `obligations/ObligationCenter.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 12 | Workflow Center | `workflows/WorkflowCenter.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 13 | Relationship Graph | `relationship-graph/RelationshipGraph.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 14 | Procurement Dashboard | `ProcurementDashboard.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 15 | Benchmark Page | `BenchmarkPage.tsx` | ❌ (1 legacy endpoint) | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 16 | Contract Detail | `contract-detail/ContractDetailWorkspace.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 17 | Executive Dashboard | `ExecutiveDashboard.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 18 | Admin Console | `admin/AdminConsole.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 19 | Legal Review View | `LegalView.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 20 | AI Chat Assistant | `ai-assistant/AiAssistantPanel.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 21 | Collaboration Panel | `collaboration/CollaborationPanel.tsx` | ❌ None | ❌ None | ❌ Mock | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| 22 | Dashboard Layout | `DashboardLayout.tsx` | ✅ Various | ✅ Partial | ✅ Partial | ❌ | ❌ | ❌ | ❌ | **PARTIAL** |

---

## Summary Statistics

| Metric | Count |
|--------|:-----:|
| Total dashboard pages/modules | **22** |
| **PASS** (real API data, all states handled) | **0** |
| **PARTIAL** (some real API, some mock) | **1** (DashboardLayout) |
| **FAIL** (entirely mock/static data) | **21** |
| Mock data files to eliminate | **17** |
| Components importing mock data | **15** |
| Inline static data arrays | **7+** |
| Backend API endpoints available | **90** |
| Backend API endpoints actually used | **~5** |

---

## Mock Data Files — Complete Inventory

### 17 Dedicated Mock Data Files

All located under `frontend/components/dashboard/`:

| # | File | Size | Description |
|---|------|------|-------------|
| 1 | `cfo/mockData.ts` | ~400 lines | CFO KPIs, exposures, renewals, vendor risks, SLA impacts, revenue leakage, AI insights |
| 2 | `compliance/mockData.ts` | ~450 lines | Compliance KPIs, regulations, findings, remediation, vendor compliance, audits, AI insights |
| 3 | `ingestion/mockData.ts` | ~350 lines | Ingestion KPIs, import sources, queues, pipeline stages, jobs, failed imports, templates |
| 4 | `search/mockData.ts` | ~450 lines | Search KPIs, categories, saved/recent searches, AI suggestions, results, analytics |
| 5 | `negotiation/mockData.ts` | ~450 lines | Negotiation KPIs, clause contents, redline entries, issues, participants, comments, AI insights |
| 6 | `analytics/mockData.ts` | ~200 lines | Analytics KPIs, risk trends, department/vendor/executive/compliance analytics, forecasts |
| 7 | `obligations/mockData.ts` | ~200 lines | Obligation KPIs, 48 generated obligations, AI insights, SLA metrics, timeline events |
| 8 | `clause-library/mockData.ts` | ~250 lines | Clause KPIs, 48 generated clause records, playbooks, benchmark data |
| 9 | `contract-detail/mockData.ts` | ~250 lines | Full contract with 16 clauses, version history, activity, negotiation issues, workflow |
| 10 | `admin/mockData.ts` | ~250 lines | Admin KPIs, 24 users, role defs, 20 AI governance events, 30 audit events, integrations |
| 11 | `workflows/mockData.ts` | ~200 lines | Workflow KPIs, 36 workflow items, insights, SLA metrics, automation rules, team members |
| 12 | `relationship-graph/mockData.ts` | ~250 lines | Generated graph ~80 nodes/~120 edges, KPIs, AI insights, timeline events |
| 13 | `procurement/mockData.ts` | ~250 lines | Procurement KPIs, 40 supplier records, spend trends, vendor categories, geographic risk |
| 14 | `contracts/mockData.ts` | ~200 lines | Contract KPIs, 60 generated contract records, saved views, activity, clause analysis |
| 15 | `portfolio/mockData.ts` | ~250 lines | Portfolio KPIs, risk trends, monthly exposure, vendor risk, clause heatmap, 48 contracts |
| 16 | `executive/mockData.ts` | ~250 lines | Executive KPIs, risk trends, monthly exposure, vendor risk, clause heatmap, AI insights |
| 17 | `benchmark/mockData.ts` | ~250 lines | Benchmark KPIs, 16 clause benchmarks, 8 industry comparisons, 6 market insights |

### 5 Components with Inline Static Data

| File | Content |
|------|---------|
| `review/ReviewWorkspace.tsx` | `KPI_METRICS` (4 objects), `MOCK_QUEUE` (4 items), `AI_FINDINGS` (3 items), `INITIAL_FILTERS` — all inline hardcoded arrays |
| `ai-assistant/AiAssistantPanel.tsx` | Hardcoded `welcomeMessage` with markdown + `responseMap` with financial data strings |
| `collaboration/CollaborationPanel.tsx` | Hardcoded `TEAM_MEMBERS` database (5 users) for @mentions |
| `contract-detail/ContractDetailWorkspace.tsx` | `sampleTexts` — 4 hardcoded clause text samples for redline generation |
| `legal-review/LegalView.tsx` | Inline static KPI metrics and review queue items |

---

## Backend API Availability

### ✅ Available Backend Endpoints (90 total)

| Domain | Endpoints | Has React Query Hooks? |
|--------|:---------:|:---------------------:|
| Health | 2 | ❌ |
| Dev Auth | 1 | ❌ |
| Uploads / Ingestion | 6 | ✅ `useUploads` |
| Search | 7 | ❌ |
| AI Analysis | 5 | ✅ (via `useUploads`) |
| Contract Review | 20 | ✅ `useReviews` |
| Notifications & Workflows | 9 | ❌ |
| Legal Playbook & Policy Engine | 30 | ❌ |
| Analytics | 5 | ❌ |
| Audit | 2 | ❌ |
| Exports | 2 | ❌ |
| Prometheus Metrics | 1 | ❌ |
| Integration Subsystem | 27 (unregistered) | ❌ |

### ❌ Missing Backend Domains (No Endpoints Exist)

These pages require **new backend development** before frontend integration is possible:

| Page | Required Backend Module |
|------|------------------------|
| Portfolio Dashboard | `/api/v1/portfolio/*` |
| CFO View | `/api/v1/cfo/*` |
| Contracts Repository | `/api/v1/contracts/*` |
| Negotiation Center | `/api/v1/negotiations/*` |
| Clause Library | `/api/v1/clauses/*` |
| Obligation Center | `/api/v1/obligations/*` |
| Workflow Center | `/api/v1/workflows/*` |
| Relationship Graph | `/api/v1/relationships/*` |
| Procurement Dashboard | `/api/v1/procurement/*` |
| Benchmark Page | `/api/v1/benchmarks/*` |
| Contract Detail | `/api/v1/contracts/{id}/*` |
| Executive Dashboard | `/api/v1/executive/*` |
| Admin Console | `/api/v1/admin/*` |
| Legal Review View | `/api/v1/legal/*` |
| AI Chat Assistant | `/api/v1/chat/*` |
| Collaboration Panel | `/api/v1/collaboration/*` |
| Compliance Center | `/api/v1/compliance/*` |

---

## Existing API Service Layer

### Modern Layer (`services/api/` + `services/hooks/`)

| File | Contents |
|------|----------|
| `services/api/client.ts` | Centralized API client — JWT auth, retry (3x), timeout (30s), idempotency keys, 401 auto-logout |
| `services/api/uploads.ts` | `uploadService` — 11 methods for uploads, AI analysis, chunks |
| `services/api/reviews.ts` | `reviewService` — 19 methods for reviews, findings, redlines, comments, approval |
| `services/hooks/useUploads.ts` | 5 query hooks + 4 mutation hooks for uploads/ingestion |
| `services/hooks/useReviews.ts` | 8 query hooks + 9 mutation hooks for reviews |

### Legacy Layer (`lib/api.ts`)

| Domain | Methods |
|--------|---------|
| Auth | `login`, `getToken` |
| Uploads | `uploadDocument`, `batchUpload` |
| Contracts | `getContracts` |
| Risks | `getRiskScore`, `getRisks`, `getRiskById` |
| Redlines | `getRedlineSuggestions`, `acceptRedline`, `rejectRedline` |
| Benchmarks | `getBenchmarkScore` |
| Evaluations | `getEvaluation` |
| Exports | URL builders for DOCX/PDF/CSV |
| Playbooks | Full CRUD (playbooks, rules, clauses, evaluations, overrides) |
| Monitoring | `getHealthDetailed` |

---

## Remediation Plan

### Phase 1 — Immediate (Backend APIs Exist + Hooks Exist)

These 3 domains already have working backend endpoints AND React Query hooks. They just need the frontend components wired up.

| Priority | Page | Effort | Action |
|:--------:|------|--------|--------|
| **P1** | Ingestion Center | 2-3 days | Replace `mockImportJobs`/`mockProcessingQueues`/etc. with `useUploadsList()`, `useUploadStatus()`, `useUploadMutations()`. Add loading/empty/error states. |
| **P2** | Review Workspace | 2-3 days | Replace inline `MOCK_QUEUE`/`AI_FINDINGS`/`KPI_METRICS` with `useReviewsList()`, `useFindings()`, `useRedlines()`, `useReviewStats()`. Wire all 9 mutations. |
| **P3** | Search Hub | 3-4 days | Create `useSearch` hooks wrapping the 7 search endpoints. Replace 7 mock datasets. |

### Phase 2 — Short-term (Backend APIs Exist, No Hooks)

These domains have backend endpoints but need React Query hooks created.

| Priority | Page | Effort | Action |
|:--------:|------|--------|--------|
| **P4** | Analytics Center | 2-3 days | Create `useAnalytics` hooks for 5 endpoints. Replace 9 mock datasets. |
| **P5** | Dashboard Layout | 1 day | Add loading/error/empty states to existing `useUploads` + `useReviews` usage. |
| **P6** | Notifications | 2 days | Create `useNotifications` hooks for 9 endpoints. |
| **P7** | Playbooks | 3-4 days | Create `usePlaybooks` hooks for 30 endpoints. |
| **P8** | Exports | 1 day | Create `useExports` hooks. |
| **P9** | Audit | 1 day | Create `useAudit` hooks for 2 endpoints. |

### Phase 3 — Medium-term (Need New Backend Endpoints)

These domains require new backend modules before frontend integration.

| Priority | Page | Effort (Backend) | Effort (Frontend) |
|:--------:|------|:----------------:|:-----------------:|
| **P10** | Contracts Repository | 3-4 days | 2-3 days |
| **P11** | Portfolio Dashboard | 3-4 days | 2-3 days |
| **P12** | Negotiation Center | 4-5 days | 3-4 days |
| **P13** | Clause Library | 2-3 days | 2 days |
| **P14** | Obligation Center | 2-3 days | 2 days |
| **P15** | Workflow Center | 3-4 days | 2-3 days |
| **P16** | Relationship Graph | 3-4 days | 3-4 days |
| **P17** | Procurement Dashboard | 3-4 days | 2-3 days |
| **P18** | Benchmark Page | 2-3 days | 2 days |
| **P19** | Contract Detail | 2-3 days | 2 days |
| **P20** | Executive Dashboard | 3-4 days | 2-3 days |
| **P21** | Admin Console | 4-5 days | 3-4 days |
| **P22** | CFO View | 3-4 days | 2-3 days |
| **P23** | Compliance Center | 3-4 days | 2-3 days |
| **P24** | Legal Review View | 2-3 days | 2 days |
| **P25** | AI Chat Assistant | 2-3 days | 1-2 days |
| **P26** | Collaboration Panel | 2-3 days | 1-2 days |

---

## Files to Delete After Integration

After all integrations are complete, remove these **17 mock data files**:

```
frontend/components/dashboard/ingestion/mockData.ts
frontend/components/dashboard/search/mockData.ts
frontend/components/dashboard/analytics/mockData.ts
frontend/components/dashboard/compliance/mockData.ts
frontend/components/dashboard/negotiation/mockData.ts
frontend/components/dashboard/clause-library/mockData.ts
frontend/components/dashboard/obligations/mockData.ts
frontend/components/dashboard/workflows/mockData.ts
frontend/components/dashboard/relationship-graph/mockData.ts
frontend/components/dashboard/contract-detail/mockData.ts
frontend/components/dashboard/admin/mockData.ts
frontend/components/dashboard/contracts/mockData.ts
frontend/components/benchmark/mockData.ts
frontend/components/portfolio/mockData.ts
frontend/components/procurement/mockData.ts
frontend/components/cfo/mockData.ts
frontend/components/executive/mockData.ts
```

Also remove inline static data from these files:

```
frontend/components/review/ReviewWorkspace.tsx         # KPI_METRICS, MOCK_QUEUE, AI_FINDINGS, INITIAL_FILTERS
frontend/components/dashboard/ai-assistant/AiAssistantPanel.tsx  # welcomeMessage, responseMap
frontend/components/dashboard/collaboration/CollaborationPanel.tsx  # TEAM_MEMBERS
frontend/components/dashboard/contract-detail/ContractDetailWorkspace.tsx  # sampleTexts
```

---

## Final Verdict

| Category | Result |
|----------|--------|
| **PASS** | **0 / 22 pages** |
| **PARTIAL** | **1 / 22 pages** (DashboardLayout) |
| **FAIL** | **21 / 22 pages** |
| **Overall** | **❌ FAIL — Application is not demo-realistic** |

The application requires **substantial backend endpoint development** (16 new domain modules) plus **frontend React Query integration** (all 22 pages) before it can be considered demo-realistic with live backend data only.

---

## Appendix: Search Patterns Used

| Pattern | Files Matched |
|---------|---------------|
| `mock` | 17 mock data files, 15 component imports |
| `fake` | 0 matches |
| `dummy` | 0 matches |
| `sample` | `contract-detail/ContractDetailWorkspace.tsx` (sampleTexts) |
| `fixtures` | 0 matches |
| `placeholder` | ~30+ matches (all legitimate HTML `placeholder` attributes on inputs) |
| `hardcoded` | 0 matches (no comments using this word) |
| `static` | `review/ReviewWorkspace.tsx` (inline static arrays) |
| `demo` | 0 matches |
| `seed` | 0 matches |
