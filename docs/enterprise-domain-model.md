# ContractRiskEdge — Enterprise Domain Model & Entity Relationship Architecture

## Fortune 500 AI-Native Contract Intelligence Operating System

---

## Table of Contents

1. [Domain Model Overview](#1-domain-model-overview)
2. [Canonical Entity Definitions](#2-canonical-entity-definitions)
3. [Contract Domain Architecture](#3-contract-domain-architecture)
4. [Clause & Playbook Domain](#4-clause--playbook-domain)
5. [Workflow & Approval Domain](#5-workflow--approval-domain)
6. [AI & Vector Architecture](#6-ai--vector-architecture)
7. [Search & Discovery Domain](#7-search--discovery-domain)
8. [Compliance Domain](#8-compliance-domain)
9. [Procurement & Vendor Domain](#9-procurement--vendor-domain)
10. [Analytics & Reporting Domain](#10-analytics--reporting-domain)
11. [Multi-Tenant Architecture](#11-multi-tenant-architecture)
12. [RBAC & Security Domain](#12-rbac--security-domain)
13. [Event-Driven Architecture](#13-event-driven-architecture)
14. [Database Optimization Strategy](#14-database-optimization-strategy)
15. [Master Entity Relationship Map](#15-master-entity-relationship-map)

---

## 1. Domain Model Overview

### 1.1 Bounded Contexts

The platform is organized into **12 bounded contexts**, each representing a distinct business capability with its own ubiquitous language, data ownership, and lifecycle management.

```
+------------------------------------------------------------------+
|                    ContractRiskEdge Platform                       |
+------------------------------------------------------------------+
|                                                                    |
|  +------------------+  +------------------+  +------------------+ |
|  | Contract Lifecycle|  | AI Intelligence  |  | Workflow Engine  | |
|  | - Repository      |  | - RAG Pipeline   |  | - Approvals      | |
|  | - Versions        |  | - Embeddings     |  | - Escalations    | |
|  | - Amendments      |  | - Classification |  | - SLA Tracking   | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                    |
|  +------------------+  +------------------+  +------------------+ |
|  | Procurement Intel|  | Compliance Mgmt  |  | Legal Operations | |
|  | - Vendors        |  | - Regulations    |  | - Negotiations   | |
|  | - Spend          |  | - Obligations    |  | - Redlines       | |
|  | - SLA            |  | - Audit          |  | - Review Queue   | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                    |
|  +------------------+  +------------------+  +------------------+ |
|  | Analytics & BI   |  | Search & Discovery|  | Ingestion & OCR  | |
|  | - KPIs           |  | - Semantic       |  | - Document Proc  | |
|  | - Forecasting    |  | - Saved Searches |  | - Extraction     | |
|  | - Benchmarks     |  | - Relationship   |  | - Classification | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                    |
|  +------------------+  +------------------+  +------------------+ |
|  | Identity & Access|  | Notification     |  | Collaboration    | |
|  | - Multi-Tenant   |  | - Alerts         |  | - Comments       | |
|  | - RBAC           |  | - Escalations    |  | - Activity Feed  | |
|  | - Audit          |  | - Webhooks       |  | - Mentions       | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                    |
+------------------------------------------------------------------+
```

### 1.2 Domain Event Boundaries

```
Contract Context       AI Context           Workflow Context
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ Contract     │──────>│ AI Analysis  │──────>│ Workflow     │
│ Uploaded     │      │ Generated    │      │ Triggered    │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                      │
       v                     v                      v
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ OCR          │      │ Clause       │      │ Approval     │
│ Completed    │      │ Analyzed     │      │ Requested    │
└──────────────┘      └──────────────┘      └──────────────┘
```

### 1.3 Entity Count by Bounded Context

| Bounded Context | Primary Entities | Description |
|----------------|-----------------|-------------|
| Contract Lifecycle | 5 | Contract, ContractVersion, Amendment, MasterAgreement, Renewal |
| AI Intelligence | 6 | AIAnalysis, AIPrompt, AIOutput, EmbeddingVector, Chunk, Citation |
| Workflow Engine | 5 | Workflow, WorkflowStep, Approval, Escalation, SLAMetric |
| Procurement Intel | 5 | Vendor, VendorRisk, SpendRecord, ProcurementWorkflow, SLA |
| Compliance Mgmt | 5 | ComplianceRequirement, ComplianceFinding, Obligation, Remediation, AuditEvent |
| Legal Operations | 4 | Negotiation, Redline, Clause, ClauseVariant |
| Analytics & BI | 3 | AnalyticsSnapshot, KpiMetric, Forecast |
| Search & Discovery | 3 | SearchIndex, SavedSearch, SearchAnalytics |
| Ingestion & OCR | 3 | IngestionJob, ExtractedPage, ExtractionResult |
| Identity & Access | 4 | Tenant, User, Role, Permission |
| Notification | 3 | Notification, Webhook, AlertRule |
| Collaboration | 3 | Comment, ActivityFeed, Team |

**Total: 40 canonical entities** across 12 bounded contexts.

---

## 2. Canonical Entity Definitions

### 2.1 Identity & Access Context

---

#### Entity: `tenants`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| tenant_id | UUID | PK, DEFAULT uuid_generate_v4() | Unique tenant identifier |
| name | TEXT | NOT NULL | Organization name |
| domain | TEXT | UNIQUE, NULLABLE | Verified domain for SSO |
| plan | TEXT | NOT NULL, DEFAULT 'starter' | Subscription tier |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Soft disable |
| max_users | INTEGER | NOT NULL, DEFAULT 10 | Seat limit |
| max_documents | INTEGER | NOT NULL, DEFAULT 1000 | Document storage limit |
| features | TEXT[] | NOT NULL, DEFAULT '{}' | Feature flags |
| settings | JSONB | NOT NULL, DEFAULT '{}' | Tenant configuration |
| encryption_key_id | TEXT | NULLABLE | KMS key for tenant-level encryption |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| deleted_at | TIMESTAMPTZ | NULLABLE | Soft delete |

**Indexes:** `tenants_pkey`, `idx_tenants_domain` (partial, WHERE domain IS NOT NULL)
**RLS:** N/A (root table)
**Soft Delete:** `deleted_at` — cascading soft-delete to all tenant data
**Audit:** All mutations logged to `audit_logs`

---

#### Entity: `users`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| user_id | TEXT | PK | Auth0 `sub` claim |
| email | TEXT | NOT NULL | Verified email |
| name | TEXT | NULLABLE | Display name |
| tenant_id | UUID | NOT NULL, FK -> tenants | Primary tenant |
| role | user_role | NOT NULL, DEFAULT 'viewer' | System role |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Account active |
| permissions | TEXT[] | NOT NULL, DEFAULT '{}' | Granular permissions |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | User preferences, profile |
| last_login | TIMESTAMPTZ | NULLABLE | Last authentication |
| mfa_enabled | BOOLEAN | NOT NULL, DEFAULT FALSE | Multi-factor auth |
| api_key_hash | TEXT | NULLABLE | Hashed API key |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| deleted_at | TIMESTAMPTZ | NULLABLE | Soft delete |

**Indexes:** `users_pkey`, `idx_users_tenant`, `idx_users_email`, `idx_users_tenant_email` (UNIQUE)
**RLS:** `tenant_id = get_current_tenant_id()`
**Soft Delete:** `deleted_at`

---

#### Entity: `roles`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| role_id | UUID | PK | |
| tenant_id | UUID | NOT NULL, FK -> tenants | |
| name | TEXT | NOT NULL | Role name (e.g., "Legal Reviewer") |
| description | TEXT | NULLABLE | |
| is_system | BOOLEAN | NOT NULL, DEFAULT FALSE | System-defined (not deletable) |
| permissions | TEXT[] | NOT NULL, DEFAULT '{}' | Permission codes |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `roles_pkey`, `idx_roles_tenant`
**RLS:** `tenant_id = get_current_tenant_id()`

---

#### Entity: `permissions`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| permission_id | UUID | PK | |
| code | TEXT | NOT NULL, UNIQUE | Machine-readable (e.g., "contract:read") |
| label | TEXT | NOT NULL | Human-readable |
| resource | TEXT | NOT NULL | Resource type (contract, vendor, etc.) |
| action | TEXT | NOT NULL | Action (create, read, update, delete, approve) |
| scope | TEXT | NOT NULL, DEFAULT 'tenant' | tenant, team, own |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `permissions_pkey`, `idx_permissions_code` (UNIQUE)
**Note:** This is a system table — not tenant-specific.

---

#### Entity: `teams`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| team_id | UUID | PK | |
| tenant_id | UUID | NOT NULL, FK -> tenants | |
| name | TEXT | NOT NULL | Team name |
| description | TEXT | NULLABLE | |
| parent_team_id | UUID | NULLABLE, FK -> teams | Hierarchical nesting |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| deleted_at | TIMESTAMPTZ | NULLABLE | |

**Indexes:** `teams_pkey`, `idx_teams_tenant`, `idx_teams_parent`
**RLS:** `tenant_id = get_current_tenant_id()`

---

#### Entity: `team_members`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| team_member_id | UUID | PK | |
| team_id | UUID | NOT NULL, FK -> teams | |
| user_id | TEXT | NOT NULL, FK -> users | |
| role_id | UUID | NOT NULL, FK -> roles | Team-level role |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `team_members_pkey`, `idx_team_members_team`, `idx_team_members_user`, UNIQUE(team_id, user_id)

---

### 2.2 Contract Lifecycle Context

---

#### Entity: `contracts`

**Current Schema (already exists):**
```sql
CREATE TABLE contracts (
    contract_id    UUID,
    tenant_id      UUID NOT NULL,
    user_id        TEXT NOT NULL,
    filename       TEXT NOT NULL,
    content_type   TEXT NOT NULL,
    file_size      BIGINT NOT NULL DEFAULT 0,
    file_path      TEXT,
    checksum       TEXT,
    status         contract_status NOT NULL DEFAULT 'pending',
    contract_type  contract_type,
    version        INTEGER NOT NULL DEFAULT 1,
    total_pages    INTEGER NOT NULL DEFAULT 0,
    total_clauses  INTEGER NOT NULL DEFAULT 0,
    total_chunks   INTEGER NOT NULL DEFAULT 0,
    risk_score     REAL CHECK (risk_score >= 0.0 AND risk_score <= 1.0),
    tags           TEXT[] NOT NULL DEFAULT '{}',
    metadata       JSONB NOT NULL DEFAULT '{}',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at    TIMESTAMPTZ,
    deleted_at     TIMESTAMPTZ,
    PRIMARY KEY (tenant_id, contract_id)
) PARTITION BY HASH (tenant_id);
```

**Proposed Extensions:**

| Additional Attribute | Type | Constraints | Description |
|---------------------|------|-------------|-------------|
| contract_value | NUMERIC(15,2) | NULLABLE | Total contract value |
| currency | TEXT | DEFAULT 'USD' | ISO currency code |
| start_date | DATE | NULLABLE | Contract effective date |
| end_date | DATE | NULLABLE | Contract expiration date |
| auto_renewal | BOOLEAN | DEFAULT FALSE | Auto-renewal clause present |
| renewal_notice_days | INTEGER | NULLABLE | Days required for renewal notice |
| governing_law | TEXT | NULLABLE | Jurisdiction |
| signing_date | DATE | NULLABLE | Date of execution |
| counterparty_id | UUID | NULLABLE, FK -> vendors | Linked vendor |
| master_agreement_id | UUID | NULLABLE, FK -> contracts | Parent MSA |
| review_status | TEXT | DEFAULT 'pending' | pending_review, in_review, approved, rejected |
| assigned_reviewer_id | TEXT | NULLABLE, FK -> users | Current reviewer |
| sla_deadline | TIMESTAMPTZ | NULLABLE | Review SLA deadline |
| search_vector | tsvector | GENERATED ALWAYS AS (...) STORED | Full-text search |

**Lifecycle States:**
```
UPLOADED -> PENDING -> PROCESSING -> READY -> UNDER_REVIEW -> APPROVED/REJECTED
                |            |                                    |
                v            v                                    v
             ERROR        ERROR                              ARCHIVED
```

**Relationships:**
- `contracts` 1:N -> `contract_versions`
- `contracts` 1:N -> `clauses`
- `contracts` 1:N -> `chunks`
- `contracts` 1:N -> `extracted_pages`
- `contracts` 1:N -> `risk_reports`
- `contracts` 1:N -> `ai_analyses`
- `contracts` 1:N -> `obligations`
- `contracts` N:M -> `contracts` (via `contract_relationships`)
- `contracts` N:1 -> `vendors`

---

#### Entity: `contract_versions`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| version_id | UUID | PK | |
| contract_id | UUID | NOT NULL, FK -> contracts | |
| tenant_id | UUID | NOT NULL | |
| version_number | INTEGER | NOT NULL, CHECK >= 1 | Sequential version |
| filename | TEXT | NOT NULL | Version-specific file |
| file_size | BIGINT | NOT NULL, DEFAULT 0 | |
| file_path | TEXT | NULLABLE | S3 path |
| checksum | TEXT | NOT NULL | SHA-256 |
| change_notes | TEXT | NULLABLE | Description of changes |
| created_by | TEXT | NOT NULL, FK -> users | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_contract_versions_contract`, UNIQUE(contract_id, version_number)
**RLS:** `tenant_id = get_current_tenant_id()`

---

#### Entity: `contract_relationships`

**Current Schema (already exists):**
```sql
CREATE TABLE contract_relationships (
    relationship_id      UUID PRIMARY KEY,
    parent_contract_id   UUID NOT NULL,
    child_contract_id    UUID NOT NULL,
    relationship_type    relationship_type NOT NULL,  -- parent, child, amendment, addendum, dpa
    effective_date       DATE,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (parent_contract_id) REFERENCES contracts(contract_id),
    FOREIGN KEY (child_contract_id) REFERENCES contracts(contract_id)
);
```

**Proposed Extensions:**
| Additional Attribute | Type | Constraints | Description |
|---------------------|------|-------------|-------------|
| tenant_id | UUID | NOT NULL | For RLS |
| is_active | BOOLEAN | DEFAULT TRUE | Soft-disable relationship |
| superseded_by | UUID | NULLABLE, FK -> contract_relationships | Replacement relationship |

---

#### Entity: `renewals`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| renewal_id | UUID | PK | |
| contract_id | UUID | NOT NULL, FK -> contracts | |
| tenant_id | UUID | NOT NULL | |
| renewal_date | DATE | NOT NULL | Scheduled renewal date |
| status | TEXT | NOT NULL, DEFAULT 'pending' | pending, in_progress, completed, expired |
| forecast_value | NUMERIC(15,2) | NULLABLE | Projected renewal value |
| probability | REAL | NULLABLE, CHECK 0-1 | AI-predicted renewal likelihood |
| auto_renewal | BOOLEAN | DEFAULT FALSE | |
| notice_deadline | DATE | NULLABLE | Last date to provide notice |
| assigned_owner | TEXT | NULLABLE, FK -> users | |
| notes | TEXT | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_renewals_contract`, `idx_renewals_date`, `idx_renewals_status`
**RLS:** `tenant_id = get_current_tenant_id()`

---

### 2.3 AI Intelligence Context

---

#### Entity: `ai_analyses`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| analysis_id | UUID | PK | |
| contract_id | UUID | NOT NULL, FK -> contracts | |
| tenant_id | UUID | NOT NULL | |
| analysis_type | TEXT | NOT NULL | risk_analysis, clause_classification, obligation_extraction, sentiment, summarization |
| model_id | TEXT | NOT NULL | Model identifier (e.g., "gpt-4o", "claude-3") |
| model_version | TEXT | NULLABLE | Specific model version |
| status | TEXT | NOT NULL, DEFAULT 'pending' | pending, processing, completed, failed |
| confidence | REAL | NULLABLE, CHECK 0-1 | Overall confidence score |
| latency_ms | INTEGER | NULLABLE | Processing time |
| token_count | INTEGER | NULLABLE | Tokens consumed |
| cost_usd | NUMERIC(10,6) | NULLABLE | Cost of inference |
| prompt_id | UUID | NULLABLE, FK -> ai_prompts | Linked prompt |
| output_id | UUID | NULLABLE, FK -> ai_outputs | Linked output |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| completed_at | TIMESTAMPTZ | NULLABLE | |

**Indexes:** `idx_ai_analyses_contract`, `idx_ai_analyses_type`, `idx_ai_analyses_status`, `idx_ai_analyses_created`
**RLS:** `tenant_id = get_current_tenant_id()`
**Audit:** Every AI analysis is immutable — once completed, it cannot be modified.

---

#### Entity: `ai_prompts`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| prompt_id | UUID | PK | |
| tenant_id | UUID | NOT NULL | |
| prompt_type | TEXT | NOT NULL | system, user, agent_config |
| prompt_text | TEXT | NOT NULL | The actual prompt |
| prompt_template_id | UUID | NULLABLE | Reference to reusable template |
| version | INTEGER | NOT NULL, DEFAULT 1 | |
| parameters | JSONB | NOT NULL, DEFAULT '{}' | Template parameters |
| token_count | INTEGER | NOT NULL, DEFAULT 0 | |
| hash | TEXT | NOT NULL | SHA-256 of prompt text |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_ai_prompts_type`, `idx_ai_prompts_hash`
**RLS:** `tenant_id = get_current_tenant_id()`

---

#### Entity: `ai_outputs`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| output_id | UUID | PK | |
| analysis_id | UUID | NOT NULL, FK -> ai_analyses | |
| tenant_id | UUID | NOT NULL | |
| output_type | TEXT | NOT NULL | classification, extraction, generation, scoring |
| content | JSONB | NOT NULL | Structured output |
| raw_text | TEXT | NULLABLE | Raw model response |
| confidence | REAL | NULLABLE, CHECK 0-1 | Per-output confidence |
| citations | JSONB | NOT NULL, DEFAULT '[]' | Source citations [{source, excerpt, relevance}] |
| reasoning | TEXT | NULLABLE | Chain-of-thought |
| token_count | INTEGER | NULLABLE | |
| latency_ms | INTEGER | NULLABLE | |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_ai_outputs_analysis`, `idx_ai_outputs_type`
**RLS:** `tenant_id = get_current_tenant_id()`

---

#### Entity: `chunks` (with pgvector embeddings)

**Current Schema (already exists):**
```sql
CREATE TABLE chunks (
    chunk_id       UUID PRIMARY KEY,
    contract_id    UUID NOT NULL,
    tenant_id      UUID NOT NULL,
    chunk_index    INTEGER NOT NULL,
    text           TEXT NOT NULL,
    token_count    INTEGER NOT NULL CHECK (token_count >= 1),
    embedding      vector(1536),
    clause_ids     UUID[] NOT NULL DEFAULT '{}',
    page_numbers   INTEGER[] NOT NULL DEFAULT '{}',
    metadata       JSONB NOT NULL DEFAULT '{}',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
);
```

**Proposed Extensions:**
| Additional Attribute | Type | Constraints | Description |
|---------------------|------|-------------|-------------|
| embedding_model | TEXT | DEFAULT 'text-embedding-3-large' | Model used for embedding |
| embedding_dimension | INTEGER | DEFAULT 1536 | |
| chunking_strategy | TEXT | DEFAULT 'semantic' | semantic, fixed_size, sentence |
| parent_chunk_id | UUID | NULLABLE, FK -> chunks | Hierarchical chunking |
| is_active | BOOLEAN | DEFAULT TRUE | For re-indexing |

---

#### Entity: `citations`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| citation_id | UUID | PK | |
| output_id | UUID | NOT NULL, FK -> ai_outputs | |
| chunk_id | UUID | NULLABLE, FK -> chunks | Referenced chunk |
| clause_id | UUID | NULLABLE, FK -> clauses | Referenced clause |
| contract_id | UUID | NOT NULL, FK -> contracts | Source contract |
| tenant_id | UUID | NOT NULL | |
| excerpt | TEXT | NOT NULL | Source text excerpt |
| relevance | REAL | NOT NULL, CHECK 0-1 | Relevance score |
| start_char | INTEGER | NULLABLE | Character offset in source |
| end_char | INTEGER | NULLABLE | Character offset in source |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_citations_output`, `idx_citations_chunk`, `idx_citations_clause`

---

### 2.4 Workflow Engine Context

---

#### Entity: `workflows`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| workflow_id | UUID | PK | |
| tenant_id | UUID | NOT NULL, FK -> tenants | |
| workflow_type | TEXT | NOT NULL | legal_review, procurement_approval, compliance_remediation, onboarding, renewal |
| entity_type | TEXT | NOT NULL | contract, vendor, obligation, finding |
| entity_id | TEXT | NOT NULL | ID of the linked entity |
| status | TEXT | NOT NULL, DEFAULT 'pending' | pending, in_progress, completed, cancelled, escalated |
| priority | TEXT | NOT NULL, DEFAULT 'medium' | critical, high, medium, low |
| assigned_to | TEXT | NULLABLE, FK -> users | Current assignee |
| created_by | TEXT | NOT NULL, FK -> users | |
| sla_deadline | TIMESTAMPTZ | NULLABLE | SLA target |
| sla_breached | BOOLEAN | DEFAULT FALSE | |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| completed_at | TIMESTAMPTZ | NULLABLE | |

**Indexes:** `idx_workflows_tenant`, `idx_workflows_type`, `idx_workflows_status`, `idx_workflows_entity`, `idx_workflows_assignee`, `idx_workflows_sla`
**RLS:** `tenant_id = get_current_tenant_id()`

**Lifecycle States:**
```
PENDING -> IN_PROGRESS -> COMPLETED
    |            |
    v            v
CANCELLED    ESCALATED -> IN_PROGRESS
```

---

#### Entity: `workflow_steps`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| step_id | UUID | PK | |
| workflow_id | UUID | NOT NULL, FK -> workflows | |
| step_order | INTEGER | NOT NULL | Sequential ordering |
| step_type | TEXT | NOT NULL | approval, review, notification, escalation, automation |
| name | TEXT | NOT NULL | Step name |
| assigned_to | TEXT | NULLABLE, FK -> users | |
| status | TEXT | NOT NULL, DEFAULT 'pending' | pending, in_progress, approved, rejected, skipped |
| sla_minutes | INTEGER | NULLABLE | Time limit |
| completed_at | TIMESTAMPTZ | NULLABLE | |
| completed_by | TEXT | NULLABLE, FK -> users | |
| notes | TEXT | NULLABLE | |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_workflow_steps_workflow`, `idx_workflow_steps_assignee`

---

#### Entity: `approvals`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| approval_id | UUID | PK | |
| workflow_step_id | UUID | NOT NULL, FK -> workflow_steps | |
| tenant_id | UUID | NOT NULL | |
| approver_id | TEXT | NOT NULL, FK -> users | |
| status | TEXT | NOT NULL, DEFAULT 'pending' | pending, approved, rejected, conditionally_approved |
| comments | TEXT | NULLABLE | |
| conditions | JSONB | NULLABLE | Conditional approval terms |
| decided_at | TIMESTAMPTZ | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_approvals_step`, `idx_approvals_approver`, `idx_approvals_status`

---

#### Entity: `escalations`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| escalation_id | UUID | PK | |
| workflow_id | UUID | NOT NULL, FK -> workflows | |
| tenant_id | UUID | NOT NULL | |
| escalation_level | INTEGER | NOT NULL, DEFAULT 1 | 1, 2, 3 (increasing severity) |
| escalated_by | TEXT | NOT NULL, FK -> users | |
| escalated_to | TEXT | NOT NULL, FK -> users | Target recipient |
| reason | TEXT | NOT NULL | |
| status | TEXT | NOT NULL, DEFAULT 'open' | open, acknowledged, resolved |
| resolved_at | TIMESTAMPTZ | NULLABLE | |
| resolution_notes | TEXT | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_escalations_workflow`, `idx_escalations_to`, `idx_escalations_status`

---

#### Entity: `sla_metrics`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| sla_id | UUID | PK | |
| tenant_id | UUID | NOT NULL | |
| entity_type | TEXT | NOT NULL | contract, workflow, vendor |
| entity_id | TEXT | NOT NULL | |
| metric_name | TEXT | NOT NULL | review_time, response_time, resolution_time, uptime |
| target_value | REAL | NOT NULL | Target (hours, %, etc.) |
| actual_value | REAL | NULLABLE | Measured value |
| unit | TEXT | NOT NULL | hours, percentage, count |
| status | TEXT | NOT NULL, DEFAULT 'on_track' | on_track, at_risk, breached |
| breached_at | TIMESTAMPTZ | NULLABLE | |
| measured_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_sla_metrics_entity`, `idx_sla_metrics_status`, `idx_sla_metrics_tenant`

---

### 2.5 Legal Operations Context

---

#### Entity: `clauses`

**Current Schema (already exists):**
```sql
CREATE TABLE clauses (
    clause_id        UUID PRIMARY KEY,
    contract_id      UUID NOT NULL,
    tenant_id        UUID NOT NULL,
    page_id          UUID REFERENCES extracted_pages(page_id),
    clause_index     INTEGER NOT NULL,
    text             TEXT NOT NULL,
    section_number   TEXT,
    heading          TEXT,
    clause_type      TEXT,
    level            INTEGER NOT NULL DEFAULT 1,
    parent_clause_id UUID REFERENCES clauses(clause_id),
    start_char       INTEGER NOT NULL,
    end_char         INTEGER NOT NULL,
    confidence       REAL NOT NULL DEFAULT 1.0,
    metadata         JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
);
```

**Proposed Extensions:**

| Additional Attribute | Type | Constraints | Description |
|---------------------|------|-------------|-------------|
| risk_score | REAL | NULLABLE, CHECK 0-1 | AI-assigned risk score |
| is_active | BOOLEAN | DEFAULT TRUE | For version comparison |
| benchmark_percentile | REAL | NULLABLE, CHECK 0-100 | Market benchmark percentile |
| playbook_id | UUID | NULLABLE, FK -> playbooks | Linked playbook entry |
| obligations | UUID[] | DEFAULT '{}' | Extracted obligation IDs |

---

#### Entity: `clause_variants`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| variant_id | UUID | PK | |
| clause_id | UUID | NOT NULL, FK -> clauses | Parent clause |
| tenant_id | UUID | NOT NULL | |
| variant_type | TEXT | NOT NULL | fallback, alternative, rejected, negotiated |
| text | TEXT | NOT NULL | Alternative text |
| source | TEXT | NULLABLE | playbook, ai_generated, manual, benchmark |
| confidence | REAL | NULLABLE, CHECK 0-1 | |
| is_approved | BOOLEAN | DEFAULT FALSE | Approved for use |
| approved_by | TEXT | NULLABLE, FK -> users | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_clause_variants_clause`, `idx_clause_variants_type`

---

#### Entity: `playbooks`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| playbook_id | UUID | PK | |
| tenant_id | UUID | NOT NULL, FK -> tenants | |
| name | TEXT | NOT NULL | Playbook name |
| description | TEXT | NULLABLE | |
| jurisdiction | TEXT | NULLABLE | Applicable legal jurisdiction |
| contract_type | contract_type | NULLABLE | Applicable contract type |
| is_active | BOOLEAN | DEFAULT TRUE | |
| version | INTEGER | NOT NULL, DEFAULT 1 | |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | |
| created_by | TEXT | NOT NULL, FK -> users | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_playbooks_tenant`, `idx_playbooks_active`

---

#### Entity: `playbook_entries`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| entry_id | UUID | PK | |
| playbook_id | UUID | NOT NULL, FK -> playbooks | |
| clause_type | TEXT | NOT NULL | Type of clause |
| preferred_text | TEXT | NOT NULL | Preferred language |
| fallback_text | TEXT | NULLABLE | Fallback language |
| rationale | TEXT | NULLABLE | Why this language is preferred |
| risk_level | risk_severity | NOT NULL | Risk if not used |
| is_required | BOOLEAN | DEFAULT FALSE | Must-have clause |
| order | INTEGER | NOT NULL, DEFAULT 0 | Display order |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_playbook_entries_playbook`, `idx_playbook_entries_type`

---

#### Entity: `negotiations`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| negotiation_id | UUID | PK | |
| contract_id | UUID | NOT NULL, FK -> contracts | |
| tenant_id | UUID | NOT NULL | |
| status | TEXT | NOT NULL, DEFAULT 'draft' | draft, in_progress, concluded, cancelled |
| counterparty | TEXT | NOT NULL | Counterparty name/contact |
| negotiation_type | TEXT | NOT NULL | new_contract, renewal, amendment, dispute |
| ai_insights | JSONB | DEFAULT '{}' | AI-generated negotiation insights |
| started_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| concluded_at | TIMESTAMPTZ | NULLABLE | |
| concluded_by | TEXT | NULLABLE, FK -> users | |
| outcome | TEXT | NULLABLE | successful, partial, failed |
| notes | TEXT | NULLABLE | |

**Indexes:** `idx_negotiations_contract`, `idx_negotiations_status`

---

#### Entity: `redlines`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| redline_id | UUID | PK | |
| clause_id | UUID | NOT NULL, FK -> clauses | |
| negotiation_id | UUID | NULLABLE, FK -> negotiations | |
| tenant_id | UUID | NOT NULL | |
| original_text | TEXT | NOT NULL | Before change |
| proposed_text | TEXT | NOT NULL | After change |
| change_type | TEXT | NOT NULL | addition, deletion, modification |
| status | TEXT | NOT NULL, DEFAULT 'proposed' | proposed, accepted, rejected, superseded |
| generated_by | TEXT | NOT NULL | ai, manual, playbook |
| ai_confidence | REAL | NULLABLE, CHECK 0-1 | |
| created_by | TEXT | NOT NULL, FK -> users | |
| resolved_by | TEXT | NULLABLE, FK -> users | |
| resolved_at | TIMESTAMPTZ | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_redlines_clause`, `idx_redlines_negotiation`, `idx_redlines_status`

---

### 2.6 Procurement & Vendor Context

---

#### Entity: `vendors`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| vendor_id | UUID | PK | |
| tenant_id | UUID | NOT NULL, FK -> tenants | |
| name | TEXT | NOT NULL | Legal entity name |
| duns_number | TEXT | NULLABLE, UNIQUE | DUNS identifier |
| tax_id | TEXT | NULLABLE | Tax registration |
| website | TEXT | NULLABLE | |
| country | TEXT | NULLABLE | HQ country |
| category | TEXT | NULLABLE | Cloud, Software, Consulting, etc. |
| status | TEXT | NOT NULL, DEFAULT 'active' | active, inactive, blocked, onboarding |
| risk_score | REAL | NULLABLE, CHECK 0-10 | Composite risk score |
| financial_stability | TEXT | NULLABLE | strong, stable, weak, distressed |
| insurance_compliant | BOOLEAN | DEFAULT FALSE | |
| sla_performance | REAL | NULLABLE, CHECK 0-100 | Average SLA score |
| total_spend | NUMERIC(15,2) | DEFAULT 0 | Lifetime spend |
| active_contracts | INTEGER | DEFAULT 0 | |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| deleted_at | TIMESTAMPTZ | NULLABLE | |

**Indexes:** `idx_vendors_tenant`, `idx_vendors_name`, `idx_vendors_category`, `idx_vendors_risk`, `idx_vendors_status`
**RLS:** `tenant_id = get_current_tenant_id()`

---

#### Entity: `vendor_risks`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| risk_id | UUID | PK | |
| vendor_id | UUID | NOT NULL, FK -> vendors | |
| tenant_id | UUID | NOT NULL | |
| risk_category | TEXT | NOT NULL | financial, compliance, geopolitical, operational, security |
| risk_score | REAL | NOT NULL, CHECK 0-10 | |
| risk_level | TEXT | NOT NULL | critical, high, medium, low |
| description | TEXT | NULLABLE | |
| ai_confidence | REAL | NULLABLE, CHECK 0-1 | |
| source | TEXT | NOT NULL | ai_analysis, manual, external_feed |
| detected_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| resolved_at | TIMESTAMPTZ | NULLABLE | |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | |

**Indexes:** `idx_vendor_risks_vendor`, `idx_vendor_risks_category`, `idx_vendor_risks_level`

---

#### Entity: `spend_records`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| spend_id | UUID | PK | |
| vendor_id | UUID | NOT NULL, FK -> vendors | |
| tenant_id | UUID | NOT NULL | |
| contract_id | UUID | NULLABLE, FK -> contracts | |
| fiscal_year | INTEGER | NOT NULL | |
| fiscal_quarter | INTEGER | NOT NULL, CHECK 1-4 | |
| amount | NUMERIC(15,2) | NOT NULL | |
| currency | TEXT | DEFAULT 'USD' | |
| category | TEXT | NULLABLE | cloud, software, consulting, etc. |
| department | TEXT | NULLABLE | Cost center |
| recorded_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_spend_records_vendor`, `idx_spend_records_period`, `idx_spend_records_category`

---

#### Entity: `procurement_workflows`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| procurement_id | UUID | PK | |
| tenant_id | UUID | NOT NULL | |
| workflow_type | TEXT | NOT NULL | sourcing, onboarding, renewal, sla_review |
| vendor_id | UUID | NOT NULL, FK -> vendors | |
| contract_id | UUID | NULLABLE, FK -> contracts | |
| status | TEXT | NOT NULL, DEFAULT 'draft' | draft, active, completed, cancelled |
| priority | TEXT | NOT NULL, DEFAULT 'medium' | |
| assigned_to | TEXT | NULLABLE, FK -> users | |
| sla_deadline | TIMESTAMPTZ | NULLABLE | |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

---

### 2.7 Compliance Context

---

#### Entity: `compliance_requirements`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| requirement_id | UUID | PK | |
| tenant_id | UUID | NOT NULL, FK -> tenants | |
| regulation | TEXT | NOT NULL | GDPR, CCPA, SOX, HIPAA, etc. |
| article | TEXT | NULLABLE | Specific article/section |
| title | TEXT | NOT NULL | Requirement title |
| description | TEXT | NOT NULL | Detailed requirement |
| risk_level | risk_severity | NOT NULL | |
| is_active | BOOLEAN | DEFAULT TRUE | |
| jurisdiction | TEXT | NULLABLE | EU, US, UK, etc. |
| effective_date | DATE | NULLABLE | |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_compliance_req_tenant`, `idx_compliance_req_regulation`, `idx_compliance_req_active`

---

#### Entity: `compliance_findings`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| finding_id | UUID | PK | |
| requirement_id | UUID | NOT NULL, FK -> compliance_requirements | |
| contract_id | UUID | NULLABLE, FK -> contracts | |
| vendor_id | UUID | NULLABLE, FK -> vendors | |
| tenant_id | UUID | NOT NULL | |
| severity | risk_severity | NOT NULL | |
| title | TEXT | NOT NULL | |
| description | TEXT | NOT NULL | |
| clause_reference | TEXT | NULLABLE | |
| recommendation | TEXT | NULLABLE | |
| status | TEXT | NOT NULL, DEFAULT 'open' | open, in_remediation, resolved, waived |
| ai_confidence | REAL | NULLABLE, CHECK 0-1 | |
| detected_by | TEXT | NOT NULL | ai_scan, manual_audit, external |
| detected_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| resolved_at | TIMESTAMPTZ | NULLABLE | |
| resolved_by | TEXT | NULLABLE, FK -> users | |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | |

**Indexes:** `idx_compliance_findings_req`, `idx_compliance_findings_contract`, `idx_compliance_findings_status`, `idx_compliance_findings_severity`

---

#### Entity: `obligations`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| obligation_id | UUID | PK | |
| contract_id | UUID | NOT NULL, FK -> contracts | |
| clause_id | UUID | NULLABLE, FK -> clauses | |
| tenant_id | UUID | NOT NULL | |
| title | TEXT | NOT NULL | |
| description | TEXT | NOT NULL | |
| obligation_type | TEXT | NOT NULL | deliverable, payment, reporting, compliance, notice |
| assignee | TEXT | NULLABLE, FK -> users | |
| status | TEXT | NOT NULL, DEFAULT 'pending' | pending, in_progress, completed, overdue, waived |
| due_date | DATE | NULLABLE | |
| reminder_days | INTEGER | NULLABLE | Days before due to remind |
| completed_at | TIMESTAMPTZ | NULLABLE | |
| ai_confidence | REAL | NULLABLE, CHECK 0-1 | |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_obligations_contract`, `idx_obligations_assignee`, `idx_obligations_status`, `idx_obligations_due`

---

#### Entity: `remediations`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| remediation_id | UUID | PK | |
| finding_id | UUID | NOT NULL, FK -> compliance_findings | |
| tenant_id | UUID | NOT NULL | |
| action | TEXT | NOT NULL | Remediation action description |
| assigned_to | TEXT | NULLABLE, FK -> users | |
| status | TEXT | NOT NULL, DEFAULT 'open' | open, in_progress, completed, verified |
| due_date | DATE | NULLABLE | |
| completed_at | TIMESTAMPTZ | NULLABLE | |
| evidence | JSONB | DEFAULT '[]' | Evidence documents/links |
| notes | TEXT | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

---

### 2.8 Analytics & Reporting Context

---

#### Entity: `analytics_snapshots`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| snapshot_id | UUID | PK | |
| tenant_id | UUID | NOT NULL, FK -> tenants | |
| snapshot_type | TEXT | NOT NULL | daily, weekly, monthly, quarterly |
| period_start | DATE | NOT NULL | |
| period_end | DATE | NOT NULL | |
| metrics | JSONB | NOT NULL | Aggregated KPI values |
| dimensions | JSONB | NOT NULL, DEFAULT '{}' | Breakdown dimensions |
| generated_by | TEXT | NOT NULL, DEFAULT 'system' | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_analytics_snapshots_tenant`, `idx_analytics_snapshots_period`, `idx_analytics_snapshots_type`
**Partitioning:** BY RANGE (period_start)

---

#### Entity: `kpi_definitions`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| kpi_id | UUID | PK | |
| tenant_id | UUID | NOT NULL, FK -> tenants | |
| code | TEXT | NOT NULL | Machine-readable code |
| name | TEXT | NOT NULL | Display name |
| description | TEXT | NULLABLE | |
| category | TEXT | NOT NULL | risk, spend, compliance, operations, ai |
| formula | TEXT | NOT NULL | SQL or expression for calculation |
| unit | TEXT | NOT NULL | count, percentage, currency, days |
| target_value | REAL | NULLABLE | Target/goal |
| warning_threshold | REAL | NULLABLE | Warning trigger |
| critical_threshold | REAL | NULLABLE | Critical trigger |
| is_active | BOOLEAN | DEFAULT TRUE | |
| refresh_interval | TEXT | DEFAULT 'daily' | realtime, hourly, daily, weekly |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

---

#### Entity: `forecasts`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| forecast_id | UUID | PK | |
| tenant_id | UUID | NOT NULL | |
| metric_code | TEXT | NOT NULL, FK -> kpi_definitions | |
| forecast_date | DATE | NOT NULL | Date of forecast |
| predicted_value | REAL | NOT NULL | |
| lower_bound | REAL | NULLABLE | Confidence interval lower |
| upper_bound | REAL | NULLABLE | Confidence interval upper |
| confidence | REAL | NULLABLE, CHECK 0-1 | |
| model_id | TEXT | NULLABLE | Forecasting model used |
| features | JSONB | DEFAULT '{}' | Input features |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_forecasts_metric`, `idx_forecasts_date`

---

### 2.9 Ingestion & OCR Context

---

#### Entity: `ingestion_jobs`

**Current Schema (already exists):**
```sql
CREATE TABLE ingestion_jobs (
    job_id           UUID PRIMARY KEY,
    document_id      UUID NOT NULL,
    tenant_id        UUID NOT NULL,
    user_id          TEXT NOT NULL,
    filename         TEXT NOT NULL,
    content_type     TEXT NOT NULL,
    status           job_status NOT NULL DEFAULT 'PENDING',
    progress         REAL NOT NULL DEFAULT 0.0,
    error_message    TEXT,
    retry_count      INTEGER NOT NULL DEFAULT 0,
    extraction_results JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ,
    FOREIGN KEY (tenant_id, document_id) REFERENCES contracts(tenant_id, contract_id)
);
```

**Proposed Extensions:**
| Additional Attribute | Type | Constraints | Description |
|---------------------|------|-------------|-------------|
| pipeline_version | TEXT | NULLABLE | Ingestion pipeline version |
| ocr_method | extraction_method | NULLABLE | OCR engine used |
| total_chunks_expected | INTEGER | NULLABLE | For progress tracking |
| total_chunks_processed | INTEGER | NULLABLE | |

---

#### Entity: `extracted_pages`

**Current Schema (already exists):**
```sql
CREATE TABLE extracted_pages (
    page_id        UUID PRIMARY KEY,
    contract_id    UUID NOT NULL,
    tenant_id      UUID NOT NULL,
    page_number    INTEGER NOT NULL CHECK (page_number >= 1),
    text           TEXT NOT NULL,
    method         extraction_method NOT NULL,
    confidence     REAL NOT NULL DEFAULT 1.0,
    metadata       JSONB NOT NULL DEFAULT '{}',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(contract_id, page_number)
);
```

---

#### Entity: `extraction_results`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| result_id | UUID | PK | |
| job_id | UUID | NOT NULL, FK -> ingestion_jobs | |
| tenant_id | UUID | NOT NULL | |
| extraction_type | TEXT | NOT NULL | metadata, clauses, parties, dates, values |
| raw_output | JSONB | NOT NULL | Extracted data |
| confidence | REAL | NOT NULL, CHECK 0-1 | |
| validation_status | TEXT | DEFAULT 'pending' | pending, validated, rejected |
| validated_by | TEXT | NULLABLE, FK -> users | |
| validated_at | TIMESTAMPTZ | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_extraction_results_job`, `idx_extraction_results_type`

---

### 2.10 Search & Discovery Context

---

#### Entity: `search_index`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| index_id | UUID | PK | |
| tenant_id | UUID | NOT NULL | |
| entity_type | TEXT | NOT NULL | contract, clause, vendor, obligation, finding |
| entity_id | TEXT | NOT NULL | |
| content | TEXT | NOT NULL | Searchable text |
| embedding | vector(1536) | NULLABLE | For semantic search |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | Faceted metadata |
| is_active | BOOLEAN | DEFAULT TRUE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_search_index_tenant`, `idx_search_index_entity`, `idx_search_index_embedding` (ivfflat), GIN(metadata)

---

#### Entity: `saved_searches`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| saved_search_id | UUID | PK | |
| tenant_id | UUID | NOT NULL | |
| user_id | TEXT | NOT NULL, FK -> users | |
| name | TEXT | NOT NULL | Search name |
| query | TEXT | NOT NULL | Search query text |
| filters | JSONB | NOT NULL, DEFAULT '{}' | Applied filters |
| scope | TEXT | NOT NULL, DEFAULT 'global' | global, contracts, vendors, clauses |
| is_shared | BOOLEAN | DEFAULT FALSE | |
| alert_enabled | BOOLEAN | DEFAULT FALSE | Email alert on new results |
| last_run_at | TIMESTAMPTZ | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_saved_searches_user`, `idx_saved_searches_tenant`

---

### 2.11 Notification & Collaboration Context

---

#### Entity: `notifications`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| notification_id | UUID | PK | |
| tenant_id | UUID | NOT NULL | |
| user_id | TEXT | NOT NULL, FK -> users | Recipient |
| type | TEXT | NOT NULL | alert, task, escalation, ai_insight, workflow, approval |
| title | TEXT | NOT NULL | |
| body | TEXT | NULLABLE | |
| severity | risk_severity | NOT NULL, DEFAULT 'info' | |
| entity_type | TEXT | NULLABLE | Related entity type |
| entity_id | TEXT | NULLABLE | Related entity ID |
| action_url | TEXT | NULLABLE | Deep link |
| is_read | BOOLEAN | DEFAULT FALSE | |
| read_at | TIMESTAMPTZ | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_notifications_user`, `idx_notifications_read`, `idx_notifications_created`, `idx_notifications_type`

---

#### Entity: `comments`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| comment_id | UUID | PK | |
| tenant_id | UUID | NOT NULL | |
| entity_type | TEXT | NOT NULL | contract, clause, vendor, workflow, finding |
| entity_id | TEXT | NOT NULL | |
| parent_comment_id | UUID | NULLABLE, FK -> comments | Threaded replies |
| author_id | TEXT | NOT NULL, FK -> users | |
| body | TEXT | NOT NULL | |
| mentions | TEXT[] | DEFAULT '{}' | @mentioned user IDs |
| is_resolved | BOOLEAN | DEFAULT FALSE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| deleted_at | TIMESTAMPTZ | NULLABLE | |

**Indexes:** `idx_comments_entity`, `idx_comments_author`, `idx_comments_parent`

---

#### Entity: `activity_feed`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| activity_id | UUID | PK | |
| tenant_id | UUID | NOT NULL | |
| user_id | TEXT | NOT NULL, FK -> users | Actor |
| activity_type | TEXT | NOT NULL | created, updated, approved, rejected, commented, escalated, ai_analyzed |
| entity_type | TEXT | NOT NULL | |
| entity_id | TEXT | NOT NULL | |
| summary | TEXT | NOT NULL | Human-readable summary |
| metadata | JSONB | DEFAULT '{}' | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `idx_activity_feed_tenant`, `idx_activity_feed_entity`, `idx_activity_feed_created`

---

#### Entity: `webhook_registrations`

**Current Schema (already exists):**
```sql
CREATE TABLE webhook_registrations (
    webhook_id    UUID PRIMARY KEY,
    tenant_id     UUID NOT NULL,
    user_id       TEXT NOT NULL,
    url           TEXT NOT NULL,
    events        TEXT[] NOT NULL DEFAULT '{ingestion.completed,ingestion.failed}',
    secret_hash   TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    description   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### 2.12 Audit Context

---

#### Entity: `audit_logs`

**Current Schema (already exists):**
```sql
CREATE TABLE audit_logs (
    audit_id      UUID NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id     UUID NOT NULL,
    user_id       TEXT NOT NULL,
    action        TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id   TEXT NOT NULL,
    ip_address    TEXT,
    details       JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);
```

**Proposed Extensions:**
| Additional Attribute | Type | Constraints | Description |
|---------------------|------|-------------|-------------|
| user_agent | TEXT | NULLABLE | Client user agent |
| session_id | TEXT | NULLABLE | Session identifier |
| correlation_id | TEXT | NULLABLE | Distributed tracing ID |

---

## 3. Contract Domain Architecture

### 3.1 Contract Lifecycle State Machine

```
                         +-----------+
                         | UPLOADED  |
                         +-----+-----+
                               |
                               v
                         +-----------+
                  +------>| PENDING   |<------+
                  |       +-----+-----+       |
                  |             |             |
                  |             v             |
                  |       +-----------+       |
                  |       |PROCESSING |       |
                  |       +-----+-----+       |
                  |            |    |         |
                  |     +------+    +------+  |
                  |     |                  |  |
                  |     v                  v  |
                  |  +-------+        +-----+-+---+
                  |  | ERROR  |       |   READY    |
                  |  +-------+        +-----+------+
                  |                         |
                  |                    +----+----+
                  |                    |         |
                  |                    v         v
                  |            +----------+  +--------+
                  |            |UNDER     |  |ARCHIVED|
                  |            |REVIEW    |  +--------+
                  |            +----+-----+
                  |                 |
                  |            +----+----+
                  |            |         |
                  |            v         v
                  |     +----------+ +----------+
                  |     | APPROVED | | REJECTED |
                  |     +----+-----+ +----------+
                  |          |
                  |          v
                  |     +----------+
                  +-----| AMENDED  |  (new version)
                        +----------+
```

**State Transition Rules:**
- `UPLOADED -> PENDING`: Automatic on file receipt
- `PENDING -> PROCESSING`: When ingestion pipeline picks up
- `PROCESSING -> READY`: When OCR, clause extraction, and AI analysis complete
- `PROCESSING -> ERROR`: On unrecoverable failure
- `READY -> UNDER_REVIEW`: When assigned to reviewer
- `UNDER_REVIEW -> APPROVED`: On approval action
- `UNDER_REVIEW -> REJECTED`: On rejection action
- `APPROVED -> AMENDED`: When a new version is uploaded
- `READY|APPROVED -> ARCHIVED`: On archival action

### 3.2 Contract Hierarchy

```
Master Agreement (MSA)
    |
    +-- Statement of Work #1 (SOW)
    |       +-- Amendment #1 to SOW #1
    |
    +-- Statement of Work #2 (SOW)
    |
    +-- Data Processing Addendum (DPA)
    |
    +-- Amendment #1 to MSA

Relationship Types: parent, child, amendment, addendum, dpa
```

### 3.3 Version Management

```
Contract v1 (original)
    |
    +-- Contract v2 (amended)
    |       |
    |       +-- Contract v3 (amended)
    |
    +-- Redline Comparison: v1 <-> v2
    +-- AI Analysis: v1
    +-- AI Analysis: v2
```

**Version Rules:**
- Each version is a full snapshot (not a diff)
- Clauses, chunks, and extracted pages are version-specific
- Risk reports are tied to a specific version
- Redline comparisons can be between any two versions
- AI analyses are version-specific

---

## 4. Clause & Playbook Domain

### 4.1 Clause Taxonomy

```
CLAUSE TYPES
├── Financial
│   ├── Payment Terms
│   ├── Pricing
│   ├── Fee Structure
│   └── Late Payment
├── Liability
│   ├── Indemnification
│   ├── Limitation of Liability
│   ├── Cap on Damages
│   └── Exclusion of Damages
├── Term & Termination
│   ├── Term
│   ├── Termination for Cause
│   ├── Termination for Convenience
│   └── Survival
├── Intellectual Property
│   ├── IP Ownership
│   ├── License Grants
│   └── IP Indemnification
├── Data & Privacy
│   ├── Data Protection
│   ├── DPA
│   ├── Security Measures
│   └── Data Retention
├── Compliance
│   ├── Regulatory Compliance
│   ├── Audit Rights
│   ├── Insurance
│   └── Export Control
├── Operational
│   ├── SLA
│   ├── Support
│   ├── Maintenance
│   └── Training
├── General
│   ├── Force Majeure
│   ├── Assignment
│   ├── Governing Law
│   ├── Dispute Resolution
│   ├── Confidentiality
│   └── Entire Agreement
```

### 4.2 Clause Variant Relationships

```
Playbook Entry (preferred)
    |
    +-- Fallback Variant (acceptable compromise)
    +-- AI-Suggested Variant (generated)
    +-- Rejected Variant (historical)
    +-- Negotiated Variant (agreed with counterparty)
```

### 4.3 Benchmark Relationships

```
Clause
    |
    +-- Benchmark Percentile (market comparison)
    +-- Similar Clauses (semantic similarity via embeddings)
    +-- Industry Standard (aggregated from corpus)
    +-- Risk Distribution (histogram of risk scores)
```

---

## 5. Workflow & Approval Domain

### 5.1 Workflow Engine Schema

```
workflows
    |
    +-- workflow_steps (ordered)
    |       |
    |       +-- approvals (per step)
    |       +-- escalations (per workflow)
    |
    +-- sla_metrics (per workflow)
    +-- activity_feed (per workflow)
```

### 5.2 Workflow Types & State Machines

**Legal Review Workflow:**
```
PENDING -> ASSIGNED -> IN_REVIEW -> APPROVED/REJECTED
                           |
                           v
                      ESCALATED -> SENIOR_REVIEW -> APPROVED/REJECTED
```

**Procurement Approval Workflow:**
```
DRAFT -> SUBMITTED -> PROCUREMENT_REVIEW -> FINANCIAL_REVIEW -> LEGAL_REVIEW -> APPROVED
                                                                    |
                                                                    v
                                                               REJECTED
```

**Compliance Remediation Workflow:**
```
OPEN -> INVESTIGATING -> REMEDIATING -> VERIFYING -> CLOSED
                                         |
                                         v
                                    REOPENED
```

### 5.3 Approval Chain Architecture

```
Single Approval:  One approver, one step
Sequential:       Step 1 -> Step 2 -> Step 3
Parallel:         Step 1 (multiple approvers, all required)
Orchestral:       Parallel groups with sequential phases
Conditional:      If value > $X, add CFO approval step
```

### 5.4 SLA Tracking

```
sla_metrics
    |
    +-- per-workflow SLA (deadline tracking)
    +-- per-step SLA (step-level deadlines)
    +-- per-vendor SLA (contractual obligations)
    +-- per-tenant SLA (platform commitments)

SLA States:
    ON_TRACK -> AT_RISK -> BREACHED
```

---

## 6. AI & Vector Architecture

### 6.1 RAG Pipeline Architecture

```
                    +-----------+
                    |  Document |
                    +-----+-----+
                          |
                          v
                    +-----------+
                    |  Chunking |
                    | (semantic)|-----+
                    +-----------+     |
                          |          |
                    +-----------+    |
                    | Embedding |    |
                    |  (vector) |    |
                    +-----------+    |
                          |          |
                    +-----------+    |
                    | pgvector  |    |
                    |  INDEX    |    |
                    +-----------+    |
                          |          |
                    +-----------+    |
              +----->|   RAG    |<---+
              |     | Retrieval|
              |     +-----+----+
              |           |
              |     +-----v----+
              |     |   LLM    |
              |     |  Prompt  |
              |     +-----+----+
              |           |
              |     +-----v----+
              |     |  Output  |
              |     | +Citation|
              |     +-----+----+
              |           |
              +-----------+
           (feedback loop)
```

### 6.2 Embedding Architecture

```
chunks table:
    chunk_id        UUID
    contract_id     UUID
    tenant_id       UUID
    text            TEXT            -- chunk content
    token_count     INTEGER         -- token count
    embedding       vector(1536)    -- OpenAI ada-002 / text-embedding-3-large
    clause_ids      UUID[]          -- associated clauses
    page_numbers    INTEGER[]       -- source pages
    metadata        JSONB           -- chunking metadata
    chunking_strategy TEXT          -- semantic, fixed, sentence

Index: ivfflat (embedding vector_cosine_ops) WITH (lists = 100)

Query: SELECT text, 1 - (embedding <=> :query_vector) AS similarity
       FROM chunks
       WHERE tenant_id = :tenant_id
       ORDER BY embedding <=> :query_vector
       LIMIT 20
```

### 6.3 AI Explainability Architecture

```
ai_analyses
    +-- analysis_id (immutable)
    +-- model_id, model_version
    +-- confidence (overall)
    +-- latency_ms, token_count, cost_usd
    +-- prompt_id -> ai_prompts (exact prompt used)
    +-- output_id -> ai_outputs (exact output)
        +-- content (structured JSON)
        +-- raw_text (model response)
        +-- citations[] -> citations
            +-- chunk_id -> chunks (source text)
            +-- excerpt (exact citation)
            +-- relevance (score)
        +-- reasoning (chain-of-thought)
```

### 6.4 Chunking Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **Semantic** | Split at natural boundaries (paragraphs, sections) | Default, best for RAG |
| **Fixed-size** | Fixed token count with overlap | High-volume processing |
| **Sentence** | Sentence-level chunks | Fine-grained retrieval |
| **Clause-aware** | Respects clause boundaries | Legal review accuracy |
| **Hierarchical** | Parent/child chunk relationships | Summarization + detail |

---

## 7. Search & Discovery Domain

### 7.1 Search Architecture

```
                    +------------------+
                    |   Search Query   |
                    +--------+---------+
                             |
               +-------------+-------------+
               |             |             |
               v             v             v
        +----------+   +----------+   +----------+
        | Full-Text|   | Semantic |   | Faceted  |
        | (tsvector)|   | (vector) |   | (JSONB)  |
        +-----+----+   +-----+----+   +-----+----+
              |              |              |
              +------+------+              |
                     |                     |
               +-----v-----+              |
               |   Hybrid  |              |
               |   Ranker  |              |
               +-----+-----+              |
                     |                    |
                     v                    v
               +----------+        +----------+
               | Results  |        | Filters  |
               | (ranked) |        | (facets) |
               +----------+        +----------+
```

### 7.2 Search Index Strategy

```
search_index table:
    index_id        UUID
    tenant_id       UUID
    entity_type     TEXT    -- contract, clause, vendor, obligation, finding
    entity_id       TEXT
    content         TEXT    -- normalized searchable text
    embedding       vector(1536)
    metadata        JSONB   -- faceted metadata (tags, type, status, dates)

Full-Text: GIN index on to_tsvector('english', content)
Semantic:  ivfflat on embedding
Faceted:   GIN on metadata (jsonb_path_ops)
```

### 7.3 OCR Indexing Pipeline

```
Upload -> S3 -> Ingestion Job -> OCR (Textract/Tika) -> Extracted Pages
    -> Clause Extraction -> Chunking -> Embedding -> Search Index
```

---

## 8. Compliance Domain

### 8.1 Regulation Mapping

```
compliance_requirements (GDPR, CCPA, SOX, HIPAA, etc.)
    |
    +-- compliance_findings (per contract/vendor)
    |       |
    |       +-- remediations (action items)
    |
    +-- obligations (derived from requirements)
    |
    +-- vendor_risks (vendor-level compliance)
```

### 8.2 Compliance Scoring Model

```
Compliance Score = weighted_average of:
    - Regulation Coverage (requirements mapped to contracts)
    - Finding Resolution Rate (open vs resolved)
    - Remediation Velocity (avg time to close)
    - Vendor Compliance Rate (compliant vendors / total)
    - Policy Adherence (active policies vs required)
```

---

## 9. Procurement & Vendor Domain

### 9.1 Vendor Hierarchy

```
Vendor (Legal Entity)
    |
    +-- Subsidiaries
    +-- Divisions
    +-- Parent Company
    +-- Affiliates
```

### 9.2 Spend Analytics Schema

```
spend_records
    vendor_id -> vendors
    contract_id -> contracts (optional)
    fiscal_year, fiscal_quarter
    amount, currency, category, department

Aggregations:
    Total Spend by Vendor
    Spend by Category (Cloud, Software, Consulting, etc.)
    Spend by Department (Cost Center)
    Spend Trend (Monthly/Quarterly/Yearly)
    Concentration (Top N vendors % of total)
```

### 9.3 Vendor Risk Scoring

```
Vendor Risk Score = weighted combination:
    - Financial Stability (25%)
    - Compliance Status (20%)
    - SLA Performance (15%)
    - Geopolitical Risk (10%)
    - Security Posture (10%)
    - Concentration Risk (10%)
    - Contractual Risk (10%)
```

---

## 10. Analytics & Reporting Domain

### 10.1 KPI Aggregation Strategy

```
analytics_snapshots (materialized aggregates)
    snapshot_type: daily, weekly, monthly, quarterly
    period_start, period_end
    metrics: JSONB of all KPI values
    dimensions: breakdown by category, department, geography

Refresh Strategies:
    Realtime: Direct query (small datasets)
    Hourly: Materialized view refresh
    Daily: Batch aggregation job
    Weekly: Executive summary generation
```

### 10.2 Time-Series Storage

```
analytics_snapshots partitioned by RANGE (period_start)
    - Daily snapshots retained for 90 days
    - Weekly snapshots retained for 12 months
    - Monthly snapshots retained for 3 years
    - Quarterly snapshots retained indefinitely
```

---

## 11. Multi-Tenant Architecture

### 11.1 Tenant Isolation Strategy

```
Isolation Level: Row-Level Security (RLS) on all tenant-scoped tables

Strategy: Shared database, isolated rows
    - All tables have tenant_id column
    - RLS policies enforce tenant isolation
    - Contracts partitioned by HASH(tenant_id)
    - Audit logs partitioned by RANGE(created_at)

Shared Resources:
    - Application server (stateless)
    - Database (with RLS)
    - Redis cache (tenant-prefixed keys)
    - S3 buckets (tenant-prefixed paths)

Isolated Per Tenant:
    - Encryption keys (KMS)
    - Feature flags
    - Configuration/settings
    - Custom playbooks
    - User roles and permissions
```

### 11.2 Tenant-Aware Indexing

```
All indexes include tenant_id as leading column:
    idx_contracts_tenant_status ON contracts(tenant_id, status)
    idx_vendors_tenant_category ON vendors(tenant_id, category)

Vector search includes tenant_id filter:
    WHERE tenant_id = :tenant_id
    ORDER BY embedding <=> :query_vector
```

---

## 12. RBAC & Security Domain

### 12.1 Hierarchical RBAC Model

```
Tenant-level Roles:
    admin       - Full access within tenant
    analyst     - Read/write on operational modules
    viewer      - Read-only access
    api         - Programmatic access (rate-limited)

Team-level Roles:
    team_lead   - Manage team members and workflows
    team_member - Standard team access

Custom Roles (tenant-defined):
    legal_reviewer  - Legal Ops modules
    procurement_mgr - Procurement modules
    compliance_officer - Compliance modules
    vendor_manager  - Vendor modules
```

### 12.2 Permission Model

```
Permission Format: resource:action[:scope]

Examples:
    contract:read:tenant     - Read any contract in tenant
    contract:create:own      - Create contracts
    contract:approve:tenant  - Approve contracts
    vendor:read:tenant       - Read any vendor
    workflow:manage:team     - Manage team workflows
    admin:users:tenant       - Manage users
    admin:settings:tenant    - Manage tenant settings

Permission Groups (roles):
    admin:      [all permissions]
    analyst:    [contract:*, vendor:*, workflow:*, clause:*]
    viewer:     [contract:read, vendor:read, clause:read]
```

### 12.3 Contextual Access Control

```
Access decisions consider:
    1. User role (admin, analyst, viewer)
    2. Team membership (team-scoped permissions)
    3. Entity ownership (own records)
    4. Workflow assignment (assigned tasks)
    5. AI context (AI-recommended actions)
```

---

## 13. Event-Driven Architecture

### 13.1 Domain Events

```
Contract Events:
    contract.uploaded        { contract_id, tenant_id, filename, file_size }
    contract.processed       { contract_id, status, pages, clauses }
    contract.analyzed        { contract_id, analysis_id, risk_score }
    contract.approved        { contract_id, approved_by, timestamp }
    contract.rejected        { contract_id, rejected_by, reason }
    contract.archived        { contract_id, archived_by }
    contract.version.created { contract_id, version_number, change_notes }

Ingestion Events:
    ingestion.started        { job_id, document_id, filename }
    ingestion.progress       { job_id, progress, stage }
    ingestion.completed      { job_id, document_id, pages, chunks }
    ingestion.failed         { job_id, error_message, retry_count }

AI Events:
    ai.analysis.started      { analysis_id, contract_id, analysis_type }
    ai.analysis.completed    { analysis_id, confidence, findings_count }
    ai.analysis.failed       { analysis_id, error }
    ai.finding.created       { finding_id, severity, category, contract_id }
    ai.insight.generated     { insight_id, type, confidence, entities[] }

Workflow Events:
    workflow.created         { workflow_id, type, entity_type, entity_id }
    workflow.assigned        { workflow_id, assigned_to }
    workflow.step.completed  { step_id, workflow_id, status }
    workflow.escalated       { workflow_id, level, escalated_to, reason }
    workflow.completed       { workflow_id, status, completed_by }
    workflow.sla.breached    { workflow_id, sla_metric, deadline }

Vendor Events:
    vendor.risk.updated      { vendor_id, risk_score, risk_level }
    vendor.sla.breached      { vendor_id, contract_id, metric, value }
    vendor.contract.created  { vendor_id, contract_id }
    vendor.onboarding.started { vendor_id, workflow_id }

Compliance Events:
    compliance.finding.created  { finding_id, severity, regulation }
    compliance.finding.resolved { finding_id, resolved_by }
    compliance.obligation.due   { obligation_id, contract_id, due_date }

Notification Events:
    notification.sent        { notification_id, user_id, type, title }
    notification.batch.sent  { notification_ids[], type, count }

Audit Events:
    audit.log.written        { audit_id, tenant_id, action, resource }
```

### 13.2 Event Bus Architecture

```
                    +-------------------+
                    |   Event Bus       |
                    | (Redis Pub/Sub +  |
                    |  RabbitMQ/NSQ)    |
                    +--------+----------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
        +----------+  +----------+  +----------+
        | Async    |  | Webhook  |  | Audit    |
        | Workers  |  | Dispatch |  | Logger   |
        +----------+  +----------+  +----------+
              |              |              |
              v              v              v
        +----------+  +----------+  +----------+
        | Queue    |  | HTTP     |  | Audit    |
        | (Redis)  |  | Outbound |  | Logs     |
        +----------+  +----------+  +----------+
```

### 13.3 Event Payload Standards

```json
{
    "event_id": "evt_abc123",
    "event_type": "contract.analyzed",
    "event_version": "1.0",
    "source": "ai-analysis-service",
    "tenant_id": "tenant_uuid",
    "timestamp": "2026-05-15T10:30:00Z",
    "correlation_id": "corr_xyz789",
    "actor_id": "user_123",
    "data": {
        "contract_id": "contract_uuid",
        "analysis_id": "analysis_uuid",
        "risk_score": 0.72,
        "findings_count": 5
    }
}
```

---

## 14. Database Optimization Strategy

### 14.1 Indexing Strategy

| Table | Index Type | Columns | Purpose |
|-------|-----------|---------|---------|
| contracts | BTREE | (tenant_id, status) | Tenant-scoped status queries |
| contracts | BTREE | (tenant_id, created_at DESC) | Recent contracts listing |
| contracts | GIN | tags | Tag-based filtering |
| contracts | GIN | search_vector | Full-text search |
| contracts | BTREE | (tenant_id, contract_type) | Type-based filtering |
| chunks | ivfflat | embedding | Semantic search |
| chunks | BTREE | (tenant_id, contract_id) | Contract chunks |
| clauses | BTREE | (tenant_id, contract_id, clause_index) | Ordered clause retrieval |
| clauses | BTREE | clause_type | Type-based filtering |
| audit_logs | BTREE | (tenant_id, created_at DESC) | Audit trail queries |
| audit_logs | BTREE | (resource_type, resource_id) | Resource audit |
| vendors | BTREE | (tenant_id, risk_score DESC) | High-risk vendor queries |
| workflows | BTREE | (tenant_id, status, sla_deadline) | SLA monitoring |
| notifications | BTREE | (tenant_id, user_id, is_read, created_at) | User notification feed |
| activity_feed | BTREE | (tenant_id, entity_type, entity_id) | Entity activity stream |

### 14.2 Partitioning Strategy

| Table | Partition Key | Partitions | Retention |
|-------|--------------|------------|-----------|
| contracts | HASH(tenant_id) | 4-16 (scale with tenants) | Permanent |
| audit_logs | RANGE(created_at) | Monthly | 7 years |
| analytics_snapshots | RANGE(period_start) | Monthly | Daily: 90d, Weekly: 1yr, Monthly: 3yr, Quarterly: permanent |
| chunks | HASH(tenant_id) | 4-16 | Permanent |
| activity_feed | RANGE(created_at) | Monthly | 1 year |

### 14.3 Caching Strategy

| Cache Layer | Technology | Data | TTL | Invalidation |
|-------------|-----------|------|-----|-------------|
| L1 (App) | In-memory | User session, permissions | 5 min | On role change |
| L2 (Redis) | Redis | KPI aggregates, search results, AI context | 15 min | On data mutation |
| L3 (DB) | PostgreSQL | Materialized views | Configurable | Refresh job |
| CDN | CloudFront | Static assets, exported reports | 1 hour | Cache invalidation API |

### 14.4 Query Optimization Patterns

```
1. Tenant-scoped queries always include tenant_id filter
2. Pagination uses keyset pagination (WHERE created_at < :cursor) for large datasets
3. JSONB queries use jsonb_path_ops GIN index
4. Vector queries include tenant_id filter before ORDER BY
5. Time-series queries use partition pruning
6. Full-text search combines with semantic search via hybrid ranker
```

### 14.5 Archival Strategy

```
Active Data (hot):    Current contracts, active workflows, open findings
                      -> Primary tables with partitioning

Warm Data:            Contracts > 1yr old, completed workflows
                      -> Same tables, compressed with pg_repack

Cold Data:            Contracts > 3yr old, audit logs > 1yr
                      -> Partition detached, stored as Parquet in S3

Archive:              Contracts > 7yr old, audit logs > 7yr
                      -> Glacier storage, metadata only in DB
```

---

## 15. Master Entity Relationship Map

```
+====================================================================+
|                    MASTER ENTITY RELATIONSHIP MAP                    |
+====================================================================+

TENANTS (root)
    |
    +-- USERS (N:1)
    |       +-- ROLES (N:M via team_members)
    |       +-- TEAMS (N:M via team_members)
    |
    +-- CONTRACTS (N:1, partitioned by HASH)
    |       +-- CONTRACT_VERSIONS (1:N)
    |       +-- CONTRACT_RELATIONSHIPS (N:M self-referencing)
    |       +-- CLAUSES (1:N)
    |       |       +-- CLAUSE_VARIANTS (1:N)
    |       |       +-- PLAYBOOK_ENTRIES (N:1)
    |       +-- CHUNKS (1:N, with vector embeddings)
    |       +-- EXTRACTED_PAGES (1:N)
    |       +-- RISK_REPORTS (1:N)
    |       |       +-- RISK_FINDINGS (1:N)
    |       +-- AI_ANALYSES (1:N)
    |       |       +-- AI_PROMPTS (N:1)
    |       |       +-- AI_OUTPUTS (1:N)
    |       |               +-- CITATIONS (1:N)
    |       +-- OBLIGATIONS (1:N)
    |       +-- NEGOTIATIONS (1:N)
    |       |       +-- REDLINES (1:N)
    |       +-- RENEWALS (1:N)
    |       +-- WORKFLOWS (1:N)
    |       +-- COMPLIANCE_FINDINGS (N:1)
    |       +-- SPEND_RECORDS (1:N)
    |
    +-- VENDORS (N:1)
    |       +-- VENDOR_RISKS (1:N)
    |       +-- SPEND_RECORDS (1:N)
    |       +-- PROCUREMENT_WORKFLOWS (1:N)
    |       +-- SLA_METRICS (1:N)
    |       +-- COMPLIANCE_FINDINGS (N:1)
    |
    +-- WORKFLOWS (N:1)
    |       +-- WORKFLOW_STEPS (1:N)
    |       |       +-- APPROVALS (1:N)
    |       +-- ESCALATIONS (1:N)
    |       +-- SLA_METRICS (1:N)
    |
    +-- COMPLIANCE_REQUIREMENTS (N:1)
    |       +-- COMPLIANCE_FINDINGS (1:N)
    |               +-- REMEDIATIONS (1:N)
    |
    +-- SEARCH_INDEX (N:1, polymorphic entity references)
    +-- SAVED_SEARCHES (N:1)
    +-- NOTIFICATIONS (N:1)
    +-- COMMENTS (N:1, polymorphic entity references)
    +-- ACTIVITY_FEED (N:1, polymorphic entity references)
    +-- AUDIT_LOGS (N:1, partitioned by RANGE)
    +-- ANALYTICS_SNAPSHOTS (N:1, partitioned by RANGE)
    +-- KPI_DEFINITIONS (N:1)
    +-- FORECASTS (N:1)
    +-- PLAYBOOKS (N:1)
    |       +-- PLAYBOOK_ENTRIES (1:N)
    +-- WEBHOOK_REGISTRATIONS (N:1)
    +-- TEAMS (N:1)
```

### 15.1 Entity Count Summary

| Context | Tables | Description |
|---------|--------|-------------|
| Identity & Access | 6 | tenants, users, roles, permissions, teams, team_members |
| Contract Lifecycle | 5 | contracts, contract_versions, contract_relationships, renewals, redline_comparisons |
| AI Intelligence | 6 | ai_analyses, ai_prompts, ai_outputs, chunks, citations, risk_findings |
| Workflow Engine | 5 | workflows, workflow_steps, approvals, escalations, sla_metrics |
| Legal Operations | 5 | clauses, clause_variants, playbooks, playbook_entries, negotiations, redlines |
| Procurement & Vendor | 4 | vendors, vendor_risks, spend_records, procurement_workflows |
| Compliance | 4 | compliance_requirements, compliance_findings, obligations, remediations |
| Analytics & Reporting | 3 | analytics_snapshots, kpi_definitions, forecasts |
| Ingestion & OCR | 3 | ingestion_jobs, extracted_pages, extraction_results |
| Search & Discovery | 2 | search_index, saved_searches |
| Notification & Collaboration | 4 | notifications, comments, activity_feed, webhook_registrations |
| Audit | 1 | audit_logs |

**Total: 48 tables** (including join tables and partitions)

---

## Appendix A: Naming Conventions

```
Tables:          snake_case, plural (contracts, users, audit_logs)
Columns:         snake_case (contract_id, created_at)
Primary Keys:    <table>_id (contract_id, user_id)
Foreign Keys:    <referenced_table>_id (tenant_id, contract_id)
JSONB:           snake_case keys
Enums:           snake_case values ('pending', 'in_progress')
Indexes:         idx_<table>_<columns> (idx_contracts_tenant_status)
Triggers:        trg_<table>_<action> (trg_contracts_updated_at)
Partitions:      <table>_<partition_key> (contracts_p0, audit_logs_2026_05)
```

## Appendix B: Soft Delete Strategy

```
All user-facing entities support soft delete via deleted_at:
    - contracts, vendors, users, teams, playbooks, comments
    - Queries include WHERE deleted_at IS NULL
    - Admin UI can view/restore deleted items
    - Cascade: soft-deleting a tenant soft-deletes all child entities

System entities are hard-deleted or retained:
    - audit_logs: never deleted (retention policy)
    - ai_analyses: never deleted (immutable)
    - ingestion_jobs: retained for 90 days
    - notifications: auto-purged after 90 days
```

## Appendix C: Audit Requirements by Entity

```
All mutations on these entities require audit logging:
    - tenants, users, roles, permissions (IAM changes)
    - contracts, contract_versions (CLM changes)
    - workflows, approvals, escalations (operational changes)
    - compliance_findings, remediations (compliance changes)
    - ai_analyses (AI operations — immutable log)

Audit payload includes:
    - before/after snapshot (for updates)
    - IP address, user agent
    - Correlation ID (for distributed tracing)
    - Reason/justification (for sensitive operations)
```
