# Backend Integration Matrix

> Last updated: May 31, 2026
> Status of real API data vs mock/fallback data across all frontend modules.

## Legend

| Icon | Meaning |
|------|---------|
| ✅ | Real API data — no mock fallbacks |
| ⚠️ | Partial — some real data, some mock/fallback |
| ❌ | Mock only — no real API integration |
| 🏗️ | Under construction — empty state shown until backend available |

---

## Core Contract Pipeline

| Module | Status | Notes |
|--------|--------|-------|
| **Contracts** | ✅ | Real API via contract service |
| **Ingestion** | ✅ | Real API via ingestion service |
| **Review Queue** | ✅ | Real API via `useReviewDashboard` hook |
| **Clause Library** | ✅ | Real API |
| **Obligations** | ✅ | Real API |

## AI Review

| Module | Status | Notes |
|--------|--------|-------|
| **Review Queue** | ✅ | Real API — `useReviewDashboard`, `useReviews` |
| **Negotiation** | ⚠️ | Mostly real, some mock edge cases |
| **Clause Intel** | ⚠️ | Partial real data, partial mock |
| **Policy Engine** | ❌ | No API integration yet |

## Operations

| Module | Status | Notes |
|--------|--------|-------|
| **Command Center** | ✅ | **Now clean** — uses `useReviewDashboard` hook. Shows empty states when no data. |
| **Reviewer Ops** | ❌ | Entirely hardcoded mock data. No API hooks. |
| **Workflow Intel** | 🏗️ | **Now clean** — all 5 tabs show empty states. Waiting for workflow API. |
| **Search & Discovery** | ❌ | No API integration yet |

## Analytics

| Module | Status | Notes |
|--------|--------|-------|
| **Analytics** | ✅ | Uses real API hooks (`useAnalyticsDashboard`). Proper loading/error/empty states. |
| **Benchmarks** | ❌ | No API integration yet |
| **Portfolio** | ❌ | No API integration yet |
| **Executive** | ✅ | **Now clean** — all widgets removed hardcoded fallbacks. Shows empty states when no data. |

## Executive Command Center (Widgets)

| Widget | Status | Notes |
|--------|--------|-------|
| **Tenant Health** | ✅ | **Now clean** — removed `0.74` hardcoded fallback. Shows "No health data available" when API unavailable. |
| **SLA Risk Heatmap** | ✅ | **Now clean** — removed 24-cell `DEFAULT_PREDICTIONS`. Transforms real `SLARiskOverview` data. |
| **Cost Governance** | ✅ | **Now clean** — removed `$7,340/$10,000` hardcoded budget. Shows "No cost data available". |
| **AI Quality Gate** | ✅ | **Now clean** — removed `87%` benchmark / `3.2%` hallucination fallback. Shows "No AI quality data available". |
| **Contract Exposure** | ✅ | Already clean — proper null state. |
| **Operational Anomalies** | ✅ | **Now clean** — uses prop data instead of ignoring it with local state. |
| **Reviewer Load** | ✅ | Already clean — proper null state. Fixed prop type. |
| **Executive Alert Center** | ✅ | Real API via `useAlertCenter` hook. |

## Governance

| Module | Status | Notes |
|--------|--------|-------|
| **Compliance** | ❌ | No API integration yet |
| **Governance** | ❌ | No API integration yet |
| **Relationships** | ❌ | No API integration yet |
| **Workflows** | ❌ | No API integration yet |

## Administration

| Module | Status | Notes |
|--------|--------|-------|
| **Admin Console** | ❌ | No API integration yet |
| **Settings** | ❌ | No API integration yet |
| **Tenant Config** | ❌ | No API integration yet |
| **AI Ops** | ❌ | No API integration yet |

---

## Mock Data Purge Summary

### Removed (this session)

| File | What was removed |
|------|-----------------|
| `TenantHealthWidget.tsx` | `{ composite: 0.74, ... }` — 6 hardcoded dimension values |
| `CostGovernanceSnapshotWidget.tsx` | `DEFAULT_DATA` — budget $7,340/$10,000, burn rate $285.50 |
| `AIQualityGateWidget.tsx` | `DEFAULT_DATA` — 87% benchmark, 3.2% hallucination rate, regression counts |
| `SLARiskHeatmapWidget.tsx` | `DEFAULT_PREDICTIONS` — 24 hardcoded SLA breach cells across 5×5 grid |
| `ReviewerLoadWidget.tsx` | `DEFAULT_DATA` — Sarah Chen, Mike Johnson, Emily Rodriguez fake reviewers |
| `AnomalyFeedWidget.tsx` | `MOCK_ANOMALIES` — empty array + ignored prop (now uses prop data) |
| `WorkflowIntelligenceDashboard.tsx` | All 5 tab components — latency table, queue depths, fake reviewers, approval delays, 68%/87.3% automation metrics |

### Previously Clean

| File | Status |
|------|--------|
| `OperationalCommandCenter.tsx` | Real API — `useReviewDashboard` |
| `ExecutiveCommandCenter.tsx` | Real API — executive aggregation layer |
| `ContractExposureWidget.tsx` | Proper null state |
| `ExecutiveAlertCenter.tsx` | Real API — `useAlertCenter` |

### Still Needs Work

| Module | Priority | Notes |
|--------|----------|-------|
| **Reviewer Ops** | High | Entirely hardcoded — needs API hook |
| **Policy Engine** | Medium | No API integration |
| **Search & Discovery** | Medium | No API integration |
| **Benchmarks** | Medium | No API integration |
| **Portfolio** | Medium | No API integration |
| **Governance group** | Low | 4 modules, all need APIs |
| **Administration group** | Low | 4 modules, all need APIs |
