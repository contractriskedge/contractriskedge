================================================================================
  SPRINT 33 — WORKFLOW PLATFORM CONSOLIDATION
  Revised Roadmap — June 27, 2026
================================================================================

Based on the Workflow Engine Audit, the existing codebase has strong building
blocks that need consolidation rather than new invention. The critical finding
is that TWO disconnected state machines exist and WorkflowPack definitions
are stored but never executed by the runtime.


================================================================================
CURRENT STATE (Post-Audit Assessment)
================================================================================

Already Built (Reusable):
  ✅ Workflow Runtime engine (WorkflowEngine class)
  ✅ Workflow persistence (6 tables, tenant-isolated)
  ✅ Review domain state machine (14 states, hardcoded transitions)
  ✅ Routing engine (weighted scoring, 5 factors)
  ✅ WorkflowPack + WorkflowVersion models + CRUD API
  ✅ WorkflowCanvas backend model (nodes, edges, validation)
  ✅ Saga compensation pattern
  ✅ Approval gates with timeout
  ✅ SLA breach detection
  ✅ Escalation policy model
  ✅ Execution audit logs
  ✅ Dashboard analytics (3 endpoints)
  ✅ Kanban visualization (frontend)
  ✅ Pending approvals UI (frontend)
  ✅ Negotiation module already uses Workflow Runtime

Missing / Needs Work:
  ❌ Two state machines are disconnected (Review domain ≠ Runtime engine)
  ❌ WorkflowPack records stored but never loaded into engine
  ❌ Transitions hardcoded in both state machines
  ❌ Condition expressions exist on model but never evaluated
  ❌ Routing weights are hardcoded constants
  ❌ No assignment strategy abstraction
  ❌ No admin UI for workflow configuration
  ❌ No visual workflow designer (backend model exists, no frontend)
  ❌ No pack-to-engine bridge
  ❌ No contract-type to workflow-type mapping


================================================================================
REVISED SPRINT 33 PLAN
================================================================================

SPRINT 33.1 — Workflow Consolidation (Backend)
────────────────────────────────────────────────────────────────────

  Goal: Unify the two state machines into one runtime without breaking
        existing functionality. Make the runtime load WorkflowPack
        definitions from the database instead of hardcoded Python.

  1. MERGE STATE MACHINES
     - Create a unified WorkflowDefinition model that can represent
       both the Review domain's 14 states and the Runtime's 9 states
     - Map existing Review domain transitions into the new format
     - Keep ReviewService.update_status() working as a facade that
       delegates to the consolidated runtime
     - All existing API endpoints continue to function unchanged

  2. RUNTIME LOADS WORKFLOW PACKS
     - Replace _init_default_definitions() with a loader that reads
       from the workflow_packs table
     - Migrate the 3 hardcoded definitions (contract_review,
       procurement_review, negotiation_review) into database records
     - Add a "publish" workflow that makes a pack available to the
       runtime (separate from "create")
     - WorkflowVersion table already exists — use it for published
       snapshot tracking

  3. JSON RULE EVALUATOR
     - Build a lightweight JSON-based condition evaluator (not a
       Python parser — exactly as discussed for Clause Recommendations)
     - Support: =, !=, >, >=, <, <=, IN, NOT_IN, CONTAINS, AND, OR
     - Evaluate condition_expression field on WorkflowPack stages
     - Example: {"var": "contract_value", "op": ">", "val": 1000000}
       → routes to executive_approval step instead of standard_approval
     - No AI. No Python eval(). Pure JSON matching.

  4. ROUTING ABSTRACTION
     - Extract routing from Review domain into a reusable service
     - Define strategy interface: RoundRobin, LeastLoaded, Weighted,
       ManagerReview, SpecificUser, Hierarchy
     - Make weights configurable (store in workflow_pack.rules JSONB)
     - Keep existing weighted algorithm as the default strategy


SPRINT 33.2 — Workflow Administration (Frontend + API)
────────────────────────────────────────────────────────────────────

  Goal: Build the admin-facing configuration UI now that the backend
        is unified and configurable.

  1. WORKFLOW DEFINITIONS UI
     - List/create/edit workflow packs
     - Define stages with transitions
     - Set stage-level SLA targets
     - Publish/version management

  2. ROUTING RULES UI
     - Select assignment strategy per workflow type
     - Configure strategy parameters (weights, pool size, etc.)
     - Preview routing results

  3. APPROVAL RULES UI
     - Define approval gates per stage
     - Set approval hierarchy (sequential, parallel, any)
     - Configure timeout and auto-reject behavior

  4. SLA CONFIGURATION UI
     - Set per-stage and per-workflow SLA targets
     - Configure escalation triggers on SLA breach
     - Notification routing for SLA warnings

  5. ESCALATION CONFIGURATION UI
     - Define escalation levels (chain of command)
     - Set escalation timing (X hours per level)
     - Configure notification channels per level

  6. SIMULATOR
     - Test workflow definitions with sample data
     - Visualize the path through states
     - Show estimated completion time based on SLA config

  7. PUBLISH/VERSION UI
     - Draft → Published workflow lifecycle
     - Version history and rollback
     - Activation/deactivation per tenant


================================================================================
WHAT NOT TO BUILD (Yet)
================================================================================

  ❌ Drag-and-drop visual workflow designer (BPMN canvas)
     - Backend WorkflowCanvas model exists but frontend canvas is
       expensive to build well. The admin configuration forms in
       Sprint 33.2 are higher priority.

  ❌ New business modules (Lifecycle, Renewals, etc.)
     - Existing modules (Review, Negotiation, Approval, Signature,
       Obligations) should be migrated to the consolidated workflow
       first. New modules can be added later.

  ❌ AI-powered workflow recommendations
     - The JSON rule evaluator (Phase 1) covers the deterministic
       case. AI can be added as an additional condition provider
       later, same pattern as Clause Recommendations.


================================================================================
ARCHITECTURE PRINCIPLES
================================================================================

  1. One Runtime
     Everything executes through WorkflowEngine. Review, Negotiation,
     Approval, Signature, Obligations, Renewals — all use the same
     state machine, persistence, audit, and API.

  2. Configuration Over Code
     Transitions, routing, SLA, escalations — all stored in the
     database and loaded at runtime. No hardcoded constants.

  3. Backward Compatibility
     Existing ReviewService.update_status() continues to work as a
     thin facade. Existing API endpoints are unchanged. Modules
     migrate to the consolidated workflow incrementally.

  4. JSON Over Python
     Condition expressions, routing rules, and transition guards
     use JSON-based evaluation. No Python eval(). No code generation.
     Safe for administrator configuration.

  5. Tenant Isolation
     All workflow data is tenant-scoped. Configuration changes by
     one tenant do not affect others.


================================================================================
BACKEND PROGRESS ESTIMATE
================================================================================

Based on the audit findings:

  Already built:    60-70% of backend infrastructure
  Sprint 33.1:      20% (consolidation + evaluator + routing)
  Sprint 33.2:      15% (admin API extensions)

The audit confirms the expensive pieces (persistence, audit, analytics,
compensation, packs, canvas model) already exist. The remaining work is
primarily connecting existing pieces and adding configuration surfaces.


================================================================================
END OF ROADMAP
================================================================================
