# Policy Engine Phase 1 — Verification Checklist

Use this checklist to validate the Policy Engine after Phase 1 implementation.
Prerequisites: backend running, migration `h3i4j5k6l7m8` applied, policy seed data loaded.

## Setup

```bash
# Apply migration
cd backend && alembic upgrade head

# Seed playbooks/rules (if empty)
cd backend && PYTHONPATH=. .venv/bin/python -m scripts.seed_policy_data

# Backfill finding↔policy linkage on existing reviews
cd backend && PYTHONPATH=. .venv/bin/python -m app.scripts.enrich_policy_linkage

# Frontend: mock data disabled
# frontend/.env.local → NEXT_PUBLIC_USE_MOCK_DATA=false
```

---

## 1. Dashboard Tab

| Check | How to verify | Pass criteria |
|-------|---------------|---------------|
| Playbook count | Open Policy Engine → Dashboard | Shows ≥1 playbook (not empty skeleton) |
| Evaluation metrics | Dashboard KPI cards | Evaluations count reflects `/playbooks/evaluations` data |
| Violation summary | Open vs resolved counts | Numbers match evaluations with `deviations_found > 0` |
| Category breakdown | Category chips | Practice areas from seeded playbooks visible |

**API:** `GET /api/v1/playbooks/`, `GET /api/v1/playbooks/evaluations`

---

## 2. Policies Tab

| Check | How to verify | Pass criteria |
|-------|---------------|---------------|
| List loads | Policies tab | Commercial, Data Privacy, Procurement playbooks listed |
| Lifecycle badge | Each row | Shows draft/review/published from `status` field |
| Detail drawer | Click a policy | Drawer opens with name, description, jurisdiction |
| Edit saves | Edit name → Save | `PATCH /playbooks/{id}` succeeds (not PUT 405) |

**API:** `GET /api/v1/playbooks/`, `PATCH /api/v1/playbooks/{id}`

---

## 3. Rules Tab

| Check | How to verify | Pass criteria |
|-------|---------------|---------------|
| Rules populate | Rules tab | Table shows seeded rules (IP, Liability, DPA, SLA, etc.) |
| Not from empty `p.rules` | Network tab | Data from `GET /playbooks/rules`, not playbook list stub |
| Search works | Search "liability" | Filters to liability-related rules |
| Policy link | Click policy name | Opens policy detail drawer |

**API:** `GET /api/v1/playbooks/rules?page_size=200`

---

## 4. Clause Requirements Tab

| Check | How to verify | Pass criteria |
|-------|---------------|---------------|
| Clause standards | Clause Reqs tab | Shows indemnification, liability cap, DPA clauses |
| Playbook linkage | Click policy | Navigates to correct playbook |

**API:** Clause intelligence hooks + `clause_standards` table

---

## 5. Violations Tab

| Check | How to verify | Pass criteria |
|-------|---------------|---------------|
| Evaluations listed | Violations tab | Shows policy evaluations with deviations |
| Deviation detail | Expand a row | `deviations` JSON visible in evaluation detail |
| Review linkage | Note `review_id` on evaluation | Matches a contract review when enriched |

**API:** `GET /api/v1/playbooks/evaluations`

---

## 6. Traceability Tab

| Check | How to verify | Pass criteria |
|-------|---------------|---------------|
| Chains load | Traceability tab | One card per playbook with real counts |
| Rule count | Each chain | Matches `policy_rules` count for playbook |
| Finding count | After enrich script | `finding_count > 0` for playbooks with matched findings |
| Redline count | Reviews with redlines | `redline_count` reflects linked redlines (not hardcoded 0) |

**API:** `GET /api/v1/playbooks/traceability`

---

## 7. Simulation Tab

| Check | How to verify | Pass criteria |
|-------|---------------|---------------|
| Playbook picker | Simulation tab | Lists seeded playbooks |
| Upload picker | Select an upload | Lists contract uploads |
| Run simulation | Click Run | `POST /playbooks/evaluate?simulation_mode=true` returns results |
| Results panel | After run | Shows rules_passed, rules_failed, deviations |

**API:** `POST /api/v1/playbooks/evaluate?playbook_id=…&upload_id=…&simulation_mode=true`

---

## Review ↔ Policy Integration

| Check | How to verify | Pass criteria |
|-------|---------------|---------------|
| Policy violations API | `GET /reviews/{id}/policy-violations` | Returns violations with `policy_name`, `rule_id`, `traceability` |
| Finding linkage persisted | DB: `review_findings.rule_id` | Non-null after first violations fetch or enrich script |
| AI Review findings | `/reviews/ai-workspace` → Findings | Policy badge on findings with linked rules |
| Classic review findings | Review workspace → Findings table | "Policy Linkage" panel when `playbook_id` set |
| Accept blocked on bad mapping | Redline with invalid_mapping | Accept hidden (separate integrity feature) |

**API:** `GET /api/v1/reviews/{review_id}/policy-violations`, `GET /api/v1/reviews/{review_id}/findings`

---

## Quick curl smoke test

```bash
# List tenant rules
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/playbooks/rules | jq '.pagination.total'

# Traceability
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/playbooks/traceability | jq '.chains[0]'

# Review violations (replace REVIEW_ID)
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/reviews/REVIEW_ID/policy-violations | jq '.violations | length'
```

---

## Known Phase 1 limitations

- Policy toggle endpoint (`POST /playbooks/{id}/toggle`) not yet implemented
- Approval workflow buttons in drawer are UI-only
- Simulation drawer still uses demo profile in some sub-views
- Create Policy (`+`) button not wired

These are deferred to Phase 2.
