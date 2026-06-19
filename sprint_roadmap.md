# ContractEdge — Sprint Roadmap (Post-RC1)

**Date:** June 18, 2026
**Status:** Release Candidate 1 Complete

The platform has reached RC1 quality with:
- Enterprise-grade architecture, workflow, security model
- Near enterprise-grade UX
- 16 areas scoring 97–100

Every sprint from this point should satisfy at least one of:
1. **Saves users time** (automation)
2. **Improves governance** (compliance/audit)
3. **Generates business value** (reporting, exports, insights)

---

## Sprint 26 — Intelligent Playbook Assignment (Highest Priority)

**Goal:** Eliminate manual playbook selection by automatically recommending the best playbook during contract upload and review creation.

### 1. Contract Type Detection
Detect contract type using AI + rule-based heuristics. Support at minimum:
- NDA, MSA, SOW, Purchase Agreement, Vendor Agreement
- Employment Agreement, Service Agreement, Data Processing Agreement
- Lease, Amendment, Unknown

### 2. Confidence Score
```json
{
  "contract_type": "NDA",
  "confidence": 0.94,
  "reasoning": ["Confidentiality clause", "Return of information", "Non-use language"]
}
```

### 3. Playbook Assignment Mapping
Database table: `contract_type → playbook`
- Contract Type, Playbook, Priority, Enabled, Notes
- No hardcoded mappings — fully configurable

### 4. Suggestion UI
After upload, display:
- Detected Contract Type
- Suggested Playbook
- Confidence percentage
- Buttons: **Accept**, **Override**, **Run Review**

### 5. Override Audit
When user overrides, record:
- Suggested Playbook, Selected Playbook, User, Timestamp, Reason

### 6. Low Confidence Handling
If confidence < 70%: show "Unable to confidently determine contract type" and require manual selection.

### 7. Version Pinning
When review starts, store `playbook_version_id`. Never change existing reviews after playbook updates.

### 8. Tests
- NDA → NDA Playbook
- MSA → Commercial Playbook
- Employment → HR Playbook
- Unknown → Manual Selection
- Override audit recorded
- Existing reviews remain pinned after playbook update

---

## Sprint 27 — Enterprise Search

**Goal:** A single search box that finds everything.

- Search contracts, findings, obligations, clauses, suppliers, review IDs, contract numbers
- Filters, saved searches, highlighted matched text
- Builds on existing search infrastructure (hybrid vector + BM25 + ILIKE fallback)

---

## Sprint 28 — Reporting & Exports

**Goal:** Create immediate business value through exports.

### Executive Reports (PDF)
- Executive Summary
- Contract Risk Report
- Review Report
- Obligation Register
- Compliance Report

### Excel Exports
- Findings Export
- Obligations Export
- Dashboard Export

### Scheduling
- Weekly email delivery
- Monthly summary

---

## Sprint 29 — Customer Onboarding

**Goal:** Dramatically improve first impressions.

- First login wizard
- Demo contracts (40–50 realistic contracts across types)
- Guided tour
- Sample playbooks, dashboards, obligations

---

## Sprint 30 — Production Hardening

**Goal:** Prepare for first real customer.

### Performance
- Query optimization, pagination, lazy loading, virtual scrolling

### Security
- Rate limiting, audit coverage, CSRF, security headers
- Password policy, session timeout

### Observability
- Error dashboard, API timing, slow query log, background job monitor

### Backup
- Restore testing, export/import, disaster recovery

---

## Sprint 31 — Customer Success Features (Very High ROI)

### Email Templates
Admin-editable templates for:
- Review Assigned, Review Approved, Contract Approved
- Obligation Due, Obligation Overdue, Contract Expiring

### SLA Engine
Auto-display:
- Reviews due today, Overdue reviews
- Contracts expiring in 30 days, Obligations overdue

### Bulk Operations
- Bulk assign, bulk approve, bulk archive
- Bulk obligation update, bulk export

---

## Strategic Recommendation

**Before Sprint 26:** Spend one day creating **40–50 realistic contracts** across different types (NDAs, MSAs, SOWs, DPAs, vendor agreements, employment agreements, etc.). Use them as the permanent regression suite. Every future sprint should be validated against this dataset.

---

## Not Building Next

These do not materially improve adoption at this stage:
- AI chatbot, Dark mode, Fancy animations
- More dashboards, More colors, Mobile app, Browser extensions

---

## Overall Roadmap

| Sprint | Focus | Priority |
|--------|-------|----------|
| 26 | Intelligent Playbook Assignment | ⭐⭐⭐⭐⭐ |
| 27 | Enterprise Search | ⭐⭐⭐⭐⭐ |
| 28 | Reports & Export | ⭐⭐⭐⭐ |
| 29 | Customer Onboarding | ⭐⭐⭐⭐ |
| 30 | Production Hardening | ⭐⭐⭐⭐⭐ |
| 31 | Customer Success Features | ⭐⭐⭐⭐ |
