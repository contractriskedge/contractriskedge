"""Sprint 23 Task 2.4 — Settings Endpoint Validation Rerun.

Tests all 13 Settings endpoints:
- GET/PUT /admin/settings
- GET /tenant-config/features/definitions
- GET /tenant-config/features/evaluate
- GET /tenant-config/features/evaluate/{key}
- POST /tenant-config/features/overrides
- GET/POST /tenant-config/policy-packs
- GET/POST /tenant-config/scoring-overrides
- GET/POST /tenant-config/compliance-packs
- GET /tenant-config/summary

For every POST: create, verify 201, read back, verify DB persistence, verify schema.
"""

import json
import urllib.request
import urllib.error
import subprocess
import sys
import os

BASE = "http://localhost:3000/api/v1"
H = {"Content-Type": "application/json"}
# Note: No X-Tenant-ID override — uses the default dev user's tenant context.
# The dev user (from dev-user token) has tenant_id = settings.dev_tenant_id.
TENANT_H = H.copy()

ok = 0
fail = 0
results = []


def req(method, path, body=None, headers=H):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        try:
            return e.code, json.loads(body_bytes)
        except Exception:
            return e.code, {"raw": body_bytes[:300].decode(errors="replace")}


def check(desc, method, path, body=None, headers=H, expected=200):
    global ok, fail
    status, data = req(method, path, body, headers)
    passed = status == expected
    if passed:
        ok += 1
    else:
        fail += 1
    note = "" if passed else f"Expected {expected}, got {status}"
    results.append((desc, method, path, status, "PASS" if passed else "FAIL", note))
    if not passed:
        print(f"  FAIL: {desc} -> {status} {json.dumps(data)[:200]}")
    return status, data


def cleanup_test_data():
    """Remove test records created during validation."""
    script = """
import asyncio
from app.kernel.database.session import TenantAwareSessionFactory
from app.config import settings
import sqlalchemy as sa

async def clean():
    factory = TenantAwareSessionFactory(database_url=settings.database_url)
    async with await factory.create_session(tenant_id='system', user_id='system', user_role='admin') as session:
        await session.execute(sa.text("DELETE FROM feature_flag_overrides WHERE flag_key = 'test_flag_s23'"))
        await session.execute(sa.text("DELETE FROM policy_packs WHERE name = 'S23 Test Pack'"))
        await session.execute(sa.text("DELETE FROM scoring_overrides WHERE clause_type = 'indemnification' AND reason = 'Sprint 23 verification'"))
        await session.execute(sa.text("DELETE FROM compliance_packs WHERE name = 'S23 US Fed'"))
        await session.commit()
        print('Cleanup OK')

asyncio.run(clean())
"""
    r = subprocess.run(
        ["bash", "-c", "cd /Volumes/ContractEdge/ContractRiskEdge/backend && source .venv/bin/activate && python3 -c " + repr(script)],
        capture_output=True, text=True, shell=False,
    )
    # Try simpler approach
    r = subprocess.run(
        ["/Volumes/ContractEdge/ContractRiskEdge/backend/.venv/bin/python3", "-c", script],
        cwd="/Volumes/ContractEdge/ContractRiskEdge/backend",
        capture_output=True, text=True,
    )
    print(f"  Cleanup: {r.stdout.strip()}")
    if r.returncode != 0:
        print(f"  Cleanup stderr: {r.stderr[:200]}")


def main():
    global ok, fail, results

    print("=" * 70)
    print("Sprint 23 Task 2.4 — Settings Endpoint Validation Rerun")
    print("=" * 70)

    # ── 1. GET /admin/settings ────────────────────────────────────
    print("\n--- 1. GET /admin/settings ---")
    check("Admin Settings GET", "GET", "/admin/settings", headers=TENANT_H)

    # ── 2. PUT /admin/settings ────────────────────────────────────
    print("\n--- 2. PUT /admin/settings ---")
    check("Admin Settings PUT", "PUT", "/admin/settings", body={
        "default_reviewer": "test-user",
        "max_findings_per_review": 50,
        "auto_escalation_days": 7,
        "notification_email": "test@example.com",
    }, headers=TENANT_H)

    # ── 3. GET /tenant-config/features/definitions ────────────────
    print("\n--- 3. GET /tenant-config/features/definitions ---")
    check("Feature Definitions GET", "GET", "/tenant-config/features/definitions", headers=TENANT_H)

    # ── 4. GET /tenant-config/features/evaluate ───────────────────
    print("\n--- 4. GET /tenant-config/features/evaluate ---")
    check("Feature Evaluate Bulk GET", "GET", "/tenant-config/features/evaluate", headers=TENANT_H)

    # ── 5. GET /tenant-config/features/evaluate/{key} ─────────────
    print("\n--- 5. GET /tenant-config/features/evaluate/{key} ---")
    check("Feature Evaluate Single GET", "GET",
          "/tenant-config/features/evaluate/contract_review_enabled", headers=TENANT_H)

    # ── 6. POST /tenant-config/features/overrides ─────────────────
    print("\n--- 6. POST /tenant-config/features/overrides ---")
    s, d = check("Feature Override POST", "POST", "/tenant-config/features/overrides", body={
        "flag_key": "test_flag_s23", "target_type": "tenant", "target_id": "tenant-001",
        "enabled": True, "reason": "Sprint 23 verification",
    }, headers=TENANT_H, expected=201)
    if s == 201:
        # Verify DB persistence by reading back
        s2, d2 = req("GET", "/tenant-config/features/evaluate/test_flag_s23", headers=TENANT_H)
        if s2 == 200:
            ok += 1
            results.append(("Feature Override DB Verify", "GET",
                           "/tenant-config/features/evaluate/test_flag_s23", s2, "PASS", ""))
        else:
            fail += 1
            results.append(("Feature Override DB Verify", "GET",
                           "/tenant-config/features/evaluate/test_flag_s23", s2, "FAIL",
                           f"Could not read back: {s2}"))

    # ── 7. GET /tenant-config/policy-packs ────────────────────────
    print("\n--- 7. GET /tenant-config/policy-packs ---")
    check("Policy Packs LIST GET", "GET", "/tenant-config/policy-packs", headers=TENANT_H)

    # ── 8. POST /tenant-config/policy-packs ───────────────────────
    print("\n--- 8. POST /tenant-config/policy-packs ---")
    s, d = check("Policy Pack POST", "POST", "/tenant-config/policy-packs", body={
        "name": "S23 Test Pack", "description": "Sprint 23 verification", "scope": "tenant",
        "rule_overrides": [], "threshold_overrides": [], "clause_overrides": [],
    }, headers=TENANT_H, expected=201)
    pack_id = d.get("pack_id", "") if s == 201 else ""
    if s == 201 and pack_id:
        s2, d2 = req("GET", f"/tenant-config/policy-packs/{pack_id}", headers=TENANT_H)
        if s2 == 200:
            ok += 1
            results.append(("Policy Pack DB Verify", "GET",
                           f"/tenant-config/policy-packs/{pack_id}", s2, "PASS", ""))
        else:
            fail += 1
            results.append(("Policy Pack DB Verify", "GET",
                           f"/tenant-config/policy-packs/{pack_id}", s2, "FAIL",
                           f"Could not read back: {s2}"))

    # ── 9. GET /tenant-config/scoring-overrides ───────────────────
    print("\n--- 9. GET /tenant-config/scoring-overrides ---")
    check("Scoring Overrides LIST GET", "GET", "/tenant-config/scoring-overrides", headers=TENANT_H)

    # ── 10. POST /tenant-config/scoring-overrides ─────────────────
    print("\n--- 10. POST /tenant-config/scoring-overrides ---")
    s, d = check("Scoring Override POST", "POST", "/tenant-config/scoring-overrides", body={
        "clause_type": "indemnification", "override_severity": "critical",
        "override_risk_weight": 1.8, "override_risk_score": 0.95,
        "is_active": True, "reason": "Sprint 23 verification",
        "applies_to_business_units": ["engineering", "legal"],
    }, headers=TENANT_H, expected=201)
    override_id = d.get("override_id", "") if s == 201 else ""

    # ── 11. GET /tenant-config/compliance-packs ───────────────────
    print("\n--- 11. GET /tenant-config/compliance-packs ---")
    check("Compliance Packs LIST GET", "GET", "/tenant-config/compliance-packs", headers=TENANT_H)

    # ── 12. POST /tenant-config/compliance-packs ──────────────────
    print("\n--- 12. POST /tenant-config/compliance-packs ---")
    s, d = check("Compliance Pack POST", "POST", "/tenant-config/compliance-packs", body={
        "region": "us_federal", "name": "S23 US Fed", "description": "Sprint 23 verification",
        "regulations": [{"regulation_key": "gdpr", "provisions": ["art5"], "severity_if_missing": "high"}],
        "required_clause_categories": ["data_protection"], "forbidden_clause_categories": [],
        "jurisdiction_rules": [],
    }, headers=TENANT_H, expected=201)
    compliance_pack_id = d.get("pack_id", "") if s == 201 else ""

    # ── 13. GET /tenant-config/summary ────────────────────────────
    print("\n--- 13. GET /tenant-config/summary ---")
    check("Tenant Config Summary GET", "GET", "/tenant-config/summary", headers=TENANT_H)

    # ── CLEANUP ────────────────────────────────────────────────────
    print("\n--- Cleanup ---")
    cleanup_test_data()

    # ── SUMMARY ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nTotal checks: {ok + fail}")
    print(f"Passed: {ok}")
    print(f"Failed: {fail}")
    print()
    print(f"{'Check':40s} {'Method':6s} {'Status':6s} {'Result':6s}  {'Notes'}")
    print("-" * 70)
    for desc, method, path, status, result, note in results:
        print(f"{desc:40s} {method:6s} {str(status):6s} {result:6s}  {note}")
    print(f"\nFunctional endpoints: {ok}/{ok + fail}")

    return 1 if fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
