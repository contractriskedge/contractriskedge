# Sprint 23 Task 3.2B — Review Workspace Gap Analysis

**Date**: 2026-06-05  
**Objective**: Audit existing ReviewWorkspace and identify gaps vs target layout  
**Rule**: Do NOT build new components if equivalent functionality already exists

---

## Target Layout

```
+--------------------------------------------------+
| Contract Header                                  |
+--------------------------------------------------+
| Risk Score | Risk Level | Findings Count         |
+--------------------------------------------------+
| Findings           | Contract Viewer             |
|--------------------|-----------------------------|
| High Risk          | PDF/Document                |
| Medium Risk        |                             |
| Low Risk           |                             |
+--------------------------------------------------+
| Redlines                                         |
+--------------------------------------------------+
| Recommendations                                  |
+--------------------------------------------------+
```

---

## Component Inventory

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| ReviewWorkspace | `components/review/ReviewWorkspace.tsx` | 485 | ✅ Exists |
| ContractSummary | `components/review/ContractSummary.tsx` | 278 | ✅ Exists |
| FindingsTable | `components/review/FindingsTable.tsx` | 608 | ✅ Exists |
| FindingsNavigator | `components/review/FindingsTable.tsx` | (inline) | ✅ Exists |
| RedlinesPanel | `components/review/RedlinesPanel.tsx` | 432 | ✅ Exists |
| RedlineCard | `components/review/RedlineCard.tsx` | — | ✅ Exists |
| RiskBreakdownPanel | `components/review/RiskBreakdownPanel.tsx` | 1424 | ✅ Exists |
| ReviewActions | `components/review/ReviewActions.tsx` | 693 | ✅ Exists |
| EvidenceViewer | `components/review/EvidenceViewer.tsx` | 168 | ✅ Exists |
| ActivityTimeline | `components/review/ActivityTimeline.tsx` | 371 | ✅ Exists |
| DocumentVersionsPanel | `components/review/DocumentVersionsPanel.tsx` | — | ✅ Exists |
| ImmutableBanner | `components/review/ImmutableBanner.tsx` | — | ✅ Exists |
| CommentThread | `components/review/CommentThread.tsx` | — | ✅ Exists |
| ApprovalModal | `components/review/ApprovalModal.tsx` | — | ✅ Exists |
| EscalationModal | `components/review/EscalationModal.tsx` | — | ✅ Exists |
| VersionDiffViewer | `components/review/VersionDiffViewer.tsx` | — | ✅ Exists |
| InlineDiffViewer | `components/review/InlineDiffViewer.tsx` | — | ✅ Exists |
| RedlineEditModal | `components/review/RedlineEditModal.tsx` | — | ✅ Exists |

---

## Gap Analysis

### 1. Contract Header

| Aspect | Status | Details |
|--------|--------|---------|
| Document name | ✅ **Exists** | `ContractSummary` shows `review.document_name` |
| Vendor information | ❌ **Missing** | No vendor field in `ContractSummary` or `ReviewWorkspace` |
| Contract metadata | ⚠️ **Partial** | Shows upload date, reviewer, doc version, AI model, tokens |
| Upload date | ✅ **Exists** | `ContractSummary` shows `new Date(review.created_at).toLocaleDateString()` |
| Created by | ❌ **Missing** | `review.created_by` exists in API but is not displayed |
| Status badge | ✅ **Exists** | Color-coded status with `getStatusLabel()` |

**Gap**: Vendor information is not displayed. The `ContractRecord` type has a `vendor` field but `ReviewDetail` doesn't. The backend `GET /contracts` endpoint returns vendor info but `GET /reviews` doesn't include it.

**Fix**: Add vendor info from the contracts endpoint, or add `created_by` display to `ContractSummary`.

---

### 2. Risk Score Display

| Aspect | Status | Details |
|--------|--------|---------|
| Risk score number | ✅ **Exists** | `ContractSummary` shows risk score as percentage |
| Risk score gauge | ✅ **Exists** | `RiskBreakdownPanel` has `RiskGauge` component (ring gauge) |
| Risk level badge | ✅ **Exists** | `ContractSummary` has `severityColor()` with color-coded badges |
| Original AI risk | ✅ **Exists** | Shows "Original AI Risk" when in remaining exposure mode |
| Current contract risk | ✅ **Exists** | Shows "Current Contract Risk" (remaining exposure) |
| Risk score trend | ⚠️ **Partial** | `RiskBreakdownPanel` shows mitigated vs remaining but no trend arrow |

**Gap**: No single row of KPI cards at the top showing Risk Score, Risk Level, Findings Count, Redlines Count in a compact format.

**Fix**: Add a KPI card row above `ContractSummary` (or integrate into it) showing:
- Risk Score (percentage + color badge)
- Risk Level (Critical/High/Medium/Low/Minimal)
- Findings Count (with severity breakdown)
- Redlines Count

---

### 3. Findings Summary

| Aspect | Status | Details |
|--------|--------|---------|
| Findings list | ✅ **Exists** | `FindingsTable` — full table with severity coding |
| Severity filter | ✅ **Exists** | Dropdown filter by severity |
| Resolution filter | ✅ **Exists** | Dropdown filter by resolution status |
| Pagination | ✅ **Exists** | 20 per page with page controls |
| Inline resolve | ✅ **Exists** | Resolve/dismiss buttons per finding |
| Expandable details | ✅ **Exists** | Click to expand full description + recommendation |
| Severity breakdown | ⚠️ **Partial** | `RiskBreakdownPanel` shows severity counts in exposure section, but no compact summary card |
| Findings count badge | ✅ **Exists** | Tab badge shows count |
| Finding-to-chunk linking | ✅ **Exists** | `onFindingSelect` highlights chunk in contract viewer |

**Gap**: No compact "Findings Summary" card showing severity distribution (Critical: N, High: N, Medium: N, Low: N) at a glance.

---

### 4. Redlines Summary

| Aspect | Status | Details |
|--------|--------|---------|
| Redlines list | ✅ **Exists** | `RedlinesPanel` — collapsible cards |
| Risk-based grouping | ✅ **Exists** | `RiskGroupHeader` groups by risk level |
| Confidence indicators | ✅ **Exists** | `ConfidencePill` shows placement confidence |
| Operation badges | ✅ **Exists** | Insertion markers, operation type badges |
| Accept/reject/modify | ✅ **Exists** | `RedlineEditModal` for status changes |
| Redline-to-chunk linking | ✅ **Exists** | `onRedlineSelect` → `locateRedline()` → scroll to chunk |
| Redlines count badge | ✅ **Exists** | Tab badge shows count |

**Gap**: No compact "Redlines Summary" card showing accepted/rejected/pending counts.

---

### 5. Recommendations Panel

| Aspect | Status | Details |
|--------|--------|---------|
| Risk mitigation suggestions | ✅ **Exists** | `RiskBreakdownPanel` has `MitigationSuggestions` section |
| Top recommended actions | ✅ **Exists** | `TopRecommendedActions` widget with priority ordering |
| Generate mitigation redline | ✅ **Exists** | `useGenerateMitigationRedline` mutation |
| Dedicated "Recommendations" tab | ❌ **Missing** | No separate recommendations tab — mitigation suggestions are inside `RiskBreakdownPanel` |

**Gap**: Recommendations are embedded within `RiskBreakdownPanel` rather than having their own tab. This is a design choice, not a missing feature. The data is present.

---

### 6. Executive Summary Section

| Aspect | Status | Details |
|--------|--------|---------|
| Contract summary panel | ✅ **Exists** | `ContractSummary` shows metadata |
| Risk breakdown | ✅ **Exists** | `RiskBreakdownPanel` shows full risk analysis |
| Review progress | ✅ **Exists** | Progress bar in `ContractSummary` |
| Finalized version info | ✅ **Exists** | Green banner for approved/finalized contracts |
| SLA status | ✅ **Exists** | `review.sla_status` and `review.sla_breached` available |
| Priority indicator | ⚠️ **Partial** | `review.priority` exists but not prominently displayed |

**Gap**: No dedicated executive summary section. However, the `ContractSummary` + `RiskBreakdownPanel` together provide equivalent information.

---

### 7. Review Status Indicators

| Aspect | Status | Details |
|--------|--------|---------|
| Status badge | ✅ **Exists** | Color-coded in `ContractSummary` |
| Immutable banner | ✅ **Exists** | `ImmutableBanner` for finalized/approved/rejected |
| Progress bar | ✅ **Exists** | Review completion progress in `ContractSummary` |
| SLA status | ✅ **Exists** | `sla_status` field available from API |
| Overdue indicator | ✅ **Exists** | `overdue_hours` field available from API |

---

### 8. Review Actions

| Aspect | Status | Details |
|--------|--------|---------|
| Assign reviewer | ✅ **Exists** | Modal with assignee ID + role selector |
| Escalate | ✅ **Exists** | `EscalationModal` with reason + target |
| Approve/Reject | ✅ **Exists** | `ApprovalModal` with decision + comments + conditions |
| Add comment | ✅ **Exists** | Inline comment form |
| Soft delete | ✅ **Exists** | With reason |
| Workflow routing | ✅ **Exists** | Send to Legal/Procurement/Security |
| Counterparty revision | ✅ **Exists** | Formal revision request |
| Negotiation package | ✅ **Exists** | Export ZIP |
| Export memo | ✅ **Exists** | Export audit report |
| Re-analyze | ✅ **Exists** | Button in nav bar |
| Permission gating | ✅ **Exists** | `hasPermission()` checks on all actions |

---

## Summary Table

| Feature | Target | Actual | Gap | Effort |
|---------|--------|--------|-----|--------|
| Contract Header | Document name, vendor, metadata | Document name + metadata only | **Vendor info missing** | Small |
| Risk Score | Score + level display | Score gauge + level badge in `ContractSummary` and `RiskBreakdownPanel` | ✅ Covered | None |
| Risk Level | Badge | Color-coded severity badge | ✅ Covered | None |
| Findings Count | Count + severity breakdown | Count in tab badge, severity in `FindingsTable` filter | **No compact severity summary card** | Small |
| Redlines Count | Count | Count in tab badge | ✅ Covered | None |
| Findings Table | Filterable, sortable, paginated | Full implementation with inline resolve | ✅ Covered | None |
| Redlines Panel | Grouped, actionable | Full implementation with confidence + insertion markers | ✅ Covered | None |
| Recommendations | Suggestions panel | Embedded in `RiskBreakdownPanel` | ✅ Covered (design choice) | None |
| Executive Summary | Overview section | `ContractSummary` + `RiskBreakdownPanel` | ✅ Covered | None |
| Review Status | Badge + progress | Status badge + progress bar + immutable banner | ✅ Covered | None |
| Review Actions | Full action set | 11 action types with permission gating | ✅ Covered | None |
| Contract Viewer | Split-pane text viewer | Chunk-based viewer with highlight + locate | ✅ Covered | None |
| Evidence Viewer | Source text for findings | Full evidence browser with search | ✅ Covered | None |
| Activity Timeline | Audit trail | Full timeline with icons + actors | ✅ Covered | None |

---

## Files Requiring Modification

### High Priority (Actual Gaps)

| File | Change | Effort |
|------|--------|--------|
| `components/review/ContractSummary.tsx` | Add vendor info, created_by, priority display | **Small** (~20 lines) |
| `components/review/ReviewWorkspace.tsx` | Add KPI card row above ContractSummary | **Small** (~50 lines) |

### Low Priority (Nice-to-Have)

| File | Change | Effort |
|------|--------|--------|
| `components/review/FindingsTable.tsx` | Add severity distribution summary above table | **Small** (~30 lines) |
| `components/review/ReviewWorkspace.tsx` | Add Recommendations as a 6th tab | **Small** (~15 lines) |

---

## Estimated Effort

| Category | Effort |
|----------|--------|
| Vendor info in ContractSummary | ~20 min |
| KPI card row in ReviewWorkspace | ~30 min |
| Severity distribution in FindingsTable | ~20 min |
| Recommendations tab | ~15 min |
| **Total** | **~1.5 hours** |

---

## Recommended Implementation Order

1. **KPI card row** — Highest visibility, shows risk score + level + findings count + redlines count at a glance
2. **Vendor info** — Fills the most obvious data gap in ContractSummary
3. **Severity distribution** — Useful but lower priority
4. **Recommendations tab** — Nice-to-have, content already exists in RiskBreakdownPanel

---

## Conclusion

**The existing ReviewWorkspace is substantially complete.** Out of 12 target features:

- **9 are fully implemented** ✅
- **3 have minor gaps** ⚠️ (vendor info, compact KPI cards, severity summary)
- **0 are completely missing** ❌

The workspace already has 18 components totaling ~5,000+ lines of code covering findings, redlines, risk analysis, evidence, activity, versions, comments, approvals, escalations, and workflow routing. The gaps are cosmetic enhancements, not missing functionality.
