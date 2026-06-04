================================================================================
  SPRINT RC1-HARDENING — Production Readiness Sprint
  Estimated: 2 days (10 story points)
  Date: June 3, 2026
================================================================================

  RATIONALE: Before building AI Routing, spend 1-2 days hardening the
  platform for pilot customers. The RC1 review identified 15 action items
  across security, reliability, and operations. Fixing these now prevents
  the "demo works, pilot fails" scenario.

================================================================================
PHASE 1 — SECURITY HARDENING (4 SP)
================================================================================

  TASK 1.1: Production JWT Secret (0.5 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Files: backend/.env.example, backend/app/config.py

  Description:
    Remove the hardcoded dev JWT secret from config.py. Require it to be
    set via environment variable JWT_SECRET. Fail startup with clear error
    if not set in production.

  Acceptance:
    - JWT_SECRET must be set via environment variable
    - Dev default removed from code
    - Startup logs warning if using default in production
    - Production startup fails if JWT_SECRET is "dev-local-jwt-secret-..."

  ─────────────────────────────────────────────────────────────────────────────

  TASK 1.2: CORS Restriction (0.5 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Files: backend/app/main.py

  Description:
    Restrict CORS allowed origins to approved domains instead of allowing
    all origins. Read allowed origins from CORS_ALLOWED_ORIGINS env var.

  Acceptance:
    - CORS_ALLOWED_ORIGINS env var controls allowed origins
    - Default to http://localhost:3000 for development
    - Production domains must be explicitly listed
    - Non-listed origins receive proper CORS error

  ─────────────────────────────────────────────────────────────────────────────

  TASK 1.3: RBAC Audit for Admin Endpoints (1 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Files: backend/app/domains/admin/router.py, backend/app/kernel/security/

  Description:
    Audit all admin endpoints to ensure proper permission requirements.
    Verify that sensitive operations (user creation, role modification,
    tenant settings) require ADMIN_TENANT or ADMIN_SYSTEM permissions.

  Acceptance:
    - All admin endpoints have permission dependencies
    - User management requires ADMIN_TENANT
    - Role management requires ADMIN_TENANT
    - Tenant settings requires ADMIN_TENANT
    - Diagnostics require ADMIN_SYSTEM
    - Audit log requires AUDIT_READ

  ─────────────────────────────────────────────────────────────────────────────

  TASK 1.4: Tenant Isolation Audit (1 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Files: All repository/service files

  Description:
    Audit all repository queries to verify tenant_id filtering. Check that
    every SELECT, UPDATE, DELETE query includes a tenant_id WHERE clause.
    This is a code review, not a code change — document any gaps found.

  Acceptance:
    - All repository queries filtered by tenant_id
    - No cross-tenant data leakage possible
    - Report generated with findings

  ─────────────────────────────────────────────────────────────────────────────

  TASK 1.5: Secrets Management Documentation (1 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Files: docs/releases/production_readiness_review.md, backend/.env.example

  Description:
    Document all required environment variables with descriptions, expected
    values, and whether they're required or optional. Update .env.example
    with complete list.

  Acceptance:
    - Complete env var reference documented
    - Each var has: name, description, required/optional, example value
    - .env.example matches production requirements
    - Sentry DSN, Resend API key, JWT secret, DB URL all documented

================================================================================
PHASE 2 — RELIABILITY VERIFICATION (3 SP)
================================================================================

  TASK 2.1: Celery Worker Recovery Test (1 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Description:
    Kill the Celery worker while tasks are in the queue. Verify:
    - Tasks are re-queued (not lost)
    - Worker reconnects when restarted
    - Tasks complete successfully after recovery
    - No duplicate execution of idempotent tasks

  Acceptance:
    - Worker crash does not lose tasks
    - Worker restart processes queued tasks
    - Email dedup prevents duplicate sends
    - Document recovery procedure

  ─────────────────────────────────────────────────────────────────────────────

  TASK 2.2: Database Restore Test (1 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Description:
    Create a fresh PostgreSQL database. Restore rc_backup.sql into it.
    Verify:
    - All tables restored with correct row counts
    - Foreign key constraints intact
    - alembic current shows correct head
    - API starts and responds correctly against restored DB

  Acceptance:
    - Restore completes without errors
    - Row counts match pre-backup values
    - API functions correctly against restored DB
    - Document restore procedure

  ─────────────────────────────────────────────────────────────────────────────

  TASK 2.3: Email Retry Verification (1 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Description:
    Trigger a notification with an invalid email address. Verify:
    - Email is marked as failed (not lost)
    - Retry count increments
    - Next retry timestamp is set
    - After max_attempts, email is permanently failed
    - Admin dashboard shows failed email count

  Acceptance:
    - Failed emails are retried up to max_attempts
    - Permanent failure after exhausting retries
    - Admin console shows accurate email queue stats
    - No infinite retry loops

================================================================================
PHASE 3 — OPERATIONS DOCUMENTATION (3 SP)
================================================================================

  TASK 3.1: Deployment Guide (1 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Files: docs/deployment.md

  Content:
    - Prerequisites (Python, PostgreSQL, Redis, Node.js versions)
    - Environment variable reference
    - Database setup and migration
    - Backend startup (development + production)
    - Frontend build and deploy
    - Docker Compose setup
    - Reverse proxy configuration (nginx/Caddy example)
    - SSL/TLS setup

  ─────────────────────────────────────────────────────────────────────────────

  TASK 3.2: Backup & Restore Guide (0.5 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Files: docs/operations/backup.md

  Content:
    - Automated backup script example
    - Cron job configuration
    - Backup verification procedure
    - Restore to clean database
    - Restore to existing database (with caution notes)
    - Point-in-time recovery considerations

  ─────────────────────────────────────────────────────────────────────────────

  TASK 3.3: Troubleshooting Guide (1 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Files: docs/operations/troubleshooting.md

  Content:
    - API won't start (DB connection, migration, port conflicts)
    - Celery workers not processing tasks
    - Emails not sending
    - Workflow stuck in "running" state
    - Database connection errors
    - Redis connection errors
    - Slow API responses
    - Migration failures

  ─────────────────────────────────────────────────────────────────────────────

  TASK 3.4: Monitoring Dashboard Setup (0.5 SP)
  ─────────────────────────────────────────────────────────────────────────────
  Files: docs/operations/monitoring.md

  Content:
    - Prometheus metrics available at /metrics
    - Key metrics to monitor (request rate, error rate, latency)
    - Health check endpoint usage
    - Celery queue depth monitoring
    - Email queue monitoring
    - Grafana dashboard JSON example (if applicable)

================================================================================
SPRINT RC1-HARDENING SUMMARY
================================================================================

  ┌────────────────────────────────────────────────────────────────────────────┐
  │ Phase │ Task                                │ SP │ Type                     │
  ├────────────────────────────────────────────────────────────────────────────┤
  │ 1     │ Production JWT Secret                │ 0.5│ Security                │
  │ 1     │ CORS Restriction                     │ 0.5│ Security                │
  │ 1     │ RBAC Audit for Admin Endpoints       │ 1  │ Security                │
  │ 1     │ Tenant Isolation Audit               │ 1  │ Security                │
  │ 1     │ Secrets Management Documentation     │ 1  │ Security                │
  ├────────────────────────────────────────────────────────────────────────────┤
  │ 2     │ Celery Worker Recovery Test          │ 1  │ Reliability             │
  │ 2     │ Database Restore Test                │ 1  │ Reliability             │
  │ 2     │ Email Retry Verification             │ 1  │ Reliability             │
  ├────────────────────────────────────────────────────────────────────────────┤
  │ 3     │ Deployment Guide                     │ 1  │ Operations              │
  │ 3     │ Backup & Restore Guide               │ 0.5│ Operations              │
  │ 3     │ Troubleshooting Guide                │ 1  │ Operations              │
  │ 3     │ Monitoring Dashboard Setup           │ 0.5│ Operations              │
  ├────────────────────────────────────────────────────────────────────────────┤
  │       │ TOTAL                                │ 10 │ 2 days, 1 dev           │
  └────────────────────────────────────────────────────────────────────────────┘

================================================================================
AFTER HARDENING — SPRINT 20
================================================================================

  Priority order for new capabilities:

  1. AI Routing (~8 SP) — Model selection intelligence
  2. AI Quality (~8 SP) — Hallucination detection + aggregation
  3. Relationships (~5 SP) — Contract relationship graph

  Benchmarks deferred until real benchmark data exists.

================================================================================
END OF RC1-HARDENING PLAN
================================================================================
