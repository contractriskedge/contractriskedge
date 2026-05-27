"""Central permission registry. Single source of truth for all permission constants."""


class Permissions:
    # ── Contracts ─────────────────────────────────────────────────
    CONTRACTS_READ = "contracts:read"
    CONTRACTS_WRITE = "contracts:write"
    CONTRACTS_DELETE = "contracts:delete"
    CONTRACTS_APPROVE = "contracts:approve"

    # ── AI ────────────────────────────────────────────────────────
    AI_ANALYZE = "ai:analyze"
    AI_VIEW = "ai:view"
    AI_MANAGE = "ai:manage"

    # ── Workflows ─────────────────────────────────────────────────
    WORKFLOWS_READ = "workflows:read"
    WORKFLOWS_WRITE = "workflows:write"
    WORKFLOWS_APPROVE = "workflows:approve"
    WORKFLOWS_ESCALATE = "workflows:escalate"
    WORKFLOWS_FINALIZE = "workflows:approve"  # Same permission as approve
    WORKFLOWS_ARCHIVE = "workflows:write"
    WORKFLOWS_BULK = "workflows:write"

    # ── Vendors ───────────────────────────────────────────────────
    VENDORS_READ = "vendors:read"
    VENDORS_WRITE = "vendors:write"

    # ── Audit ─────────────────────────────────────────────────────
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # ── Users ─────────────────────────────────────────────────────
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"

    # ── Benchmarks ────────────────────────────────────────────────
    BENCHMARK_READ = "benchmarks:read"
    BENCHMARK_WRITE = "benchmarks:write"
    BENCHMARK_EXPORT = "benchmarks:export"
    BENCHMARK_SEED = "benchmarks:seed"
    BENCHMARK_ADMIN = "benchmarks:admin"

    # ── Admin ─────────────────────────────────────────────────────
    ADMIN_TENANT = "admin:tenant"
    ADMIN_SYSTEM = "admin:system"

    # ── Special ───────────────────────────────────────────────────
    ALL = "*"
