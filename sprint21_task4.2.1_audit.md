================================================================================
  SPRINT 21 TASK 4.2.1 — Root Cause Audit
  6 ReviewStatus Values Missing from PostgreSQL Enum
  Completed: June 4, 2026
================================================================================

ROOT CAUSE
───────────────────────────────────────────────────────────────────────────────

All 6 statuses were added to the Python ReviewStatus and WorkflowState enums
during workflow redesign (Sprints 17-20), but NO Alembic migration was ever
created to add them to the PostgreSQL `review_status` enum type.

The DB enum has 16 values. The Python enum has 22 values. 6 are missing.

================================================================================
  STATUS AUDIT TABLE
================================================================================

STATUS 1: ai_reviewed
───────────────────────────────────────────────────────────────────────────────

  Defined In:     models.py:41 (ReviewStatus), workflow.py:44 (WorkflowState)
  Maps To:        WorkflowState.AI_REVIEWED (also: ai_analyzed, review_ready)
  Referenced In:  models.py, workflow.py, test_state_transitions.py,
                  test_workflow_reliability.py
  Reachable?:     YES — from ANALYZING; can go to PROCUREMENT_REVIEW,
                  LEGAL_REVIEW, IN_REVIEW, CLOSED
  Persisted?:     NO — NOT in PostgreSQL enum
  Frontend?:      NO — frontend uses "ai_analyzed" instead
  Routes/Svc?:    NO
  Dead Code?:     PARTIALLY — WorkflowState uses it, but routes never set it.
                  DB rows use "ai_analyzed" instead. It's an alias.
  Recommendation: MAP_TO_EXISTING_STATUS — Remove from WorkflowState,
                  map ai_reviewed → AI_REVIEWED → ai_analyzed in DB.
                  All current logic already treats ai_analyzed as the
                  canonical "AI analysis complete" status.

  ─────────────────────────────────────────────────────────────────────────────
  Rationale: "ai_reviewed" was introduced as the WorkflowState name, but the
  DB already has "ai_analyzed" which serves the same purpose. The LEGACY_STATUS_MAP
  already maps ai_analyzed → AI_REVIEWED. Removing ai_reviewed from WorkflowState
  and using ai_analyzed as the canonical value would eliminate the gap.
  ─────────────────────────────────────────────────────────────────────────────


STATUS 2: analyzing
───────────────────────────────────────────────────────────────────────────────

  Defined In:     models.py:37 (ReviewStatus), workflow.py:42 (WorkflowState)
  Maps To:        WorkflowState.ANALYZING
  Referenced In:  models.py, workflow.py, router.py (progress endpoint),
                  service.py (re-analysis), test_state_transitions.py,
                  test_workflow_reliability.py, UploadWorkflow.tsx
  Reachable?:     YES — from UPLOADED/DRAFT; can go to AI_ANALYZED,
                  AI_REVIEWED, UPLOADED, CLOSED/ARCHIVED
  Persisted?:     NO — NOT in PostgreSQL enum
  Frontend?:      YES — but only as a local upload workflow stage, not as
                  a review status
  Routes/Svc?:    YES — router.py returns "analyzing" as a progress string;
                  service.py includes it in review_statuses_for_reanalysis
  Dead Code?:     NO — actively used as a transient state during AI analysis.
                  Reviews are in "analyzing" state briefly before moving to
                  ai_analyzed. The progress endpoint returns it.
  Recommendation: ADD_TO_DATABASE_ENUM — This is a real, active state that
                  reviews pass through. It's returned by route handlers and
                  used in service logic. Must be added to the DB enum.

  ─────────────────────────────────────────────────────────────────────────────
  Rationale: Unlike ai_reviewed which is an alias, "analyzing" is a distinct
  state that reviews actually pass through during AI processing. The router
  returns it from the progress endpoint. It cannot be removed or remapped.
  ─────────────────────────────────────────────────────────────────────────────


STATUS 3: legal_review
───────────────────────────────────────────────────────────────────────────────

  Defined In:     models.py:46 (ReviewStatus), workflow.py:46 (WorkflowState)
  Maps To:        WorkflowState.LEGAL_REVIEW (also: legal_approval)
  Referenced In:  models.py, workflow.py, workflows/router.py,
                  test_state_transitions.py, test_workflow_reliability.py,
                  workflow.ts (frontend), ReviewQueue.tsx, ReviewActions.tsx,
                  useReviews.ts
  Reachable?:     YES — from AI_REVIEWED, REVIEW_READY, AI_ANALYZED,
                  PROCUREMENT_REVIEW, IN_REVIEW, NEGOTIATION, SECURITY_REVIEW,
                  ESCALATED; can go to APPROVED, NEGOTIATION, REJECTED,
                  PROCUREMENT_REVIEW, ESCALATED, CLOSED
  Persisted?:     NO — NOT in PostgreSQL enum
  Frontend?:      YES — HEAVY usage: labels, colors, action permissions,
                  stable status for polling
  Routes/Svc?:    YES — workflow runtime router uses it as a step name
  Dead Code?:     NO — fully integrated, heavily used, critical workflow state
  Recommendation: ADD_TO_DATABASE_ENUM — Critical workflow state used across
                  the entire stack. Cannot be removed or remapped.

  ─────────────────────────────────────────────────────────────────────────────
  Rationale: "legal_review" is one of the most important workflow states. It's
  referenced in frontend workflow definitions with labels, colors, and action
  permissions. It has full transition matrices in both state machines. The DB
  has "legal_approval" but that's a different state (legal approved the review,
  not reviewing it). These are semantically different and cannot be collapsed.
  ─────────────────────────────────────────────────────────────────────────────


STATUS 4: negotiation
───────────────────────────────────────────────────────────────────────────────

  Defined In:     models.py:49 (ReviewStatus), workflow.py:48 (WorkflowState)
  Maps To:        WorkflowState.NEGOTIATION
  Referenced In:  models.py, workflow.py, workflows/router.py,
                  test_state_transitions.py, test_workflow_reliability.py,
                  status_constants.py (documented as intentionally excluded),
                  sprint20_complete.md
  Reachable?:     YES — from PROCUREMENT_REVIEW, LEGAL_REVIEW, SECURITY_REVIEW;
                  can go to PROCUREMENT_REVIEW, LEGAL_REVIEW, APPROVED,
                  REJECTED, CLOSED
  Persisted?:     NO — NOT in PostgreSQL enum. status_constants.py explicitly
                  documents this gap: "This value was NEVER added to the
                  PostgreSQL review_status enum."
  Frontend?:      NO — frontend uses a separate negotiation_sessions table
                  with its own stage column (not review_status)
  Routes/Svc?:    YES — workflow runtime router uses it
  Dead Code?:     PARTIALLY — The Python enum defines it and the state machine
                  supports transitions to/from it, but it's intentionally
                  excluded from ACTIVE_REVIEW_STATUSES to prevent DB crashes.
                  Negotiation is tracked via a separate domain table.
  Recommendation: MAP_TO_EXISTING_STATUS — Collapse negotiation reviews to
                  "in_review" status for DB persistence. The separate
                  negotiation_sessions table handles the actual negotiation
                  tracking. Remove negotiation from ReviewStatus transitions
                  or map it to in_review in the persistence layer.

  ─────────────────────────────────────────────────────────────────────────────
  Rationale: The status_constants.py already documents this gap. Negotiation
  has its own separate domain with its own tables (negotiation_sessions with
  stage column). The review_status should not carry a "negotiation" value
  because negotiation is not a review status — it's a separate workflow phase
  tracked in its own table. The transition matrix allows it, but the DB cannot
  store it. Best approach: remove from ReviewStatus or map to in_review.
  ─────────────────────────────────────────────────────────────────────────────


STATUS 5: procurement_review
───────────────────────────────────────────────────────────────────────────────

  Defined In:     models.py:45 (ReviewStatus), workflow.py:45 (WorkflowState)
  Maps To:        WorkflowState.PROCUREMENT_REVIEW
  Referenced In:  models.py, workflow.py, workflows/router.py,
                  test_state_transitions.py, test_workflow_reliability.py,
                  workflow.ts (frontend), ReviewQueue.tsx, useReviews.ts
  Reachable?:     YES — from AI_REVIEWED, REVIEW_READY, AI_ANALYZED,
                  IN_REVIEW, NEGOTIATION, SECURITY_REVIEW, LEGAL_REVIEW,
                  ESCALATED; can go to LEGAL_REVIEW, SECURITY_REVIEW,
                  NEGOTIATION, REJECTED, CLOSED
  Persisted?:     NO — NOT in PostgreSQL enum
  Frontend?:      YES — labels, colors, stable status for polling
  Routes/Svc?:    YES — workflow runtime router defines it as a workflow type
  Dead Code?:     NO — fully integrated, heavily used, critical workflow state
  Recommendation: ADD_TO_DATABASE_ENUM — Critical workflow state used across
                  the entire stack. Cannot be removed or remapped.

  ─────────────────────────────────────────────────────────────────────────────
  Rationale: Same as legal_review — "procurement_review" is a core workflow
  state with full frontend support (labels, colors, polling logic), complete
  transition matrices, and workflow runtime integration. It is semantically
  distinct from any existing DB enum value.
  ─────────────────────────────────────────────────────────────────────────────


STATUS 6: security_review
───────────────────────────────────────────────────────────────────────────────

  Defined In:     models.py:47 (ReviewStatus), workflow.py:47 (WorkflowState)
  Maps To:        WorkflowState.SECURITY_REVIEW
  Referenced In:  models.py, workflow.py, test_state_transitions.py,
                  test_workflow_reliability.py, workflow.ts (frontend),
                  ReviewQueue.tsx, useReviews.ts
  Reachable?:     YES — from PROCUREMENT_REVIEW, IN_REVIEW, ESCALATED;
                  can go to LEGAL_REVIEW, NEGOTIATION, REJECTED,
                  PROCUREMENT_REVIEW, ESCALATED, CLOSED
  Persisted?:     NO — NOT in PostgreSQL enum
  Frontend?:      YES — labels, colors, stable status for polling
  Routes/Svc?:    NO
  Dead Code?:     NO — fully integrated, frontend-supported workflow state
  Recommendation: ADD_TO_DATABASE_ENUM — Active workflow state with full
                  frontend support. Cannot be removed or remapped.

  ─────────────────────────────────────────────────────────────────────────────
  Rationale: Same pattern as legal_review and procurement_review — a core
  workflow state with frontend labels, colors, and transition matrices.
  ─────────────────────────────────────────────────────────────────────────────


================================================================================
  RECOMMENDATIONS SUMMARY
================================================================================

  Status                  Recommendation          Priority   Effort
  ─────────────────────── ─────────────────────── ────────── ──────
  ai_reviewed             MAP_TO_EXISTING_STATUS  🟡 Medium   Low
                          (alias for ai_analyzed)

  analyzing               ADD_TO_DATABASE_ENUM    🔴 High    Low

  legal_review            ADD_TO_DATABASE_ENUM    🔴 High    Low

  negotiation             MAP_TO_EXISTING_STATUS  🟡 Medium   Medium
                          (use negotiation_sessions table)

  procurement_review      ADD_TO_DATABASE_ENUM    🔴 High    Low

  security_review         ADD_TO_DATABASE_ENUM    🔴 High    Low


================================================================================
  MIGRATION SQL (for ADD_TO_DATABASE_ENUM recommendations)
================================================================================

  To add the 4 missing statuses to the PostgreSQL enum:

  ```sql
  ALTER TYPE review_status ADD VALUE 'analyzing' BEFORE 'ai_analyzed';
  ALTER TYPE review_status ADD VALUE 'legal_review' BEFORE 'legal_approval';
  ALTER TYPE review_status ADD VALUE 'procurement_review' BEFORE 'legal_review';
  ALTER TYPE review_status ADD VALUE 'security_review' BEFORE 'legal_review';
  ```

  Note: 'negotiation' is intentionally excluded per the documented gap.
  'ai_reviewed' is intentionally excluded (it's an alias for ai_analyzed).

================================================================================
  IMPACT OF NOT FIXING
================================================================================

  Any code path that tries to persist a review with one of these 6 statuses
  will crash with:

    psycopg2.errors.InvalidTextRepresentationError: invalid input value
    for enum review_status: "legal_review"

  Current code avoids this by:
  - Using POST /reviews/{id}/status which goes through WorkflowState machine
    (which uses LEGACY_STATUS_MAP, not direct DB writes)
  - Route handlers like approve/escalate use the ReviewStatus enum which maps
    through LEGACY_STATUS_MAP before persisting
  - The frontend displays these statuses but the backend maps them before DB write

  However, the workflow/advance endpoint and the generic status update endpoint
  (POST /reviews/{id}/status?status=...) pass the raw string value, which WILL
  crash if it's one of these 6 values.

================================================================================
