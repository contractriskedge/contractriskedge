================================================================================
  SPRINT 23 TASK 1.1 — Relationships Graph Audit & Architecture
  Completed: June 5, 2026
================================================================================

1. EXECUTIVE SUMMARY
───────────────────────────────────────────────────────────────────────────────

  The Relationships Graph module is a fully built frontend UI shell with
  zero backend integration. 10 frontend files exist with production-quality
  D3 force-directed graph rendering, detail drawers, timeline, and filters.
  All of it runs on empty mock arrays — the graph renders with zero nodes.

  No backend relationship module exists anywhere in the codebase.
  No API endpoints serve relationship graph data.

  The underlying database has 19 tables with 17 distinct foreign-key
  relationship types — a rich graph is readily constructible.

  Estimated effort to implement: 3 sprints (Tasks 1.1 → 1.2 → 1.3)

2. CURRENT-STATE ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────

  2.1 Frontend (10 files, fully built, zero data)
  ─────────────────────────────────────────────────────────────────────────────
    File                    | Lines | Purpose
    ────────────────────────┼───────┼────────────────────────────
    types.ts                | ~200  | TypeScript types (WRONG — enterprise
                          |       | contract types, not DB entities)
    mockData.ts             | ~500  | Synthetic data (never loaded)
    index.ts                | ~10   | Barrel exports
    RelationshipGraph.tsx   | ~185  | Main orchestrator
    GraphCanvas.tsx         | ~290  | D3 force-directed graph
    GraphFilterBar.tsx      | ~100  | Filters + mode selector
    GraphKpiCards.tsx       | ~70   | KPI metrics row
    NodeDetailDrawer.tsx    | ~350  | Slide-out detail panel
    Timeline.tsx            | ~90   | Timeline sidebar
    AiInsights.tsx          | ~130  | AI insight cards

    Critical issue: RelationshipGraph.tsx overrides all mock imports
    with empty arrays: const mockGraphData = { nodes: [], edges: [] };

  2.2 Backend
  ─────────────────────────────────────────────────────────────────────────────
    No relationship router, service, or repository exists.
    No "relationship" or "graph" route in any existing router.
    The only graph endpoint is GET /api/v1/playbooks/{id}/graph
    (policy rule dependencies — unrelated).

3. DATABASE RELATIONSHIP INVENTORY
───────────────────────────────────────────────────────────────────────────────

  3.1 Node Types (10 entities)
  ─────────────────────────────────────────────────────────────────────────────
    # | Node Type      | Source Table            | PK Column        | Tenant FK
    ───┼───────────────┼────────────────────────┼──────────────────┼───────────
    1  | Tenant        | tenants                | tenant_id        | — (root)
    2  | Upload        | upload_sessions        | upload_id        | ✅ tenant_id
    3  | Review        | contract_reviews       | review_id        | ✅ tenant_id
    4  | Finding       | review_findings        | finding_id       | ✅ tenant_id
    5  | Redline       | review_redlines        | redline_id       | ✅ tenant_id
    6  | Clause        | clauses                | clause_id        | ✅ tenant_id
    7  | Obligation    | obligations            | obligation_id    | ✅ tenant_id
    8  | Negotiation   | negotiation_sessions   | session_id       | ✅ tenant_id
    9  | Workflow      | workflow_instances     | instance_id      | ✅ tenant_id
    10 | AI Run        | ai_execution_runs      | run_id           | ✅ tenant_id

  3.2 Edge Types (17 relationships)
  ─────────────────────────────────────────────────────────────────────────────
    # | Edge Type         | Source → Target         | FK Column(s)
    ───┼──────────────────┼─────────────────────────┼──────────────────────
    1  | uploaded_as      | Review → Upload         | review.upload_id
    2  | reviewed_in      | Finding → Review        | finding.review_id
    3  | redlined_in      | Redline → Review        | redline.review_id
    4  | finding_from_run | AI Finding → AI Run     | ai_finding.run_id
    5  | ai_run_for       | AI Run → Upload         | ai_run.upload_id
    6  | ai_finding_for   | Review Finding → AI Finding | review_finding.finding_id
    7  | ai_redline_for   | Review Redline → AI Redline | review_redline.redline_id
    8  | negotiates       | Negotiation → Review    | neg.session_id → review.review_id
    9  | obligates        | Obligation → Review     | oblig.review_id (logical)
    10 | workflow_for     | Workflow → Review       | wf.context->>'review_id' (logical)
    11 | version_of       | Doc Version → Review    | cdv.review_id
    12 | approved_in      | Approval → Review       | approval.review_id
    13 | escalated_in     | Escalation → Review     | escalation.review_id
    14 | assigned_to      | Assignment → Review     | assignment.review_id
    15 | commented_on     | Comment → Review        | comment.review_id
    16 | clause_used_in   | Clause → Review         | clause_usage.review_id (logical)
    17 | tenant_owns      | Everything → Tenant     | *.tenant_id

  3.3 Vendor/Counterparty Data (3 sources)
  ─────────────────────────────────────────────────────────────────────────────
    Source Table          | Column              | Type
    ──────────────────────┼─────────────────────┼──────────────
    upload_sessions       | metadata->>'counterparty' | JSONB key
    negotiation_sessions  | counterparty        | String(255) — direct column
    obligations           | vendor_name         | String(255) — denormalized

4. REQUIRED API DESIGN
───────────────────────────────────────────────────────────────────────────────

  4.1 Endpoints
  ─────────────────────────────────────────────────────────────────────────────
    GET /api/v1/relationships/graph?review_id={uuid}&depth={1|2|3}
      → Full graph centered on a review with configurable traversal depth
      → Response: { nodes: GraphNode[], edges: GraphEdge[] }

    GET /api/v1/relationships/graph?upload_id={uuid}&depth={1|2|3}
      → Full graph centered on an upload/document

    GET /api/v1/relationships/graph?tenant_id={uuid}&limit={50|100|200}
      → Tenant-level overview graph (top-N connected entities)

  4.2 Graph Schema (Pydantic)
  ─────────────────────────────────────────────────────────────────────────────
    class GraphNode(BaseModel):
        id: str           # f"{node_type}:{entity_id}"
        type: NodeType    # Enum: upload, review, finding, redline, ...
        label: str        # Display name
        tenant_id: str
        metadata: dict    # Entity-specific fields (status, severity, etc.)
        connection_count: int  # Number of edges from this node

    class GraphEdge(BaseModel):
        id: str           # f"{source_id}→{target_id}:{edge_type}"
        source: str       # Node ID
        target: str       # Node ID
        type: EdgeType    # Enum: uploaded_as, reviewed_in, ...
        label: str        # Display label
        metadata: dict    # Edge-specific fields

    class RelationshipGraph(BaseModel):
        nodes: list[GraphNode]
        edges: list[GraphEdge]
        total_nodes: int
        total_edges: int
        generated_at: datetime

  4.3 NodeType Enum
  ─────────────────────────────────────────────────────────────────────────────
    NodeType = {
        tenant, upload, review, finding, redline, clause,
        obligation, negotiation, workflow, ai_run, vendor
    }

  4.4 EdgeType Enum
  ─────────────────────────────────────────────────────────────────────────────
    EdgeType = {
        uploaded_as, reviewed_in, redlined_in, finding_from_run,
        ai_run_for, ai_finding_for, ai_redline_for, negotiates,
        obligates, workflow_for, version_of, approved_in,
        escalated_in, assigned_to, commented_on, clause_used_in,
        tenant_owns, reviewed_by, vendor_for
    }

5. REQUIRED DATABASE QUERIES
───────────────────────────────────────────────────────────────────────────────

  5.1 Review-Centered Graph (depth=1)
  ─────────────────────────────────────────────────────────────────────────────
    -- Core review node
    SELECT review_id, status, finding_count FROM contract_reviews WHERE review_id = :id

    -- Direct connections (depth 1)
    SELECT * FROM upload_sessions WHERE upload_id = :upload_id
    SELECT * FROM review_findings WHERE review_id = :id
    SELECT * FROM review_redlines WHERE review_id = :id
    SELECT * FROM review_assignments WHERE review_id = :id
    SELECT * FROM review_approvals WHERE review_id = :id
    SELECT * FROM review_escalations WHERE review_id = :id
    SELECT * FROM review_status_history WHERE review_id = :id
    SELECT * FROM review_comments WHERE review_id = :id
    SELECT * FROM contract_document_versions WHERE review_id = :id
    SELECT * FROM negotiation_sessions WHERE review_id = :id
    SELECT * FROM obligations WHERE review_id = :id
    SELECT * FROM workflow_instances WHERE context->>'review_id' = :id
    SELECT * FROM ai_execution_runs WHERE upload_id = :upload_id

    -- Counterparty/vendor
    SELECT metadata->>'counterparty' FROM upload_sessions WHERE upload_id = :upload_id

  5.2 Depth-2 Traversal
  ─────────────────────────────────────────────────────────────────────────────
    -- For each finding, get AI finding source
    SELECT af.* FROM ai_findings af
    JOIN review_findings rf ON rf.finding_id = af.finding_id
    WHERE rf.review_id = :id

    -- For each AI finding, get AI run
    SELECT * FROM ai_execution_runs WHERE run_id IN (:ai_run_ids)

    -- For each clause_type in findings, find matching clauses
    SELECT * FROM clauses WHERE clause_type IN (:finding_clause_types)

    -- For each negotiation, get negotiation versions/issues/redlines
    SELECT * FROM negotiation_versions WHERE session_id IN (:neg_session_ids)
    SELECT * FROM negotiation_issues WHERE session_id IN (:neg_session_ids)
    SELECT * FROM negotiation_redlines WHERE session_id IN (:neg_session_ids)

6. RECOMMENDED VISUALIZATION LIBRARY
───────────────────────────────────────────────────────────────────────────────

  Keep the existing D3.js force-directed graph in GraphCanvas.tsx.

  Rationale:
    ✅ Already built — 290 lines of production-quality D3 code
    ✅ Supports zoom, pan, drag, tooltips, animations, fullscreen
    ✅ Node colors, sizes, and labels configurable
    ✅ Force simulation with charge, link distance, and collision detection
    ✅ Already wired to the component tree (filters, detail drawer, timeline)

  The only change needed is replacing the mock data source with real API calls.
  The D3 rendering code itself does not need to be rewritten.

7. IMPLEMENTATION EFFORT ESTIMATE
───────────────────────────────────────────────────────────────────────────────

  Task                    | Files    | Est. Hours | Dependencies
  ────────────────────────┼──────────┼────────────┼─────────────
  1.2 Backend: schemas    | 1 (new)  | 1          | None
  1.2 Backend: service    | 1 (new)  | 4          | Schemas
  1.2 Backend: router     | 1 (new)  | 1          | Service
  1.2 Backend: tests      | 1 (new)  | 2          | Service
  1.3 Frontend: types     | 1 (mod)  | 1          | Backend schemas
  1.3 Frontend: API hook  | 1 (new)  | 1          | Types
  1.3 Frontend: component | 1 (mod)  | 2          | API hook
  1.3 Frontend: cleanup   | 1 (del)  | 1          | Component
  ────────────────────────┼──────────┼────────────┼─────────────
  Total                   | 8 files  | 13 hours   | —

8. SPRINT BREAKDOWN
───────────────────────────────────────────────────────────────────────────────

  Sprint 23 Task 1.2 — Backend (recommended 2-3 days)
  ─────────────────────────────────────────────────────────────────────────────
    - Create backend/app/domains/relationships/ directory
    - schemas.py: GraphNode, GraphEdge, RelationshipGraph, NodeType, EdgeType
    - service.py: RelationshipGraphBuilder with depth-1 and depth-2 traversal
    - router.py: GET /api/v1/relationships/graph with review_id, upload_id, tenant_id params
    - tests/: Unit tests for graph building
    - Register router in main.py

  Sprint 23 Task 1.3 — Frontend (recommended 2-3 days)
  ─────────────────────────────────────────────────────────────────────────────
    - Update types.ts: Replace enterprise-contract types with DB entity types
    - Create useRelationshipGraph() hook
    - Update RelationshipGraph.tsx: Connect to API, remove mock overrides
    - Remove mockData.ts (no longer needed)
    - Test: zoom, pan, node selection, edge selection, detail drawer
    - Test: empty state, loading state, error state, large graph performance

9. KEY ARCHITECTURAL DECISIONS
───────────────────────────────────────────────────────────────────────────────

  Decision 1: Review-centered graph
    The graph is always centered on a review (or upload). From the review,
    depth-1 traverses direct FK relationships. Depth-2 follows indirect
    relationships (AI findings → AI runs, clause types → clauses, etc.).

  Decision 2: Tenant isolation
    Every query includes tenant_id. The graph endpoint is multi-tenant safe
    by design since all domain tables have tenant_id FKs.

  Decision 3: Pagination limits
    Maximum nodes per request: 200 (configurable). Depth-2 queries are
    limited to 50 child nodes per parent to prevent explosion.

  Decision 4: Caching
    Graph responses are cached for 5 minutes (TTL). The graph data changes
    only when reviews transition or new findings/redlines are created.

  Decision 5: Keep existing D3 frontend
    The existing GraphCanvas.tsx is production-quality D3 code. Only the
    data source needs to change. No visualization library rewrite needed.

================================================================================
