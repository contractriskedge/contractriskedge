================================================================================
  SPRINT 21 — IMPLEMENTATION PLAN
  "Human Review Workflow Hardening"
  Estimated: 2-3 weeks (13 story points)
  Date: June 4, 2026
================================================================================

  CONTEXT:
  ──────────────────────────────────────────────────────────────────────────────
  Sprint 20 (Executive Analytics) is COMPLETE and tagged v0.20.0.
  
  The AI pipeline is fully operational. The Executive Dashboard is complete.
  The weakest link is now the human review process — specifically state
  transition consistency, approval chain enforcement, escalation hardening,
  and end-to-end validation.

  This sprint hardens the complete human review lifecycle from AI analysis
  completion through final approval and audit recording.

  VERIFIED STATE (from codebase audit):
  ──────────────────────────────────────────────────────────────────────────────
  Review Queue frontend:     ReviewQueue.tsx (1064 lines) — fully built
  Approval frontend:         ApprovalModal.tsx (409 lines) — fully built
  Escalation frontend:       EscalationModal.tsx (344 lines) — fully built
  Reviewer Operations:       ReviewerOperations.tsx (507 lines) — fully built
  
  Backend router:            review/router.py (2717 lines) — all endpoints exist
  Backend service:           review/service.py (3147 lines) — all services exist
  Backend repository:        review/repository.py (760 lines) — all queries exist
  
  State machines:            status_constants.py + workflow_state.py (dual systems)
  Lock guard:                review/lock_guard.py — immutable state enforcement
  Audit trail:               review/audit_trail_service.py (352 lines) — comprehensive
  
  Routing engine:            routing/engine.py (429 lines) — 5-dimension scoring
  E2E tests:                 e2e_review_lifecycle_validation.py (695 lines)
                             test_review_lifecycle.py (436 lines)

  Backend APIs:              30+ endpoints covering the full lifecycle
  Frontend API service:      services/api/reviews.ts (520 lines)

================================================================================
PHASE 1 — STATE MACHINE UNIFICATION (5 SP) [P1]
================================================================================

  TASK 1.1: Align WorkflowState with ReviewStatus (3 SP)
  ──────────────────────────────────────────────────────────────────────────────

  Files to modify:
    backend/app/domains/analytics/status_constants.py
    backend/app/domains/review/workflow_state.py
    backend/app/domains/analytics/executive_service.py (ACTIVE_REVIEW_STATUSES usage)

  Problem:
    Two parallel state machines exist:
    - ReviewStatus (20 values) — DB enum
    - WorkflowState (14 values) — enterprise workflow
    They are out of sync. WorkflowState is missing: draft, legal_review, 
    exec_review, compliance_review, negotiation, executed, archived.
    
    ACTIVE_REVIEW_STATUSES only lists 4 statuses but ReviewStatus has many more
    active-like statuses (legal_approval, exec_approval, compliance_review, etc.)
    that aren't counted as "active" for analytics.

  Implementation:
    1. Add missing states to WorkflowState enum:
       - DRAFT = "draft"
       - LEGAL_REVIEW = "legal_review"
       - EXEC_REVIEW = "exec_review"
       - COMPLIANCE_REVIEW = "compliance_review"
       - NEGOTIATION = "negotiation"
       - EXECUTED = "executed"
       - ARCHIVED = "archived"
    
    2. Update WorkflowState.transition_matrix to include new states
    
    3. Update ACTIVE_REVIEW_STATUSES in status_constants.py to include ALL
       non-terminal active states:
       - draft, ai_analyzed, in_review, legal_review, exec_review,
         compliance_review, negotiation, legal_approval, exec_approval,
         pending_approval, conditional_approval
    
    4. Update TERMINAL_REVIEW_STATUSES to include: approved, rejected,
       finalized, executed, archived, cancelled

    5. Update workflow_state.py REVIEW_STATUS_MAP to map every ReviewStatus
       value to a WorkflowState value (no gaps)

  Acceptance:
    ✅ WorkflowState has all 20 ReviewStatus values mapped
    ✅ ACTIVE_REVIEW_STATUSES captures all non-terminal states
    ✅ TERMINAL_REVIEW_STATUSES captures all terminal states
    ✅ Analytics counts correctly reflect all active reviews
    ✅ No ValueError on unknown status mapping


  TASK 1.2: Add State Transition Validation Middleware (2 SP)
  ──────────────────────────────────────────────────────────────────────────────

  Files to create:
    backend/app/domains/review/state_validator.py (NEW — 120 lines)

  Implementation:
    Create a StateValidator class that:
    1. On every status transition, validates:
       - Source state exists in the state machine
       - Target state is reachable from source (valid transition)
       - Review is not in an immutable (terminal) state
       - No concurrent transition in progress (optimistic lock)
    
    2. Returns structured error response for invalid transitions:
       {
         "error": "invalid_transition",
         "from_status": "approved",
         "to_status": "in_review",
         "message": "Cannot transition from 'approved' to 'in_review'",
         "allowed_transitions": ["finalized", "archived"]
       }
    
    3. Integrates with existing lock_guard.py

  Acceptance:
    ✅ Invalid transitions return structured errors (not 500)
    ✅ Allowed transitions are returned in error response
    ✅ Terminal states are immutable
    ✅ Concurrent transition detection works
    ✅ Lock guard integration preserved


================================================================================
PHASE 2 — APPROVAL CHAIN ENFORCEMENT (3 SP) [P1]
================================================================================

  TASK 2.1: Implement Multi-Level Approval Routing (2 SP)
  ──────────────────────────────────────────────────────────────────────────────

  Files to create:
    backend/app/domains/review/approval_chain.py (NEW — 180 lines)

  Problem:
    Currently any authorized user can approve a review. There's no multi-level
    approval routing (e.g., "legal must approve before exec").

  Implementation:
    Create ApprovalChainService:
    1. Define approval chain configuration per tenant/workflow_type:
       - legal_review → legal_approval
       - executive_review → exec_approval
       - compliance_review → compliance_approval
    
    2. On approve action, check:
       - Is this the correct level in the chain?
       - Have all prerequisite approvals been obtained?
       - Does the user have authority for this level?
    
    3. If chain not complete, set status to conditional_approval
       instead of approved, and route to next level
    
    4. Store chain state in review metadata:
       {
         "approval_chain": {
           "completed": ["legal_approval"],
           "pending": ["exec_approval"],
           "current_level": "exec_approval"
         }
       }

  Acceptance:
    ✅ Multi-level approval enforced for configured workflow types
    ✅ Prerequisite approval check before allowing next level
    ✅ Chain state persisted in review metadata
    ✅ Reviews with partial chain show "Conditionally Approved" status
    ✅ Fallback to single approval when no chain configured


  TASK 2.2: Add Conditional Approve UI Path (1 SP)
  ──────────────────────────────────────────────────────────────────────────────

  Files to modify:
    frontend/components/review/ApprovalModal.tsx

  Problem:
    Backend supports conditionally_approved decision type but frontend
    ApprovalModal only offers "Approve" and "Reject" buttons.

  Implementation:
    1. Add "Conditionally Approve" as a third action button (styled differently)
    2. Show conditions editor when selected (reuse existing JSON editor)
    3. Add tooltip: "Approves with conditions — routes to next approval level"
    4. Wire to POST /reviews/{review_id}/approve with decision="conditionally_approved"

  Acceptance:
    ✅ "Conditionally Approve" button visible in ApprovalModal
    ✅ Conditions JSON editor functional
    ✅ Correct API call with decision parameter
    ✅ Tooltip explains behavior


================================================================================
PHASE 3 — ESCALATION HARDENING (2 SP) [P2]
================================================================================

  TASK 3.1: Add Escalation SLA and Auto-Escalation (1 SP)
  ──────────────────────────────────────────────────────────────────────────────

  Files to modify:
    backend/app/domains/review/service.py (escalation section)
    backend/app/domains/review/schemas.py

  Problem:
    No SLA or timeout for escalated reviews. No auto-escalation if a review
    sits too long in a stage without action.

  Implementation:
    1. Add escalation_deadline to escalation schema (default: 24h from escalation)
    2. Add auto_escalation_after_hours field (default: 48)
    3. In the escalation service, calculate and store deadline
    4. Add a background check (or periodic task) that detects:
       - Escalations past deadline → auto-escalate to next level
       - Reviews stuck in a stage > auto_escalation_after_hours → trigger escalation

  Acceptance:
    ✅ Escalation deadline stored and visible in UI
    ✅ Auto-escalation triggers when deadline passes
    ✅ Configurable timeout per tenant/workflow type


  TASK 3.2: Add Max Escalation Depth Limit (1 SP)
  ──────────────────────────────────────────────────────────────────────────────

  Files to modify:
    backend/app/domains/review/service.py (escalation section)
    backend/app/domains/review/schemas.py

  Problem:
    No configurable limit on escalation chain depth — could loop indefinitely.

  Implementation:
    1. Add max_escalation_depth field (default: 3)
    2. On escalation, check current escalation count vs max depth
    3. If max depth reached, route to tenant_admin for manual resolution
    4. Store escalation_depth counter in review metadata

  Acceptance:
    ✅ Max escalation depth enforced
    ✅ Reviews at max depth routed to tenant_admin
    ✅ Configurable per tenant
    ✅ Escalation depth counter visible in audit trail


================================================================================
PHASE 4 — E2E VALIDATION & TEST HARDENING (3 SP) [P1]
================================================================================

  TASK 4.1: Fix E2E Test Route References (1 SP)
  ──────────────────────────────────────────────────────────────────────────────

  Files to modify:
    e2e_review_lifecycle_validation.py
    test_review_lifecycle.py

  Problem:
    E2E tests reference:
    - GET /reviews/{review_id}/audit which doesn't exist as standalone route
      (audit data is accessed via GET /reviews/{review_id}/activity and workspace hydration)
    - DOCX export routes that may differ from actual routes

  Implementation:
    1. Fix GET /reviews/{review_id}/audit → GET /reviews/{review_id}/activity
    2. Verify and fix DOCX export route references
    3. Add explicit status transition assertions after each action
    4. Add rollback/cleanup to prevent test pollution

  Acceptance:
    ✅ All E2E tests pass without route errors
    ✅ Status transitions explicitly asserted after each action
    ✅ Cleanup runs after test completion


  TASK 4.2: Add State Transition E2E Tests (1 SP)
  ──────────────────────────────────────────────────────────────────────────────

  Files to create:
    tests/e2e/test_state_transitions.py (NEW — 200 lines)

  Implementation:
    Test every valid and invalid state transition:
    1. Valid transitions (happy path):
       - upload → ai_analyzed → in_review → approved → finalized
       - upload → ai_analyzed → in_review → rejected
       - in_review → legal_review → legal_approval → exec_approval → approved
       - in_review → escalated → resolved → in_review
    
    2. Invalid transitions (error path):
       - approved → in_review (terminal → active)
       - rejected → approved (terminal → active)
       - finalized → in_review (terminal → active)
       - draft → approved (skip required stages)

  Acceptance:
    ✅ All valid transitions succeed
    ✅ All invalid transitions return structured errors
    ✅ Terminal state immutability verified


  TASK 4.3: Add Concurrency/Load Test (1 SP)
  ──────────────────────────────────────────────────────────────────────────────

  Files to create:
    tests/e2e/test_concurrent_assignments.py (NEW — 120 lines)

  Problem:
    Simultaneous assignments to the same reviewer could race.

  Implementation:
    1. Launch 5 concurrent assign requests to the same reviewer
    2. Verify no duplicate assignments
    3. Verify reviewer workload metrics are consistent after all complete
    4. Add optimistic locking assertion

  Acceptance:
    ✅ No duplicate assignments under concurrency
    ✅ Reviewer workload metrics consistent
    ✅ No 500 errors from race conditions


================================================================================
SPRINT 21 SUMMARY
================================================================================

  Phase 1: State Machine Unification (5 SP) [P1]
    Task 1.1: Align WorkflowState with ReviewStatus ........... 3 SP
    Task 1.2: State Transition Validation Middleware .......... 2 SP

  Phase 2: Approval Chain Enforcement (3 SP) [P1]
    Task 2.1: Multi-Level Approval Routing .................... 2 SP
    Task 2.2: Conditional Approve UI Path .................... 1 SP

  Phase 3: Escalation Hardening (2 SP) [P2]
    Task 3.1: Escalation SLA and Auto-Escalation ............. 1 SP
    Task 3.2: Max Escalation Depth Limit ..................... 1 SP

  Phase 4: E2E Validation & Test Hardening (3 SP) [P1]
    Task 4.1: Fix E2E Test Route References .................. 1 SP
    Task 4.2: State Transition E2E Tests .................... 1 SP
    Task 4.3: Concurrency/Load Test .......................... 1 SP

  Total: 13 story points

  Priority Legend:
    P1 — Must-have for Sprint 21 completion
    P2 — Important but can defer to Sprint 22 if needed
    P3 — Nice-to-have

================================================================================
BACKEND APIS INVOLVED
================================================================================

  Existing (to be modified):
    POST /api/v1/reviews/{review_id}/approve     — Add chain enforcement
    POST /api/v1/reviews/{review_id}/escalate    — Add SLA/deadline/depth
    POST /api/v1/reviews/bulk-approve            — Add chain enforcement
    GET  /api/v1/reviews/{review_id}             — Add chain state to response
    GET  /api/v1/reviews/queue                   — Add chain state filter

  New:
    (No new routes — all changes are service-layer logic)

================================================================================
FRONTEND SCREENS INVOLVED
================================================================================

  Existing (to be modified):
    frontend/components/review/ApprovalModal.tsx        — Add conditional approve
    frontend/components/review/ReviewQueue.tsx          — Add chain state display
    frontend/components/review/EscalationModal.tsx      — Add deadline display

================================================================================
DEEPSEEK IMPLEMENTATION PROMPTS
================================================================================

  Prompt 1 — State Machine Unification:
    "Update WorkflowState enum in workflow_state.py to include all 20 ReviewStatus
    values. Add missing states: draft, legal_review, exec_review, compliance_review,
    negotiation, executed, archived. Update transition_matrix. Update REVIEW_STATUS_MAP
    to map every ReviewStatus to a WorkflowState. Then update ACTIVE_REVIEW_STATUSES
    and TERMINAL_REVIEW_STATUSES in status_constants.py to include all relevant states.
    Create state_validator.py with structured error responses for invalid transitions."

  Prompt 2 — Approval Chain:
    "Create approval_chain.py service that enforces multi-level approval routing.
    Define chain per workflow_type: legal_review→legal_approval→exec_approval.
    On approve, check prerequisites and route to next level if chain not complete.
    Store chain state in review metadata. Update POST /reviews/{review_id}/approve
    to integrate chain enforcement. Add 'Conditionally Approve' button to frontend
    ApprovalModal.tsx."

  Prompt 3 — Escalation Hardening:
    "Add escalation_deadline and max_escalation_depth to escalation schema and service.
    Calculate deadline on escalation (default 24h). Add auto-escalation check for
    reviews past deadline. Enforce max_escalation_depth (default 3) — route to
    tenant_admin if exceeded. Store depth counter in review metadata."

  Prompt 4 — E2E Tests:
    "Fix route references in e2e_review_lifecycle_validation.py (audit→activity).
    Create test_state_transitions.py covering all valid and invalid state transitions.
    Create test_concurrent_assignments.py with 5 concurrent assign requests.
    Verify no duplicates, consistent metrics, no race conditions."

================================================================================
TEST CASES
================================================================================

  State Machine Tests:
    TC1: Valid transition upload → ai_analyzed → in_review → approved → finalized
    TC2: Valid transition in_review → rejected
    TC3: Valid transition in_review → legal_review → legal_approval → exec_approval → approved
    TC4: Valid transition in_review → escalated → resolved → in_review
    TC5: Invalid transition approved → in_review (returns structured error)
    TC6: Invalid transition rejected → approved (returns structured error)
    TC7: Invalid transition finalized → in_review (returns structured error)
    TC8: Invalid transition draft → approved (skip required stages)

  Approval Chain Tests:
    TC9: Single approval works when no chain configured
    TC10: Multi-level approval requires legal before exec
    TC11: Conditional approval routes to next chain level
    TC12: Chain completion triggers full approval

  Escalation Tests:
    TC13: Escalation stores deadline correctly
    TC14: Auto-escalation triggers after deadline
    TC15: Max depth enforcement routes to tenant_admin
    TC16: Escalation depth counter increments correctly

  Concurrency Tests:
    TC17: 5 concurrent assigns — no duplicates
    TC18: Reviewer workload metrics consistent after concurrent assigns

================================================================================
E2E VALIDATION PLAN
================================================================================

  Full Lifecycle Test:
    1. Upload contract → verify status = "uploaded"
    2. AI analyzes → verify status = "ai_analyzed"
    3. Assign reviewer → verify status = "in_review", assigned_to set
    4. Add findings → verify findings_count > 0
    5. Legal review → verify status = "legal_review"
    6. Legal approve → verify status = "legal_approval"
    7. Executive review → verify status = "exec_review"
    8. Executive approve → verify status = "approved"
    9. Finalize → verify status = "finalized"
    10. Verify audit trail has all 9 transitions
    11. Verify attempt to modify finalized review fails

  Escalation Test:
    1. Assign reviewer → in_review
    2. Escalate with reason → verify status = "escalated"
    3. Verify escalation_deadline stored
    4. Resolve escalation → verify status = "in_review"
    5. Verify audit trail has escalation + resolution

  Error Path Test:
    1. Try to approve without assignment → verify error
    2. Try to finalize without approval → verify error
    3. Try to modify finalized review → verify lock guard error
    4. Try invalid state transition → verify structured error

================================================================================
