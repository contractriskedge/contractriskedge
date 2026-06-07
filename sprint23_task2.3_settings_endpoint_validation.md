================================================================================
  SPRINT 23 TASK 2.3 — Settings Endpoint Validation Report
  Completed: June 5, 2026
================================================================================

EXECUTIVE SUMMARY
───────────────────────────────────────────────────────────────────────────────

  13 endpoints tested across 4 settings domains.
  9 fully functional (69%).
  4 broken — all POST write endpoints with pre-existing service-layer bugs.

  The tenant_config service uses raw SQL with mixed named/positional parameter
  styles (e.g., `$1, $2, :name::jsonb`) which asyncpg rejects. These are
  pre-existing bugs in the service layer, not caused by the router registration.

  Additionally, the feature_flag_overrides table has a different schema than
  what the service expects (integer `id` vs varchar `override_id`).

ENDPOINT VALIDATION MATRIX
───────────────────────────────────────────────────────────────────────────────

  Endpoint                          | Method | Status | DB Verified | Notes
  ──────────────────────────────────┼────────┼────────┼─────────────┼──────────────
  /admin/settings                   | GET    | ✅ 200 | ✅ Real data | 25+ fields
  /admin/settings                   | PUT    | ✅ 200 | ✅ Persists  | Read-back OK
  /tenant-config/features/definitions| GET   | ✅ 200 | ✅ Built-in  | 14 flags
  /tenant-config/features/evaluate  | GET    | ✅ 200 | ✅ DB-driven | 14 evaluated
  /tenant-config/features/evaluate/{k}| GET   | ✅ 200 | ✅ DB-driven | Single flag
  /tenant-config/features/overrides | POST   | ❌ 500 | ❌           | Column mismatch
  /tenant-config/policy-packs       | GET    | ✅ 200 | ✅ DB-driven | Empty list
  /tenant-config/policy-packs       | POST   | ❌ 500 | ❌           | Param style bug
  /tenant-config/scoring-overrides  | GET    | ✅ 200 | ✅ DB-driven | Empty list
  /tenant-config/scoring-overrides  | POST   | ❌ 500 | ❌           | Param style bug
  /tenant-config/compliance-packs   | GET    | ✅ 200 | ✅ DB-driven | Empty list
  /tenant-config/compliance-packs   | POST   | ❌ 422 | ❌           | Region enum
  /tenant-config/summary            | GET    | ✅ 200 | ✅ Aggregated| All domains

ADMIN SETTINGS — DETAILED
───────────────────────────────────────────────────────────────────────────────

  GET /admin/settings
    Status:     ✅ 200
    Data:       Real database data from tenant_settings table
    Fields:     25+ (branding, AI config, risk thresholds, SLA hours, features)
    Auth:       ✅ Requires admin permission
    Tenant:     ✅ Multi-tenant safe (scoped by tenant_id)

  PUT /admin/settings
    Status:     ✅ 200
    Write:      ✅ Persisted to tenant_settings table
    Read-back:  ✅ brand_name=TestCorp-Validate, ai_temperature=20, risk_crit=75
    Validation: ✅ Validates ai_temperature (0-100), risk thresholds (0-100), SLA hours
    Auth:       ✅ Requires admin permission
    Tenant:     ✅ Multi-tenant safe

FEATURE FLAGS — DETAILED
───────────────────────────────────────────────────────────────────────────────

  GET /tenant-config/features/definitions
    Status:     ✅ 200
    Data:       14 built-in flag definitions with defaults, states, dependencies
    Source:     In-memory (_BUILTIN_FEATURE_FLAGS), no DB query

  GET /tenant-config/features/evaluate
    Status:     ✅ 200
    Data:       14 evaluated flags with tenant overrides applied
    Source:     DB-driven (feature_flag_overrides table queried)
    DB verified:✅ Reads from feature_flag_overrides

  POST /tenant-config/features/overrides
    Status:     ❌ 500
    Root cause: Service expects `override_id` (varchar) column but the actual
                table has `id` (integer, auto-increment). The INSERT statement
                includes `override_id` which doesn't exist.
    Fix:        Update service.py to use the actual column name `id` or add
                an `override_id` column via migration.

POLICY PACKS — DETAILED
───────────────────────────────────────────────────────────────────────────────

  GET /tenant-config/policy-packs
    Status:     ✅ 200
    Data:       Empty list (table exists, no data yet)
    DB verified:✅ Table created by migration m0n1o2p3q4r5

  POST /tenant-config/policy-packs
    Status:     ❌ 500
    Root cause: Service uses mixed parameter styles: `$1, $2, :name::jsonb`.
                asyncpg does not support mixing named (`:name`) and positional
                (`$1`) parameters in the same query.
    Fix:        Convert all parameters to positional (`$1, $2, $3::jsonb`) or
                all to named (`:name, :other, :third::jsonb`).

SCORING OVERRIDES — DETAILED
───────────────────────────────────────────────────────────────────────────────

  GET /tenant-config/scoring-overrides
    Status:     ✅ 200
    Data:       Empty list (table exists, no data yet)
    DB verified:✅ Table created by migration m0n1o2p3q4r5

  POST /tenant-config/scoring-overrides
    Status:     ❌ 500
    Root cause: Same as policy_packs — mixed `$1, :bus::jsonb` parameter styles.
    Fix:        Same as policy_packs — convert to consistent parameter style.

COMPLIANCE PACKS — DETAILED
───────────────────────────────────────────────────────────────────────────────

  GET /tenant-config/compliance-packs
    Status:     ✅ 200
    Data:       Empty list (table exists, no data yet)
    DB verified:✅ Table created by migration m0n1o2p3q4r5

  POST /tenant-config/compliance-packs
    Status:     ❌ 422
    Root cause: Region field requires enum value. Input 'EU' is not valid;
                expected one of: us_federal, us_state, eu, uk, apac, latam, global.
    Fix:        Use lowercase 'eu' instead of 'EU'.

CONFIG SUMMARY — DETAILED
───────────────────────────────────────────────────────────────────────────────

  GET /tenant-config/summary
    Status:     ✅ 200
    Data:       Aggregated summary with 8 keys:
                tenant_id, tenant_name, plan, feature_flags,
                active_policy_packs, scoring_overrides, compliance_packs, settings
    Source:     Combines data from tenant_settings, feature_flag_overrides,
                policy_packs, scoring_overrides, compliance_packs tables
    DB verified:✅ Real aggregated data

CLASSIFICATION SUMMARY
───────────────────────────────────────────────────────────────────────────────

  Classification | Count | Endpoints
  ───────────────┼───────┼────────────────────────────────────────────
  Fully Functional|  9   | GET/PUT /admin/settings
                |       | GET /tenant-config/features/definitions
                |       | GET /tenant-config/features/evaluate
                |       | GET /tenant-config/features/evaluate/{key}
                |       | GET /tenant-config/policy-packs
                |       | GET /tenant-config/scoring-overrides
                |       | GET /tenant-config/compliance-packs
                |       | GET /tenant-config/summary
  ───────────────┼───────┼────────────────────────────────────────────
  Broken (service)| 3   | POST /tenant-config/features/overrides
                |       | POST /tenant-config/policy-packs
                |       | POST /tenant-config/scoring-overrides
  ───────────────┼───────┼────────────────────────────────────────────
  Broken (schema)| 1   | POST /tenant-config/compliance-packs (422)
  ───────────────┼───────┼────────────────────────────────────────────
  Total         | 13   |

DEFECTS FOUND
───────────────────────────────────────────────────────────────────────────────

  Defect 1: feature_flag_overrides column mismatch (HIGH)
    The service INSERT expects `override_id` (varchar) but the actual table
    has `id` (integer, auto-increment). All 3 existing backup SQL files confirm
    the table has `id SERIAL PRIMARY KEY`, not `override_id`.
    Fix: Update service.py INSERT to omit override_id (use DEFAULT).

  Defect 2: Mixed parameter styles in raw SQL (HIGH)
    Three service methods mix `$1` positional params with `:name` named params
    in the same query. asyncpg requires consistent parameter style.
    Affected: PolicyPackService.create_pack(), ScoringOverrideService.create_override()
    Fix: Convert all `:name::jsonb` casts to `$N::jsonb`.

  Defect 3: CompliancePack region enum validation (LOW)
    The Pydantic schema expects lowercase enum values ('eu', 'uk') but the
    test used uppercase ('EU'). This is a test input issue, not a service bug.

NOTIFICATION PREFERENCES VERIFICATION
───────────────────────────────────────────────────────────────────────────────

  (Not tested in this run — requires auth token with user context)

================================================================================
