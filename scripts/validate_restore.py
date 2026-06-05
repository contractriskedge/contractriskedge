#!/usr/bin/env python3
"""Restore validation script — compares source DB with restored DB."""
import subprocess, os, sys

PSQL = "/opt/homebrew/opt/postgresql@16/bin/psql"
SRC = "postgresql://dev_user:dev_password@localhost:5432/contract_risk_dev"
DST = "postgresql://dev_user:dev_password@localhost:5432/contract_risk_restore_test"


def query(db, sql):
    env = {**os.environ, "PAGER": ""}
    r = subprocess.run([PSQL, db, "-t", "-A", "-c", sql], capture_output=True, text=True, env=env)
    return r.stdout.strip()


print("=" * 60)
print("  RESTORE VALIDATION REPORT")
print("=" * 60)
print()

# 1. Table count
print("--- TABLE COUNT ---")
src_tables = query(SRC, "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
dst_tables = query(DST, "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
print(f"  Source:  {src_tables}")
print(f"  Restore: {dst_tables}")
print(f"  Status:  {'MATCH' if src_tables == dst_tables else 'MISMATCH'}")
print()

# 2. Enum
print("--- ENUM (review_status) ---")
src_enum = query(SRC, "SELECT enum_range(NULL::review_status)::text;")
dst_enum = query(DST, "SELECT enum_range(NULL::review_status)::text;")
print(f"  Source:  {src_enum}")
print(f"  Restore: {dst_enum}")
print(f"  Status:  {'MATCH' if src_enum == dst_enum else 'MISMATCH'}")
print()

# 3. Alembic version
print("--- ALEMBIC VERSION ---")
src_av = query(SRC, "SELECT version_num FROM alembic_version;")
dst_av = query(DST, "SELECT version_num FROM alembic_version;")
print(f"  Source:  {src_av}")
print(f"  Restore: {dst_av}")
print(f"  Status:  {'MATCH' if src_av == dst_av else 'MISMATCH'}")
print()

# 4. DB size
print("--- DB SIZE ---")
src_size = query(SRC, "SELECT pg_size_pretty(pg_database_size(current_database()));")
dst_size = query(DST, "SELECT pg_size_pretty(pg_database_size(current_database()));")
print(f"  Source:  {src_size}")
print(f"  Restore: {dst_size}")
print()

# 5. Row counts
tables = [
    "contract_reviews", "review_assignments", "review_approvals",
    "review_escalations", "review_findings", "review_redlines",
    "review_status_history", "upload_sessions", "ai_execution_runs",
    "notifications", "governance_audit_events", "negotiation_sessions",
    "negotiation_issues", "negotiation_redlines", "negotiation_versions",
    "workflow_instances", "tenants", "admin_users",
]
print("--- KEY TABLE ROW COUNTS ---")
print(f"{'Table':<35} {'Source':>6} {'Restore':>6}  Status")
print("-" * 55)
all_match = True
for t in tables:
    s = query(SRC, f"SELECT count(*) FROM {t};")
    d = query(DST, f"SELECT count(*) FROM {t};")
    match = s == d
    if not match:
        all_match = False
    print(f"{t:<35} {s:>6} {d:>6}  {'MATCH' if match else 'MISMATCH'}")

print()

# 6. Integrity checks
print("--- INTEGRITY CHECKS ---")
fk_count = query(DST, "SELECT count(*) FROM pg_constraint WHERE contype='f';")
print(f"  Foreign key constraints: {fk_count}")

orphan_assign = query(
    DST,
    "SELECT count(*) FROM review_assignments ra WHERE NOT EXISTS (SELECT 1 FROM contract_reviews cr WHERE cr.review_id = ra.review_id);",
)
print(f"  Orphaned assignments:     {orphan_assign}")

orphan_findings = query(
    DST,
    "SELECT count(*) FROM review_findings rf WHERE NOT EXISTS (SELECT 1 FROM contract_reviews cr WHERE cr.review_id = rf.review_id);",
)
print(f"  Orphaned findings:        {orphan_findings}")

uq = query(DST, "SELECT count(*) FROM pg_constraint WHERE conname='uq_review_assignee';")
print(f"  uq_review_assignee:       {'EXISTS' if uq == '1' else 'MISSING'}")

print()

# 7. Overall
print("--- OVERALL RESULT ---")
enum_ok = src_enum == dst_enum
av_ok = src_av == dst_av
integrity_ok = orphan_assign == "0" and orphan_findings == "0"
print(f"  Table counts:  {'PASS' if src_tables == dst_tables else 'FAIL'}")
print(f"  Row counts:    {'PASS' if all_match else 'FAIL'}")
print(f"  Enums:         {'PASS' if enum_ok else 'FAIL'}")
print(f"  Alembic:       {'PASS' if av_ok else 'FAIL'}")
print(f"  Integrity:     {'PASS' if integrity_ok else 'FAIL'}")

if src_tables == dst_tables and all_match and enum_ok and av_ok and integrity_ok:
    print("\n  >>> RESTORE VALIDATION: PASS <<<")
    sys.exit(0)
else:
    print("\n  >>> RESTORE VALIDATION: FAIL <<<")
    sys.exit(1)
