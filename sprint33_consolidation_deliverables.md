================================================================================
  SPRINT 33.1 — WORKFLOW CONSOLIDATION
  Architecture & Migration Deliverables
================================================================================

Date: 2026-06-27
Author: Workflow Audit + Consolidation Implementation


================================================================================
1. ARCHITECTURE DIAGRAM
================================================================================

BEFORE CONSOLIDATION (Two disconnected systems):

  ┌─────────────────────────────────┐   ┌──────────────────────────────────┐
  │     REVIEW DOMAIN               │   │     WORKFLOW RUNTIME ENGINE      │
  │                                 │   │                                  │
  │  ReviewService.update_status()  │   │  WorkflowEngine.start_workflow() │
  │         │                       │   │         │                        │
  │         ▼                       │   │         ▼                        │
  │  WorkflowState.validate_trans() │   │  _execute_steps() [async]        │
  │         │                       │   │         │                        │
  │         ▼                       │   │         ▼                        │
  │  contract_reviews.status        │   │  workflow_instances              │
  │  (single column)                │   │  (6 tables)                      │
  │                                 │   │                                  │
  │  USED BY: Everything            │   │  USED BY: Negotiation only       │
  └─────────────────────────────────┘   └──────────────────────────────────┘
            ✗ NOT CONNECTED ✗


AFTER CONSOLIDATION (Unified via consolidator):

  ┌─────────────────────────────────────────────────────────────────────┐
  │                     EXISTING API SURFACE                            │
  │  ReviewService.update_status()  (unchanged signature)               │
  │  NegotiationService (unchanged)                                      │
  └──────────────────────────┬──────────────────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │              WORKFLOW CONSOLIDATOR (NEW)                            │
  │                                                                     │
  │  WorkflowConsolidator                                              │
  │    ├── ensure_workflow_instance()  — creates shadow instance        │
  │    ├── record_transition()        — syncs review→workflow           │
  │    ├── get_workflow_status()      — consolidated status API         │
  │    └── resolve_workflow_pack()    — DB-backed pack resolution       │
  │                                                                     │
  │  This is the ONLY module that knows about both state machines.      │
  └──────────────────────────┬──────────────────────────────────────────┘
              ┌──────────────┴──────────────┐
              │                              │
              ▼                              ▼
  ┌──────────────────────┐   ┌──────────────────────────┐
  │  REVIEW STATE        │   │  WORKFLOW RUNTIME        │
  │  MACHINE (unchanged) │   │  ENGINE (unchanged)       │
  │                      │   │                           │
  │  validate_transition │   │  WorkflowEngine           │
  │  guard_mutable       │   │  WorkflowPersistenceAdapter│
  │  audit_trail         │   │  Saga compensation        │
  │  notify_service      │   │  SLA timers               │
  └──────────────────────┘   └───────────────────────────┘
              │                              │
              ▼                              ▼
  ┌──────────────────────┐   ┌──────────────────────────┐
  │  contract_reviews    │   │  workflow_instances      │
  │  (source of truth)   │   │  (shadow/index)          │
  └──────────────────────┘   └──────────────────────────┘


================================================================================
2. MODULE DEPENDENCY DIAGRAM
================================================================================

  app.domains.review.service
       │
       ├── app.domains.review.workflow     (WorkflowState, validate_transition)
       ├── app.domains.review.repository   (ReviewRepository)
       ├── app.domains.review.audit_trail  (AuditTrailService)
       │
       └── app.domains.workflow.consolidator  ★ NEW ★
                │
                ├── app.domains.workflow.models      (WorkflowInstance, etc.)
                ├── app.domains.review.workflow      (ReviewState enum mapping)
                └── app.domains.workflow.engine      (WorkflowStatus enum only)


  app.domains.negotiation.service
       │
       ├── app.domains.negotiation.models
       │
       └── app.domains.workflow.engine      (WorkflowEngine — unchanged)
            │
            └── app.domains.workflow.persistence  (unchanged)


  Dependency rule:
    review.service → consolidator → workflow.models
    review.service → review.workflow (direct, for transition validation)
    consolidator → review.workflow (for ReviewState enum only)
    consolidator → workflow.models (for WorkflowInstance ORM)

  NO circular dependencies introduced.


================================================================================
3. UPDATED EXECUTION FLOW
================================================================================

A. Review Creation (get_or_create_review):

  1. review_repo.create_review()          → contract_reviews row created
  2. consolidator.ensure_workflow_instance()  → workflow_instances row created
  3. Review proceeds as before

B. Review Status Transition (update_status):

  1. Validate transition (existing)
     - Guard: rejection reason, close/archive reason, open obligations
     - validate_transition() via WorkflowState machine
  2. Persist to contract_reviews (existing)
     - review_repo.update_status()
     - audit_trail.record_transition()
     - notify_service (for close/archive)
  3. Shadow workflow instance (NEW — non-blocking)
     - consolidator.record_transition()
     - Updates workflow_instances.current_step
     - Completes previous WorkflowInstanceStep
     - Creates next WorkflowInstanceStep
     - Sets terminal states (ARCHIVED → COMPLETED, REJECTED → FAILED)
     - Failures are logged but DO NOT block the API response

C. Workflow Status Query (new consolidated endpoint):

  1. consolidator.get_workflow_status()
     - Reads contract_reviews.status
     - Reads workflow_instances + workflow_instance_steps
     - Returns merged response with both perspectives


================================================================================
4. MIGRATION SUMMARY
================================================================================

Data Migration Required: NONE
  - contract_reviews.status remains the source of truth
  - workflow_instances is created as a shadow/index
  - Existing records are NOT backfilled (optional future task)

Schema Migration Required: NONE
  - All tables already exist
  - No new columns or tables added

Code Migration:
  - NEW FILE:  backend/app/domains/workflow/consolidator.py
  - MODIFIED:  backend/app/domains/review/service.py
    - Added 2 calls to WorkflowConsolidator (create + transition)
    - Both are non-blocking (try/except with log warning)

Configuration Changes: NONE
  - No new settings or environment variables

Rollback Plan:
  - Remove the 2 try/except blocks from review/service.py
  - Delete consolidator.py
  - Everything else continues working unchanged


================================================================================
5. REGRESSION CHECKLIST
================================================================================

All existing functionality must continue working:

  Review Lifecycle:
  [ ] GET /api/v1/reviews/{id} — returns review detail
  [ ] PUT /api/v1/reviews/{id}/status — transitions work
  [ ] POST /api/v1/reviews/{id}/status — status updates
  [ ] Rejection requires reason
  [ ] Close/archive requires reason ≥ 5 chars
  [ ] Close/archive blocked by open obligations
  [ ] Close/archive override works
  [ ] Audit trail recorded for every transition

  Workflow Runtime:
  [ ] POST /api/v1/workflows — starts new instance
  [ ] GET /api/v1/workflows — lists instances
  [ ] GET /api/v1/workflows/{id} — gets instance detail
  [ ] POST /api/v1/workflows/{id}/cancel — cancels instance
  [ ] POST /api/v1/workflows/approvals/resolve — resolves approval
  [ ] GET /api/v1/workflows/approvals/pending — pending approvals

  Negotiation:
  [ ] Negotiation sessions create workflow instances
  [ ] Stage transitions update workflow status
  [ ] Event handler auto-creates sessions on review approval

  Workflow Packs:
  [ ] GET /api/v1/workflow-packs — lists packs
  [ ] POST /api/v1/workflow-packs — creates pack
  [ ] POST /api/v1/workflow-packs/activate — activates pack

  Consolidation (NEW):
  [ ] Workflow instance created when review is created
  [ ] Workflow instance updated when review transitions
  [ ] Terminal review states (archived, rejected) reflected in workflow
  [ ] Non-blocking on failure (logged, not raised)
  [ ] Existing review API unchanged


================================================================================
6. REMAINING WORK BEFORE CONFIGURATION UI
================================================================================

Sprint 33.1 — Consolidation (BACKEND — this phase):
  [X] Unified WorkflowConsolidator class
  [X] Review → Workflow state mapping (REVIEW_STATE_TO_STAGE)
  [X] Workflow instance creation on review create
  [X] Workflow instance update on review transition
  [X] Non-blocking failure handling
  [ ] Workflow pack resolution from database (resolve_workflow_pack)
  [ ] Migration of 3 hardcoded definitions to DB records
  [ ] JSON rule evaluator for condition_expression
  [ ] Routing abstraction (strategy interface)
  [ ] Consolidated status endpoint
  [ ] Integration tests

Sprint 33.2 — Configuration (FRONTEND + API):
  [ ] Workflow definition management UI
  [ ] Routing rules configuration
  [ ] Approval gate configuration
  [ ] SLA / escalation configuration
  [ ] Publish/version management
  [ ] Simulator

================================================================================
END OF DELIVERABLES
================================================================================
