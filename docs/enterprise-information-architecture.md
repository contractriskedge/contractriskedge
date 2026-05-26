# ContractRiskEdge — Enterprise Information Architecture

## Fortune 500 AI-First Contract Intelligence Platform

---

## 1. Global Navigation Hierarchy

### 1.1 Top-Level Navigation Groups

The platform is organized into **7 primary navigation groups**, each representing a distinct operational domain. These groups are surfaced in the global sidebar and govern module visibility, cross-linking, and AI context.

```
  INTELLIGENCE        CONTRACTS           PROCUREMENT
  ───────────         ─────────           ───────────
  Portfolio Risk      Repository          Vendor 360
  CFO Risk Dashboard  Detail Workspace    Supplier Directory
  Market Benchmarks   Clause Library      Spend Analytics
  Executive Analytics Playbooks           Procurement Workflows

  LEGAL OPS           COMPLIANCE          WORKFLOWS
  ─────────           ─────────           ──────────
  Legal Review        Reg. Intelligence   Approval Center
  Negotiation Center  Obligation Mgmt     Sourcing Events
  Redline Workspace   Audit Center        Onboarding Pipeline
  Relationship Graph  Policy Manager      SLA Operations

  ADMIN
  ─────
  Security Console    User Management     AI Governance
  Integrations Hub    Audit Logs          System Health
```

### 1.2 Navigation Group Definitions

| Group | Purpose | Primary Personas | AI Surface |
|-------|---------|-----------------|------------|
| **Intelligence** | Strategic risk & opportunity visibility across the portfolio | Executives, CFO, Risk Officers | AI summaries, anomaly detection, predictive alerts |
| **Contracts** | Full contract lifecycle management & clause governance | Legal Ops, Contract Managers | AI clause analysis, auto-redlining, obligation extraction |
| **Procurement** | Vendor relationship intelligence & spend optimization | Procurement Managers, Vendor Managers | AI vendor scoring, savings detection, concentration alerts |
| **Legal Ops** | Legal review, negotiation, and relationship mapping | Legal Reviewers, Negotiators | AI copilot drafting, fallback recommendations, risk scoring |
| **Compliance** | Regulatory intelligence, obligation tracking, audit readiness | Compliance Officers, Auditors | AI regulation mapping, gap detection, remediation tracking |
| **Workflows** | Cross-functional operational orchestration | All personas | AI workflow routing, SLA prediction, escalation triggers |
| **Admin** | Platform governance, security, and configuration | System Administrators | AI governance monitoring, anomaly detection, usage analytics |

### 1.3 Navigation Depth & Breadth

```
Level 0: Navigation Group (7 groups)
Level 1: Primary Module (18 modules)
Level 2: Sub-Module (views within a module)
Level 3: Entity View (specific contract, vendor, clause)
Level 4: Detail Drawer (contextual deep-dive)
```

**Rule:** Maximum navigation depth is **4 levels**. Level 4 is always a drawer/panel, never a full page transition.

---

## 2. Module Hierarchy & Relationships

### 2.1 Complete Module Tree

```
INTELLIGENCE
+-- Portfolio Risk Dashboard
|   +-- Risk Heatmap
|   +-- Exposure Analytics
|   +-- Trend Forecasting
|   +-- AI Risk Alerts
+-- CFO Risk Dashboard
|   +-- Financial Exposure
|   +-- Revenue at Risk
|   +-- Concentration Analysis
|   +-- Executive Summary
+-- Market Benchmarks
|   +-- Clause Benchmarking
|   +-- Pricing Benchmarks
|   +-- Term Comparison
|   +-- Negotiation Intelligence
+-- Executive Analytics
    +-- Board Reports
    +-- Strategic KPIs
    +-- Portfolio Health
    +-- AI Executive Briefing

CONTRACTS
+-- Contracts Repository
|   +-- Contract List (Table/Grid)
|   +-- Advanced Search
|   +-- Bulk Operations
|   +-- Upload & Ingestion
+-- Contract Detail Workspace
|   +-- Document Viewer
|   +-- Clause Navigation
|   +-- Obligations Panel
|   +-- Version History
|   +-- Activity Timeline
+-- Clause Library
|   +-- Clause Catalog
|   +-- Playbook Manager
|   +-- Fallback Clauses
|   +-- Benchmark Comparison
+-- Document Ingestion Center
    +-- Batch Processing
    +-- OCR & Classification
    +-- Metadata Extraction
    +-- Quality Review

PROCUREMENT
+-- Vendor 360 Workspace
|   +-- Vendor Health Summary
|   +-- Risk Pulse
|   +-- Action Agenda
|   +-- Intelligence Sidebar
+-- Supplier Directory
|   +-- Supplier Table
|   +-- Filter System
|   +-- Supplier Detail Drawer
|   +-- Relationship Map
+-- Spend Analytics
|   +-- Trend Analysis
|   +-- Category Breakdown
|   +-- Geographic Risk
|   +-- Concentration Analysis
+-- Procurement Workflows
    +-- Approval Queue
    +-- Sourcing Events
    +-- Onboarding Pipeline
    +-- SLA Operations

LEGAL OPS
+-- Legal Review Workspace
|   +-- Review Queue
|   +-- Clause Workspace
|   +-- AI Copilot Drawer
|   +-- Redline Engine
+-- Negotiation Center
|   +-- Session Manager
|   +-- Diff Engine
|   +-- Issue Tracker
|   +-- Fallback Library
+-- Relationship Graph
    +-- Entity Graph
    +-- Dependency Map
    +-- Timeline
    +-- AI Insights

COMPLIANCE
+-- Compliance Intelligence Center
|   +-- Regulation Map
|   +-- Finding Management
|   +-- Remediation Tracker
|   +-- AI Insight Panel
+-- Obligation Management Center
|   +-- Obligation Registry
|   +-- SLA Center
|   +-- Compliance Filtering
|   +-- AI Obligation Extraction
+-- Audit Center
    +-- Audit Trail
    +-- Evidence Management
    +-- Policy Manager
    +-- AI Audit Assistant

WORKFLOWS
+-- Workflow Center
|   +-- Kanban Board
|   +-- Approval Table
|   +-- SLA Monitoring
|   +-- AI Insights
+-- Sourcing Events
+-- Onboarding Pipeline
+-- Escalation Manager

ADMIN
+-- Security Console
+-- User Management
+-- AI Governance Center
+-- Integrations Hub
+-- Audit Logs
+-- System Health
```

### 2.2 Cross-Module Entity Relationships

```
                    +----------------------+
                    |     CONTRACT         |  -- Core Entity
                    |  id, name, type,     |
                    |  riskScore, status   |
                    +----------+-----------+
                               |
            +------------------+------------------+
            |                  |                  |
            v                  v                  v
    +--------------+  +--------------+  +------------------+
    |   VENDOR     |  |   CLAUSE     |  |   OBLIGATION     |
    |  riskScore,  |  |  type, text, |  |  status, dueDate |
    |  spend, SLA  |  |  riskLevel   |  |  assignee        |
    +------+-------+  +------+-------+  +----------+-------+
           |                  |                  |
           v                  v                  v
    +--------------+  +--------------+  +------------------+
    |  WORKFLOW    |  |   FINDING    |  |   COMPLIANCE     |
    |  type, stage |  |  severity,   |  |  regulation,     |
    |  assignee    |  |  confidence  |  |  status          |
    +--------------+  +--------------+  +------------------+
```

**Navigation Rules:**
- Every entity is clickable and opens its detail workspace
- Entities are cross-linked: Contract to Vendor, Contract to Clause, Clause to Finding, etc.
- The AI Copilot maintains entity context across navigation
- Breadcrumbs are entity-aware: `Contracts > MSA-Acme > Clause 4.2 > Finding #3`

### 2.3 Contextual Navigation Transitions

| Source Module | Target Module | Trigger | Transition Type |
|--------------|---------------|---------|-----------------|
| Portfolio Risk | Contract Detail | Click contract row | Full page (slide) |
| Contract Detail | Vendor 360 | Click vendor name | Drawer (slide-over) |
| Legal Review | Negotiation Center | "Open in Negotiation" | Full page (fade) |
| Vendor 360 | Supplier Drawer | Click supplier row | Drawer (slide-over) |
| Clause Library | Contract Detail | Click contract reference | Full page (slide) |
| Compliance Center | Obligation Center | Click obligation link | Partial (panel swap) |
| Any Module | AI Copilot | Cmd+K / FAB click | Overlay (modal) |
| Search Hub | Any Entity | Click search result | Context-dependent |

---

## 3. User Persona Architecture

### 3.1 Persona Navigation Matrix

| Persona | Default Landing | Priority Modules | Shortcuts | AI Copilot Mode |
|---------|----------------|-----------------|-----------|-----------------|
| **Legal Reviewer** | Legal Review Workspace | Review Queue, Clause Workspace, Negotiation Center | Cmd+1: Queue, Cmd+2: Redline, Cmd+3: Copilot | `legal_assistant` |
| **Procurement Manager** | Vendor 360 | Supplier Directory, Spend Analytics, Workflows | Cmd+1: Vendors, Cmd+2: Spend, Cmd+3: Actions | `procurement_assistant` |
| **CFO** | CFO Risk Dashboard | Portfolio Risk, Benchmarks, Executive Analytics | Cmd+1: Risk, Cmd+2: Reports, Cmd+3: Briefing | `executive_intelligence` |
| **Compliance Officer** | Compliance Intelligence | Obligation Center, Audit Center, Policy Manager | Cmd+1: Findings, Cmd+2: Obligations, Cmd+3: Audit | `compliance_assistant` |
| **Executive** | Portfolio Risk Dashboard | Executive Analytics, Benchmarks, AI Briefing | Cmd+1: Summary, Cmd+2: Reports, Cmd+3: Alerts | `executive_intelligence` |
| **System Admin** | Admin Console | Security, Users, AI Governance, Integrations | Cmd+1: Users, Cmd+2: Audit, Cmd+3: Health | `workflow_coordinator` |
| **Vendor Manager** | Vendor 360 | Supplier Directory, Contract Detail, Workflows | Cmd+1: Vendors, Cmd+2: Contracts, Cmd+3: Actions | `procurement_assistant` |

### 3.2 Role-Based Navigation Visibility

```
Admin:       [ALL MODULES VISIBLE]
Analyst:     [Intelligence] [Contracts] [Procurement] [Legal Ops] [Compliance] [Workflows]
Viewer:      [Intelligence] [Contracts - Read] [Procurement - Read] [Analytics - Read]
Compliance:  [Compliance] [Obligations] [Contracts - Read] [Workflows]
Legal:       [Legal Ops] [Contracts] [Clause Library] [Negotiation]
Procurement: [Procurement] [Contracts] [Workflows] [Vendor 360]
```

### 3.3 Persona Workflow Journeys

**Legal Reviewer Journey:**
```
Dashboard -> Legal Review Queue -> Select Contract -> Clause Workspace
    -> AI Finds Issue -> Open AI Copilot -> Get Recommendation
    -> Apply Redline -> Escalate if needed -> Approve -> Next Contract
```

**Procurement Manager Journey:**
```
Dashboard -> Vendor 360 -> View Health Summary -> See Risk Alerts
    -> Open Supplier Drawer -> Review Contract Terms
    -> Initiate Sourcing Event -> Track in Workflows -> Monitor SLA
```

**CFO Journey:**
```
Dashboard -> CFO Risk Dashboard -> View Financial Exposure
    -> Drill into Concentration Risk -> See Top Risky Vendors
    -> Open Executive Briefing -> AI Summarizes Portfolio Health
    -> Export Board Report
```

---

## 4. AI-First Platform Architecture

### 4.1 AI Surface Areas

```
                    AI COPILOT (Persistent)
    +---------------------+  +---------------------+  +-----------------------------+
    |       Chat          |  |      Insights       |  |      Suggested Actions       |
    |  -----------------  |  |  -----------------  |  |  --------------------------  |
    |  Natural            |  |  Proactive          |  |  "Redline clause 4.2"        |
    |  language           |  |  alerts             |  |  "Escalate to senior"        |
    |  queries            |  |  based on           |  |  "Generate report"           |
    |                     |  |  context            |  |  "Compare vendors"            |
    +---------------------+  +---------------------+  +-----------------------------+
              ^                        ^                           ^
              |                        |                           |
         Context-aware            Screen-aware               Entity-aware
```

### 4.2 AI Proximity to Content

| Location | AI Element | Behavior |
|----------|-----------|----------|
| **Global** | AI Copilot FAB (floating action button) | Persistent, bottom-right, always accessible |
| **Inline** | AI Finding Cards (in clause workspace) | Contextual, appears next to relevant content |
| **Panel** | AI Insights Panel (right sidebar) | Screen-aware, updates on navigation |
| **Header** | AI Summary Banner | Top of page, provides executive overview |
| **Toolbar** | AI Action Buttons | "AI Redline", "AI Analyze", "AI Compare" |
| **Search** | AI Semantic Search | Natural language query, results with confidence |

### 4.3 AI Context Propagation

```
User navigates: Portfolio -> Contract Detail -> Clause 4.2

AI Context Chain:
  Screen: "contract-detail"
  Entity: "Contract: MSA-AcmeCorp"
  Sub-Entity: "Clause: 4.2-Indemnification"
  Workflow: "legal_review"
  User Role: "legal_reviewer"
  Recent: ["Viewed clause 4.2", "Opened redline mode"]

AI Response: "I see you're reviewing the indemnification clause in
  MSA-AcmeCorp. This clause has a high risk score of 8.2/10.
  Would you like me to suggest fallback language from your playbook?"
```

### 4.4 Proactive AI Triggers

| Trigger Condition | AI Action | Surface |
|------------------|-----------|---------|
| High-risk clause detected | Surface finding card + copilot suggestion | Inline + Copilot |
| SLA breach imminent | Push notification + escalation suggestion | Notification + Copilot |
| Contract renewal approaching | Suggest renewal workflow + benchmark data | Banner + Copilot |
| Vendor concentration exceeds threshold | Alert + diversification recommendation | Insight panel |
| Benchmark deviation found | Compare clause + suggest alternative | Clause workspace |
| User idle on a screen | Surface relevant insight | Copilot insights tab |

---

## 5. Workspace Architecture

### 5.1 Workspace Layout Patterns

The platform uses **4 canonical workspace layouts**:

**PATTERN A: Full-Screen Dashboard**
```
+------------------------------------------------------+
|  KPI Row (horizontal scroll)                         |
+------------------------------------------------------+
|  Filter Bar                                           |
+------------------------------------------------------+
|  +--------------+  +--------------+  +------------+  |
|  |  Chart/Panel |  |  Chart/Panel |  |  Sidebar   |  |
|  |              |  |              |  |  Insights  |  |
|  +--------------+  +--------------+  +------------+  |
|  +----------------------------------------------+    |
|  |  Data Table (paginated, sortable)            |    |
|  +----------------------------------------------+    |
+------------------------------------------------------+
```
Used by: Portfolio, CFO, Benchmarks, Analytics

**PATTERN B: 3-Panel Workspace**
```
+------------------------------------------------------+
|  Toolbar (contextual actions)                        |
+----------+---------------------------+----------------+
|  LEFT    |  CENTER                  |  RIGHT         |
|  Panel   |  Panel                   |  Panel         |
|  ------- |  ----------              |  ------        |
|  Queue   |  Clause/Content          |  AI Copilot    |
|  List    |  Viewer                  |  Insights      |
|  Nav     |  Redline Engine          |  Details       |
|  240px   |  flex-1                  |  320px         |
+----------+---------------------------+----------------+
```
Used by: Legal Review, Negotiation, Contract Detail

**PATTERN C: Graph Workspace**
```
+------------------------------------------------------+
|  KPI Row + Filter Bar                                |
+----------+---------------------------+----------------+
|  LEFT    |  CENTER                  |  RIGHT         |
|  AI      |  Graph Canvas            |  Node Detail   |
|  Insights|  (interactive)           |  Drawer        |
|  Timeline|                          |  (slide-over)  |
+----------+---------------------------+----------------+
```
Used by: Relationship Graph

**PATTERN D: Drawer-Enhanced Dashboard**
```
+------------------------------------------------------+
|  KPI Row + Filter Bar                                |
+------------------------------------------------------+
|  +------------------------------------------------+  |
|  |  Data Table / Content Grid                     |  |
|  |                                                |  |
|  +------------------------------------------------+  |
|                                                      |
|  +------------------------------------------------+  |
|  |  Detail Drawer (slides from right)             |  |
|  |  ---------------------------                   |  |
|  |  Tabs: Overview, Risk, Spend, SLA, Audit       |  |
|  +------------------------------------------------+  |
+------------------------------------------------------+
```
Used by: Vendor 360, Supplier Directory, Contracts

### 5.2 Workspace-to-Module Mapping

| Module | Layout Pattern | Panels | Drawers |
|--------|---------------|--------|---------|
| Portfolio Risk | A (Full Dashboard) | Charts, Table, Sidebar | Contract Detail |
| CFO Dashboard | A (Full Dashboard) | Financial Charts, KPIs, Table | Risk Detail |
| Legal Review | B (3-Panel) | Queue, Clause, AI Copilot | Finding Detail |
| Vendor 360 | D (Drawer Dashboard) | Hero, Charts, Table | Supplier Drawer |
| Contract Detail | B (3-Panel) | Clauses, Viewer, Obligations | Version History |
| Negotiation Center | B (3-Panel) | Issues, Diff, Fallbacks | Issue Detail |
| Compliance Center | B (3-Panel) | Regulations, Findings, Insights | Finding Detail |
| Relationship Graph | C (Graph) | Insights, Graph, Node Detail | Node Drawer |
| Workflow Center | D (Drawer Dashboard) | Kanban, Table, KPIs | Workflow Detail |

### 5.3 Panel Collapsibility Rules

```
Left Panel:   Collapsible (hamburger icon) -- default: open on desktop, closed on tablet
Right Panel:  Collapsible (panel icon) -- default: open on desktop, closed on mobile
AI Copilot:   Toggle (FAB) -- always available, overlays on mobile
Detail Drawer: Always slide-over, never pushes content
```

---

## 6. Enterprise Search Integration

### 6.1 Search Architecture

```
GLOBAL SEARCH BAR (TopNav -- always visible)
+-------------------------------------------------------------------+
|  Search contracts, vendors, clauses, obligations...              |
+-------------------------------------------------------------------+

RESULTS OVERLAY (Cmd+K)
+-------------------------------------------------------------------+
|  +-------------+  +-------------+  +---------------------------+  |
|  |  QUICK      |  |  ENTITIES   |  |  AI SUGGESTIONS           |  |
|  |  Actions    |  |  ---------   |  |  -------------            |  |
|  |  "New       |  |  Contracts  |  |  "Show me high-           |  |
|  |  contract"  |  |  Vendors    |  |  risk contracts           |  |
|  |  "Upload"   |  |  Clauses    |  |  with uncapped            |  |
|  |  "Report"   |  |  Workflows  |  |  liability"               |  |
|  +-------------+  +-------------+  +---------------------------+  |
+-------------------------------------------------------------------+
```

### 6.2 Search Scopes

| Scope | Sources | AI Behavior |
|-------|---------|-------------|
| **Global** | All entities + documents | Semantic + keyword hybrid |
| **Module-Scoped** | Current module only | Context-aware ranking |
| **Entity-Scoped** | Specific entity type (contracts only) | Filtered + smart suggestions |
| **Saved Search** | User-defined persistent queries | Auto-refresh + alerts |
| **AI Natural Language** | Full platform | "Find contracts with uncapped liability over $5M" |

### 6.3 Relationship-Aware Navigation

Search results include relationship indicators:
```
Result: MSA-AcmeCorp (Contract)
  +-- Vendor: Acme Corp (risk: 8.2/10)
  +-- Clauses: 24 (3 high-risk)
  +-- Obligations: 7 (2 overdue)
  +-- Workflow: Legal Review (SLA: 5h remaining)
```

---

## 7. Notification & Activity System

### 7.1 Notification Center Architecture

```
NOTIFICATION CENTER (TopNav Bell Icon)
+---------------------------------------------------------------------+
|  +----------+----------+----------+----------+------------------+  |
|  |  ALL     | ALERTS   | TASKS    | AI       | ESCALATIONS      |  |
|  |  (24)    | (8)      | (12)     | (4)      | (3)              |  |
|  +----------+----------+----------+----------+------------------+  |
|                                                                     |
|  SLA Breach: SecureNet Solutions                       2m ago     |
|     3rd consecutive month below 99.9% uptime                      |
|                                                                     |
|  Contract Expiring: CloudServ Ltd                      1h ago     |
|     $2.8M renewal requires VP approval                             |
|                                                                     |
|  AI Insight: Liability Threshold                       3h ago     |
|     3 vendors exceed acceptable limits                             |
|                                                                     |
|  Task: Quarterly Risk Review                           1d ago     |
|     7 high-risk suppliers remaining                                |
|                                                                     |
+---------------------------------------------------------------------+
```

### 7.2 Notification Types & Routing

| Type | Source | Severity | Delivery | AI Involvement |
|------|--------|----------|----------|----------------|
| SLA Breach | Workflow Center | Critical | Push + Banner | AI suggests remediation |
| Contract Expiry | Contracts | Warning | Push + Email | AI recommends renewal strategy |
| AI Finding | AI Copilot | Contextual | Inline + Bell | AI generates finding |
| Task Assignment | Workflows | Info | Bell + Toast | AI prioritizes queue |
| Escalation | Legal Review | Critical | Push + Bell + Email | AI drafts escalation summary |
| Compliance Gap | Compliance Center | Warning | Bell + Email | AI maps to regulation |
| Benchmark Alert | Benchmarks | Info | Bell | AI compares to market |

---

## 8. Multi-Tenant & RBAC Navigation

### 8.1 Tenant-Aware Navigation

```
TENANT SWITCHER (Admin only)
+--------------------------------------------------------------+
|  Acme Corp (Current)  v                                     |
|  -----------------------------------------------------       |
|  |  Acme Corp        |  1,234 contracts |  Active          |
|  |  BetaCorp         |  567 contracts   |  Active          |
|  |  Gamma Industries |  89 contracts    |  Trial           |
+--------------------------------------------------------------+
```

### 8.2 RBAC Visibility Matrix

| Module | Admin | Analyst | Viewer | Legal | Procurement | Compliance |
|--------|-------|---------|--------|-------|-------------|------------|
| Portfolio Risk | Full | Full | Read | Read | Read | Read |
| CFO Dashboard | Full | Full | Read | - | - | Read |
| Contracts Repository | Full | Full | Read | Full | Read | Read |
| Contract Detail | Full | Full | Read | Full | Read | Read |
| Clause Library | Full | Full | Read | Full | - | Read |
| Legal Review | Full | Full | - | Full | - | - |
| Negotiation Center | Full | Full | - | Full | - | - |
| Vendor 360 | Full | Full | Read | Read | Full | Read |
| Supplier Directory | Full | Full | Read | - | Full | - |
| Compliance Center | Full | Full | Read | - | - | Full |
| Obligation Center | Full | Full | Read | Read | - | Full |
| Workflow Center | Full | Full | - | Full | Full | Full |
| Admin Console | Full | - | - | - | - | - |

---

## 9. Mobile & Responsive Strategy

### 9.1 Responsive Breakpoints

| Breakpoint | Width | Layout | Behavior |
|-----------|-------|--------|----------|
| **Desktop** | >=1280px | Full 3-panel | All panels visible |
| **Tablet** | 768-1279px | 2-panel adaptive | Right panel becomes drawer |
| **Mobile** | <768px | Single panel | All panels stack, AI FAB overlays |

### 9.2 Mobile Navigation

```
Mobile Navigation (Bottom Tab Bar):
+---------------------------------------------------------------------+
|                                                                     |
|  [Content Area -- single panel, full width]                        |
|                                                                     |
|                                                                     |
+---------------------------------------------------------------------+
|  Intel  |  Cont  |  Proc  |  Legal  |  Alerts  |  AI              |
+---------------------------------------------------------------------+
```

### 9.3 Responsive Workspace Rules

```
Desktop:    Left Panel | Center Panel | Right Panel | AI Copilot (FAB)
Tablet:     Left Panel | Center Panel | [Right Panel = Drawer] | AI FAB
Mobile:     [Single Panel] | [All others = Drawers] | AI FAB (bottom)
```

---

## 10. Design System Foundations

### 10.1 Layout Standards

| Element | Desktop | Tablet | Mobile |
|---------|---------|--------|--------|
| Sidebar | 240px (collapsed: 64px) | 64px (collapsed) | Hidden (hamburger) |
| Left Panel | 240-320px | 240px | Full-width drawer |
| Right Panel | 320-420px | Drawer | Drawer |
| Content Max-Width | 1440px | 100% | 100% |
| Spacing (padding) | 24px | 16px | 12px |
| Grid Gap | 16px | 12px | 8px |

### 10.2 Typography Hierarchy

```
H1 (Page Title):     text-xl font-bold       -- 20px, 700 weight
H2 (Section):        text-sm font-semibold   -- 14px, 600 weight
H3 (Card Title):     text-xs font-semibold   -- 12px, 600 weight
Body:                text-sm                 -- 14px, 400 weight
Small:               text-[11px]             -- 11px, 400 weight
Caption:             text-[10px]             -- 10px, 500 weight (uppercase)
Data (tabular):      tabular-nums            -- monospaced numbers
```

### 10.3 Component Standards

| Component | Pattern | States | AI Enhancement |
|-----------|---------|--------|----------------|
| **KPI Card** | Icon + Value + Trend + Sparkline | Default, Hover, Active | AI confidence indicator |
| **Data Table** | Sortable, Filterable, Paginated | Default, Hover, Selected, Bulk | AI row highlighting |
| **Detail Drawer** | Slide-over, Multi-tab, Sticky header | Open, Closing | AI insight tab |
| **Filter Bar** | Horizontal dropdowns + chips | Default, Active, Reset | AI filter suggestions |
| **Chart** | Recharts (Area, Bar, Pie, Composed) | Interactive tooltip | AI annotation overlay |
| **Badge** | Risk/Status indicator | Critical, High, Medium, Low, Info | AI confidence badge |
| **Button** | Primary, Secondary, Ghost, Danger | Default, Hover, Active, Disabled | AI action button |
| **Toast** | Notification popup | Success, Error, Warning, Info | AI-generated message |

### 10.4 Data Grid Standards

```
+---------------------------------------------------------------------+
|  Column Types:                                                     |
|  +----------+----------+----------+----------+------------------+  |
|  |  Entity  |  Risk    |  Status  |  Numeric |  AI Confidence   |  |
|  |  (link)  |  Badge   |  Badge   |  ($/num) |  Bar + %         |  |
|  +----------+----------+----------+----------+------------------+  |
|  |  Acme    |  8.2/10  |  At Risk |  $12.4M  |  ######## 84%   |  |
|  |  Corp    |          |          |          |                  |  |
|  +----------+----------+----------+----------+------------------+  |
|                                                                     |
|  Interaction: Click row -> Detail Drawer                            |
|  Checkbox -> Bulk actions toolbar                                   |
|  Sort: Click column header                                          |
|  Filter: Column-specific dropdown                                  |
|  Pagination: 12/25/50/100 per page                                 |
+---------------------------------------------------------------------+
```

---

## 11. Collaboration Architecture

### 11.1 Collaboration Surfaces

| Surface | Location | Capabilities |
|---------|----------|--------------|
| **Comments** | Clause-level (inline) | Threaded, @mentions, resolve |
| **Annotations** | Document viewer | Highlight, note, share |
| **Approvals** | Workflow Center | Multi-stage, conditional routing |
| **Escalations** | Legal Review, Workflows | Level-based, auto-routing |
| **Shared Workspaces** | Any module | Team-based views, saved filters |
| **Activity Feed** | Right panel, Drawer | Real-time, filterable by type |

### 11.2 Activity Feed Architecture

```
ACTIVITY STREAM
-----------------------------

Today
+-- Alice Chen reviewed Clause 4.2 in MSA-AcmeCorp      2m ago
+-- Bob Martinez approved CloudServ Renewal              15m ago
+-- AI detected liability gap in SecureNet contract      1h ago
+-- Carol Singh escalated DataSync compliance issue      3h ago

Yesterday
+-- David Kim completed Q2 Risk Review                   1d ago
+-- Eve Johnson uploaded 12 new contracts                1d ago
+-- AI generated 4 savings recommendations               1d ago
```

---

## 12. Executive Experience Strategy

### 12.1 Executive Dashboard Layout

```
EXECUTIVE BRIEFING (Default view for C-suite)
+--------------------------------------------------------------+
|  AI Executive Summary (generated, contextual)                |
|  "Portfolio risk is stable. 3 critical items need attention: |
|   - SecureNet SLA breach (day 3 of 5)                       |
|   - CloudServ renewal ($2.8M) requires approval             |
|   - 2 new compliance findings under GDPR Article 32"        |
+--------------------------------------------------------------+

+--------------+ +--------------+ +--------------+ +----------+
| Portfolio    | | Revenue at   | | Compliance   | | AI       |
| Health 87%   | | Risk $4.2M   | | Score 92%    | | Insights |
+--------------+ +--------------+ +--------------+ +----------+

+--------------------------------------------------------------+
|  Trend: Portfolio Risk Over Time (Area Chart)                |
+--------------------------------------------------------------+

+----------------------+ +------------------------------------+
|  Top Risks (Table)   | |  Upcoming Renewals (Timeline)      |
+----------------------+ +------------------------------------+
```

### 12.2 Board Reporting Navigation

```
Executive Analytics -> Report Builder -> Select Template
    -> "Board Summary" -> AI Generates Report
    -> Review -> Export PDF -> Schedule Recurring
```

---

## 13. Scalability Recommendations

### 13.1 Module Isolation

Each module should be:
- **Lazy-loaded** (Next.js dynamic imports)
- **State-isolated** (module-level context providers)
- **API-independent** (own data fetching layer)
- **Testable in isolation** (module-level storybook stories)

### 13.2 Navigation Performance

| Strategy | Implementation |
|----------|---------------|
| Prefetching | Next.js `<Link prefetch>` for top-level modules |
| View Transition | Framer Motion `AnimatePresence` with `mode="wait"` |
| State Preservation | Module context persists across navigation |
| Lazy Loading | Dynamic imports for all sub-modules |
| Cache Strategy | SWR/React Query with stale-while-revalidate |

### 13.3 Cross-Module Communication

```
Event Bus Pattern:
  Module A -> dispatches event -> Event Bus -> Module B listens -> updates

Events:
  contract.selected    -> { contractId, vendorId }
  workflow.changed     -> { workflowId, status }
  ai.finding.created   -> { findingId, severity, entityId }
  notification.new     -> { type, title, action }
  search.triggered     -> { query, scope }
```

### 13.4 Future Module Expansion Points

| Expansion Area | Integration Point | Current Placeholder |
|---------------|-------------------|-------------------|
| AI Contract Drafting | Legal Review -> Drafting | AI Copilot integration |
| Automated Negotiation | Negotiation Center | AI fallback suggestions |
| Supply Chain Risk | Vendor 360 | Supplier concentration |
| ESG Compliance | Compliance Center | Regulation mapping |
| Insurance Intelligence | CFO Dashboard | Risk exposure |
| Real-time Collaboration | All modules | Comment system |

---

## 14. Implementation Roadmap

### 14.1 Phase 1 -- Foundation (Current)
- [x] Portfolio Risk Dashboard
- [x] Legal Review Workspace
- [x] Vendor 360 Workspace
- [x] Contract Detail Workspace
- [x] AI Copilot (global)
- [x] Global navigation (Sidebar + TopNav)

### 14.2 Phase 2 -- Expansion
- [ ] Navigation group restructuring (7 groups)
- [ ] Enterprise search (Cmd+K overlay)
- [ ] Notification center
- [ ] Role-based landing pages
- [ ] Module lazy loading
- [ ] AI context propagation

### 14.3 Phase 3 -- Enterprise
- [ ] Multi-tenant navigation
- [ ] Mobile responsive navigation
- [ ] Saved searches + alerts
- [ ] Executive briefing automation
- [ ] Collaboration surfaces (comments, mentions)
- [ ] Activity feed consolidation

### 14.4 Phase 4 -- AI-First
- [ ] Proactive AI triggers
- [ ] AI-driven navigation suggestions
- [ ] Semantic search across all entities
- [ ] AI workflow orchestration
- [ ] Executive AI briefings (auto-generated)

---

## 15. Summary: Key Architectural Decisions

1. **7 navigation groups** -- Intelligence, Contracts, Procurement, Legal Ops, Compliance, Workflows, Admin
2. **18 primary modules** -- Each with consistent workspace patterns
3. **4 canonical layouts** -- Full Dashboard, 3-Panel, Graph, Drawer-Enhanced
4. **Max depth 4** -- Never more than 4 clicks to any piece of data
5. **Persistent AI Copilot** -- Context-aware across all navigation
6. **Entity cross-linking** -- Every entity links to every related entity
7. **Role-based visibility** -- 5 personas with distinct default experiences
8. **Responsive 3-tier** -- Desktop (full), Tablet (adaptive), Mobile (stacked)
9. **Event bus** -- Modules communicate through typed events
10. **Lazy loading** -- All modules are dynamically imported
