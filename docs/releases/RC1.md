# ContractEdge — Release Candidate 1 (RC1)

**Date:** June 3, 2026  
**Tag:** `rc1`  
**Commit:** `2c3ad35` (Sprint 19 Phase 1-2)  
**Database Migration Head:** `2dfddf86fae7` (negotiation tables)  
**Backup File:** `rc_backup.sql` (3,420 lines)  
**Validation:** 21/21 RC checks passed

---

## Features Included

### Core Contract Review (100%)
- Document upload and ingestion pipeline
- AI-powered analysis with findings and redlines
- Review queue with role-based assignment
- Multi-stage approval workflow (legal → executive)
- Status tracking with full state machine
- SLA monitoring and breach detection

### Workflow Platform (100%)
- Workflow execution engine with state machine runtime
- Persistent workflow instances (survive restart)
- Workflow packs (procurement, healthcare, SaaS, finance)
- Approval gates with timeout and escalation
- SLA timers and breach detection
- Compensation/Saga rollback support
- Dashboard and metrics APIs

### Negotiation Platform (100%)
- Full negotiation lifecycle: drafting → review → negotiating → approved → executed
- Redline management (create, accept, reject, supersede)
- Issue tracking with severity and escalation
- Comment threads with nested replies
- Participant management with role-based access
- Stage transition validation (invalid transitions blocked)
- Audit logging via shared governance framework
- Workflow integration (negotiation creates workflow instances)

### Notifications & Email (95%)
- 8 HTML email templates (assignment, approval, escalation, etc.)
- Celery worker with 3-attempt retry
- Tenant-level email redirect
- Admin console email queue dashboard
- Resend API integration

### Audit & Governance (95%)
- Shared `governance_audit_events` table across all domains
- Review status change tracking
- Negotiation event logging (creation, stage changes, redlines, issues)
- Audit events survive record deletion
- Admin audit log endpoint with filtering

### AI Operations — Cost Analytics (100%)
- Total cost, tokens, and request tracking
- Cost breakdown by model
- Latency metrics (avg, min, max per model)
- Data sourced from `ai_execution_runs` (22 runs, 29K tokens)

### AI Operations — Safety Analytics (100%)
- Approval rate and confidence tracking
- Execution success rate monitoring
- Approval breakdown by type
- Data sourced from `ai_approvals` (3 approvals) and `ai_execution_runs`

---

## Database Schema

### Migration History
| Revision | Description |
|----------|-------------|
| `5772cbcfe2b2` | Initial schema |
| `e7b21230c345` | Performance indexes |
| `3a8f6d9e1b2c` | RLS for tenant isolation |
| `f4a1c8e2b9d0` | Admin console tables |
| `c3d4e5f6a7b8` | Branch point |
| `8d458e3067ef` | Email redirect tenant settings |
| `df2e1aba9afc` | Email queue table |
| `47565f229d4b` | Finding feedback columns |
| `cacd9f177b1a` | Historical workflow_stage repair |
| `f8a9b0c1d2e3` | Benchmark job enum types |
| `6ff4692ea980` | Workflow tables |
| `2dfddf86fae7` | Negotiation tables |

### Key Tables (50+ total)
- `contract_reviews` — Core review records
- `review_findings` — AI-generated findings
- `review_redlines` — Redline changes
- `review_status_history` — Status change audit
- `workflow_instances` — Persisted workflow state
- `workflow_instance_steps` — Step-level execution tracking
- `workflow_execution_logs` — Workflow audit events
- `negotiation_sessions` — Negotiation aggregate root
- `negotiation_versions` — Document versions
- `negotiation_redlines` — Proposed changes
- `negotiation_issues` — Issue tracking
- `negotiation_comments` — Comment threads
- `negotiation_participants` — Session participants
- `email_queue` — Outbound email queue
- `governance_audit_events` — Cross-domain audit trail
- `ai_execution_runs` — AI model execution records
- `ai_approvals` — AI approval decisions
- `ai_findings` — AI analysis findings

---

## API Endpoints (200+ total)

### Core Review (`/api/v1/reviews`)
- CRUD for reviews, findings, redlines, comments, approvals, escalations
- Workflow advance, command center, queue, recommendations

### Workflows (`/api/v1/workflows`, `/api/v1/workflow-packs`)
- Workflow pack management (CRUD, activate, deactivate)
- Workflow runtime (start, cancel, approve, reject)
- Dashboard, metrics, stages, bottlenecks

### Negotiations (`/api/v1/negotiations`)
- Full CRUD for sessions, redlines, issues, comments, participants
- Stage transitions with validation
- KPI aggregation, activity/audit log

### AI Governance (`/api/v1/ai-governance`)
- Prompt registry and versioning
- Evaluation datasets and runs
- Model audit log
- Quality dashboard
- Cost summary
- Safety summary
- Hallucination detection
- Quality gate evaluation

### Admin (`/api/v1/admin`)
- User management (CRUD)
- Role management (CRUD)
- Tenant settings
- System health
- Diagnostics
- Audit logs

### Other Domains
- Ingestion, contracts, clause library, obligations
- Compliance, human oversight, AI governance
- Search, analytics, benchmarks
- Exports, notifications

---

## Known Limitations

| Area | Limitation | Impact |
|------|-----------|--------|
| AI Routing | Not implemented | Model selection is hardcoded (gpt-4o only) |
| AI Quality Analytics | Not implemented | No hallucination rate dashboard |
| AI Benchmarks | No data (`benchmark_scores` empty) | Benchmark tab shows no data |
| Relationships | Not implemented | No relationship graph feature |
| Tenant Config | Router exists but unwired | Feature flags not configurable via API |
| Settings | Static UI only | Profile, notifications, security not functional |
| Email Delivery | Queue empty in RC session | Requires lifecycle events to trigger |
| Model Audit Log | 0 rows | `model_audit_log` table empty — cost data from `ai_execution_runs` instead |

---

## Open Items

1. **Production hardening** — See `production_readiness_review.md`
2. **AI Routing** — New capability for model selection intelligence
3. **AI Quality** — Hallucination detection storage and aggregation
4. **Relationships** — Contract relationship graph
5. **Benchmarks** — Seed and populate benchmark scoring data
6. **Tenant Config** — Wire existing router in `main.py`
7. **Settings** — Connect static UI to backend endpoints

---

## Deployment

### Prerequisites
- Python 3.11+
- PostgreSQL 16
- Redis 7+
- Node.js 20+ (frontend)

### Environment Variables
See `backend/.env.example` and `frontend/.env.local.example`

### Docker
```bash
docker compose up -d
```

### Manual
```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## Verification

RC1 was validated with 21 automated tests covering:
- Negotiation lifecycle (9 checks)
- Contract review accessibility (3 checks)
- Workflow persistence (3 checks)
- Audit trail completeness (2 checks)
- AI Cost metrics accuracy (2 checks)
- AI Safety metrics accuracy (2 checks)

All 21 checks passed. See `release_candidate_review.md` for full results.
