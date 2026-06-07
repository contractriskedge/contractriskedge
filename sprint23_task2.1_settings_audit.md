================================================================================
  SPRINT 23 TASK 2.1 — Settings Module Audit
  Completed: June 5, 2026
================================================================================

EXECUTIVE SUMMARY
───────────────────────────────────────────────────────────────────────────────

  The Settings module is the least production-ready area of ContractEdge.
  12 settings-related features were audited. Only 2 are fully operational.
  1 critical defect found: the entire tenant_config router is NOT registered.

  Overall settings completion: ~20%

CURRENT ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────

  Frontend:
    /settings → SettingsPage (static shell — 6 decorative cards, no API)
    /settings (admin) → TenantSettings (scaffold — "Sprint 7, In Development")
    No settings hooks exist in services/hooks/

  Backend:
    admin/router.py → GET/PUT /api/v1/admin/tenants/{id}/settings (✅ works)
    notify/router.py → GET/PUT /api/v1/notifications/preferences (✅ works)
    tenant_config/router.py → 12 endpoints (❌ NOT REGISTERED in main.py)
    workspace/router.py → Dashboard views CRUD (✅ works)

  Database:
    7 settings-related tables exist. 3 have no Python ORM model.
    4 have no API endpoints. 1 has an unregistered router.

FEATURE CLASSIFICATION
───────────────────────────────────────────────────────────────────────────────

  ✅ COMPLETE (2/12)
  ─────────────────────────────────────────────────────────────────────────────
  Tenant Settings (branding, AI config, risk thresholds, SLA hours)
    Frontend: admin panel → TenantSettings (scaffold UI)
    Backend:  GET/PUT /api/v1/admin/tenants/{id}/settings
    DB: tenant_settings table with 25 columns
    CRUD: Read + Update (upsert)
    Validation: Basic field validation
    Status: ✅ Backend complete, frontend is scaffold

  Notification Preferences
    Frontend: ❌ No UI exists
    Backend:  GET/PUT /api/v1/notifications/preferences
    DB: notification_preferences table
    CRUD: Read + Update per notification type
    Validation: Minimal (query params only)
    Status: ✅ Backend complete, no frontend

  Dashboard Views
    Frontend: ❌ No settings UI
    Backend:  Full CRUD at /api/v1/workspace/views
    DB: dashboard_views table
    CRUD: Full CRUD
    Status: ✅ Complete

  🟡 PARTIAL (2/12)
  ─────────────────────────────────────────────────────────────────────────────
  Feature Flags
    Frontend: TenantSettings scaffold (planned but empty)
    Backend:  12 endpoints in tenant_config/router.py
              ⚠ ROUTER NOT REGISTERED IN MAIN.PY — dead code
    DB: feature_flag_overrides table
    CRUD: Create + Delete overrides
    Validation: Yes
    Status: 🟡 Backend exists but inaccessible

  SLA Policies
    Frontend: ❌ No UI
    Backend:  GET/POST /api/v1/reviews/sla-policies
    DB: sla_policies table (⚠ no Python ORM model)
    CRUD: Create + List only (no update/delete)
    Status: 🟡 Missing model, missing endpoints

  ❌ MISSING (8/12)
  ─────────────────────────────────────────────────────────────────────────────
  Approval Thresholds
    DB: approval_thresholds table exists
    API: ❌ None
    Model: ❌ None
    Status: ❌ Data exists, inaccessible

  SLA Metrics
    DB: sla_metrics table exists
    API: ❌ None
    Model: ❌ None
    Status: ❌ Data exists, inaccessible

  User Preferences (JSONB)
    DB: admin_users.preferences column exists
    API: ❌ None
    Model: Column exists
    Status: ❌ No read/update endpoints

  Policy Packs
    Backend: tenant_config/router.py (unregistered)
    Status: ❌ Dead code

  Scoring Overrides
    Backend: tenant_config/router.py (unregistered)
    Status: ❌ Dead code

  Compliance Packs
    Backend: tenant_config/router.py (unregistered)
    Status: ❌ Dead code

  Settings Page (Profile, Notifications, Security, API Keys, Billing, Integrations)
    Frontend: Static card grid only
    Backend: ❌ None
    Status: ❌ Placeholder

  TenantSettings Page (branding, feature flags, risk weights, workflows, packs, routing)
    Frontend: Scaffold only
    Backend: Partial (tenant_settings API exists, tenant_config router unregistered)
    Status: ❌ Placeholder

GAP ANALYSIS
───────────────────────────────────────────────────────────────────────────────

  🔴 CRITICAL GAPS
  ─────────────────────────────────────────────────────────────────────────────
  1. tenant_config router not registered in main.py
     Impact: 12 endpoints (feature flags, policy packs, scoring, compliance, config)
     are completely inaccessible. Any frontend calling these gets 404.

  2. Frontend tenant API service calls non-existent endpoints
     Impact: The typed service at services/api/tenant.ts calls endpoints like
     /api/v1/tenants/{id}/settings which don't exist. The real endpoint is
     /api/v1/admin/tenants/{id}/settings.

  3. 3 database tables have no Python model
     sla_policies, approval_thresholds, sla_metrics — data exists but is
     inaccessible to the application. Risk of schema drift.

  🟡 MEDIUM GAPS
  ─────────────────────────────────────────────────────────────────────────────
  4. Settings page is a static shell with no functionality
  5. User preferences (JSONB column) have no API
  6. SLA Policies missing update/delete
  7. Notification preferences use query params instead of body schemas
  8. No settings-related React Query hooks

REMEDIATION PLAN
───────────────────────────────────────────────────────────────────────────────

  Phase 1 — Critical Fixes (estimated 2 days)
  ─────────────────────────────────────────────────────────────────────────────
  1.1 Register tenant_config router in main.py (5 minutes)
  1.2 Add Python ORM models for sla_policies, approval_thresholds, sla_metrics (4 hours)
  1.3 Fix frontend tenant API service endpoint paths (1 hour)

  Phase 2 — Backend APIs (estimated 3 days)
  ─────────────────────────────────────────────────────────────────────────────
  2.1 Add user preferences API (GET/PUT /api/v1/admin/users/{id}/preferences) (2 hours)
  2.2 Add SLA Policies update/delete endpoints (2 hours)
  2.3 Add Approval Thresholds API (4 hours)
  2.4 Add SLA Metrics API (2 hours)
  2.5 Add notification preferences request body schema (1 hour)

  Phase 3 — Frontend (estimated 5 days)
  ─────────────────────────────────────────────────────────────────────────────
  3.1 Create useTenantSettings hook (2 hours)
  3.2 Create useNotificationPreferences hook (1 hour)
  3.3 Build Tenant Settings form (branding, AI config, risk thresholds) (1 day)
  3.4 Build Notification Preferences UI (1 day)
  3.5 Build Feature Flag toggles UI (1 day)
  3.6 Build SLA Policies management UI (1 day)
  3.7 Wire Profile, Security, API Keys, Billing, Integrations cards (2 days)

  Total estimated effort: 10 days

IMPLEMENTATION ORDER RECOMMENDATION
───────────────────────────────────────────────────────────────────────────────

  Priority | Task                         | Effort | Risk Reduction
  ─────────┼──────────────────────────────┼────────┼────────────────
  P0       | Register tenant_config router| 5 min  | Unblocks 12 endpoints
  P1       | Fix frontend API paths       | 1 hr   | Fixes broken calls
  P1       | Add missing ORM models       | 4 hrs  | Prevents schema drift
  P2       | Add user preferences API     | 2 hrs  | Enables profile settings
  P2       | Build Tenant Settings form   | 1 day  | First visible settings UI
  P3       | Build Notification UI        | 1 day  | User-facing feature
  P3       | Build Feature Flag UI        | 1 day  | Admin capability
  P4       | Add remaining APIs           | 2 days | Completeness
  P4       | Wire remaining settings cards| 2 days | Polish

================================================================================
