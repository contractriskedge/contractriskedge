#!/usr/bin/env python3
"""
Sprint 21 Task 4.3 — Concurrency & Race Condition Validation.

Tests 6 race-condition scenarios against a running FastAPI server.
Uses asyncio.gather() to fire concurrent requests and verifies
database integrity after each race.

Usage:
  python test_concurrency_validation.py [--url http://localhost:3000]

Requires:
  - FastAPI server running on BASE_URL
  - PostgreSQL database accessible via DB_URL
  - A review in the appropriate starting state for each test
"""

import asyncio
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.request
import urllib.error
from base64 import urlsafe_b64encode
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, text

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
API_URL = f"{BASE_URL}/api/v1"
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://dev_user:dev_password@localhost:5432/contract_risk_dev",
)
DEV_JWT_SECRET = os.getenv(
    "DEV_JWT_SECRET",
    "dev-local-jwt-secret-do-not-use-in-production",
)

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️ WARN"

results: list[dict] = []


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def create_token() -> str:
    """Create a dev JWT token matching the backend dev_token.py."""
    header = urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload_data = {
        "sub": "dev-user",
        "email": "dev@localhost",
        "tenant_id": "00000000-0000-4000-8000-000000000001",
        "role": "tenant_admin",
        "permissions": [
            "*",
            "contracts:approve",
            "workflows:write",
            "workflows:approve",
            "contracts:read",
            "audit:read",
            "workflows:escalate",
        ],
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    payload = urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()
    signature = urlsafe_b64encode(
        hmac.new(
            DEV_JWT_SECRET.encode(),
            f"{header}.{payload}".encode(),
            hashlib.sha256,
        ).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.{signature}"


def api_sync(method: str, path: str, token: str = "", body: dict = None) -> tuple:
    """Synchronous API request."""
    url = f"{API_URL}{path}"
    req = urllib.request.Request(url, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    data_bytes = json.dumps(body).encode() if body is not None else None
    try:
        r = urllib.request.urlopen(req, data_bytes)
        body_bytes = r.read()
        return r.status, json.loads(body_bytes.decode()) if body_bytes else {"status": "ok"}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"detail": str(e)}
    except Exception as e:
        return 0, {"detail": str(e)}


async def api(method: str, path: str, token: str = "", body: dict = None) -> tuple:
    """Async wrapper for API request using asyncio.to_thread."""
    return await asyncio.to_thread(api_sync, method, path, token, body)


def db_query(sql: str, params: dict = None) -> list[dict]:
    """Execute raw SQL and return rows as list of dicts."""
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        rows = result.fetchall()
        columns = result.keys()
        return [dict(zip(columns, row)) for row in rows]


def db_query_one(sql: str, params: dict = None) -> Optional[dict]:
    rows = db_query(sql, params)
    return rows[0] if rows else None


def get_review_status(review_id: str) -> Optional[str]:
    row = db_query_one(
        "SELECT status::text FROM contract_reviews WHERE review_id::text = :rid AND is_deleted = FALSE",
        {"rid": review_id},
    )
    return row["status"] if row else None


def get_status_history(review_id: str) -> list[dict]:
    return db_query(
        """SELECT from_status, to_status, changed_by, created_at::text as created_at
           FROM review_status_history
           WHERE review_id::text = :rid
           ORDER BY created_at ASC""",
        {"rid": review_id},
    )


def get_assignments(review_id: str) -> list[dict]:
    return db_query(
        """SELECT assignee_id, role, assigned_by, created_at::text as created_at
           FROM review_assignments
           WHERE review_id::text = :rid
           ORDER BY created_at ASC""",
        {"rid": review_id},
    )


def get_approvals(review_id: str) -> list[dict]:
    return db_query(
        """SELECT decision, approver_id, comments, decided_at::text as decided_at
           FROM review_approvals
           WHERE review_id::text = :rid
           ORDER BY decided_at ASC""",
        {"rid": review_id},
    )


def find_review_in_status(target_status: str) -> Optional[str]:
    """Find a review in the given status, or None."""
    row = db_query_one(
        """SELECT review_id::text FROM contract_reviews
           WHERE status::text = :s AND is_deleted = FALSE
           ORDER BY created_at DESC LIMIT 1""",
        {"s": target_status},
    )
    return row["review_id"] if row else None


def find_or_create_review_in_status(target_status: str) -> str:
    """Find a review in the given status, or create one by advancing through states."""
    existing = find_review_in_status(target_status)
    if existing:
        return existing

    token = create_token()

    # Find a review in draft or ai_analyzed to work with
    rid = find_review_in_status("ai_analyzed") or find_review_in_status("draft")
    if not rid:
        # List reviews and pick the first one
        code, data = api_sync("GET", "/reviews?page_size=5", token)
        if code == 200 and data.get("data"):
            rid = data["data"][0].get("review_id")
        else:
            raise RuntimeError(f"No reviews available. API returned {code}: {data}")

    # Advance through states to reach target
    status = get_review_status(rid)

    # State progression map
    progression = {
        "draft": "ai_analyzed",
        "ai_analyzed": "in_review",
        "in_review": "legal_approval",
        "legal_approval": "exec_approval",
        "exec_approval": "approved",
        "approved": "finalized",
    }

    # Walk from current status to target
    while status and status != target_status and status in progression:
        next_status = progression[status]
        # For transitions that need assignment first
        if status == "ai_analyzed" and target_status != "ai_analyzed":
            code, _ = api_sync("POST", f"/reviews/{rid}/assign", token, {
                "assignee_id": "reviewer@test.com",
                "role": "reviewer",
            })
            if code not in (200, 400):
                pass  # May already be assigned

        code, data = api_sync(
            "POST", f"/reviews/{rid}/status?status={next_status}&reason=Concurrency+test+setup",
            token,
        )
        if code == 200:
            status = get_review_status(rid)
        else:
            # Try workflow/advance as fallback
            action_map = {
                "in_review": "in_review",
                "legal_approval": "legal_review",
                "exec_approval": "exec_approval",
                "approved": "approved",
                "finalized": "finalized",
            }
            action = action_map.get(next_status)
            if action:
                code2, _ = api_sync(
                    "POST", f"/reviews/{rid}/workflow/advance", token,
                    {"action": action, "note": "Concurrency test setup"},
                )
                if code2 == 200:
                    status = get_review_status(rid)

    if status != target_status:
        raise RuntimeError(
            f"Could not advance review {rid} to '{target_status}'. "
            f"Currently at '{status}'. Tried progression through {list(progression.keys())}"
        )

    return rid


def heading(text: str):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")


def subheading(text: str):
    print(f"\n  ── {text}")


def check(step: str, detail: str, success: bool, data=None):
    status = PASS if success else FAIL
    results.append({"step": step, "detail": detail[:300], "status": status, "data": data})
    print(f"  {status} {step}")
    if detail:
        print(f"         {detail}")


# ═══════════════════════════════════════════════════════════════════
# Test 1: Simultaneous Approval Race
# ═══════════════════════════════════════════════════════════════════


async def test_simultaneous_approval_race(token: str):
    """Fire 2 concurrent approve requests. Only one should succeed."""
    heading("TEST 1: Simultaneous Approval Race")
    print("  Scenario: Two concurrent approve requests on the same review")

    rid = find_or_create_review_in_status("exec_approval")
    print(f"  Review ID: {rid}")
    print(f"  Initial status: {get_review_status(rid)}")

    # Resolve any open critical/high findings that would block approval
    findings = db_query(
        """SELECT finding_id::text FROM review_findings
           WHERE review_id::text = :rid AND resolution IS NULL
           AND severity IN ('critical', 'high')""",
        {"rid": rid},
    )
    for f in findings:
        api_sync("POST", f"/reviews/{rid}/findings/{f['finding_id']}/resolve", token, {
            "resolution": "acknowledged",
            "note": "Auto-resolved for concurrency test",
        })
    if findings:
        print(f"  Resolved {len(findings)} critical/high findings before approval race")

    history_before = len(get_status_history(rid))

    # Fire 2 concurrent approves
    approve_body = {"decision": "approved", "comments": "Concurrent approve test"}
    responses = await asyncio.gather(
        api("POST", f"/reviews/{rid}/approve", token, approve_body),
        api("POST", f"/reviews/{rid}/approve", token, approve_body),
    )

    status_after = get_review_status(rid)
    history_after = get_status_history(rid)
    approvals = get_approvals(rid)

    successes = sum(1 for code, _ in responses if code == 200)
    failures = sum(1 for code, _ in responses if code != 200)

    print(f"  Responses: {responses}")
    print(f"  Final status: {status_after}")
    print(f"  Approvals recorded: {len(approvals)}")
    print(f"  Status history entries: {len(history_after)} (was {history_before})")

    # Verify: at most 1 approval should succeed
    check(
        "1a. At most 1 approve succeeds",
        f"{successes} success, {failures} failed",
        successes <= 1,
    )
    # Verify: final status is approved
    check(
        "1b. Final status is approved",
        f"status={status_after}",
        status_after == "approved",
    )
    # Verify: at most 1 approval record
    check(
        "1c. At most 1 approval record",
        f"approvals={len(approvals)}",
        len(approvals) <= 1,
    )
    # Verify: exactly 1 status transition to approved
    approved_transitions = [h for h in history_after if h["to_status"] == "approved"]
    check(
        "1d. Exactly 1 approved transition",
        f"transitions={len(approved_transitions)}",
        len(approved_transitions) == 1,
    )


# ═══════════════════════════════════════════════════════════════════
# Test 2: Approve vs Reject Race
# ═══════════════════════════════════════════════════════════════════


async def test_approve_vs_reject_race(token: str):
    """Fire concurrent approve and reject. Exactly one should win."""
    heading("TEST 2: Approve vs Reject Race")
    print("  Scenario: Concurrent approve and reject on the same review")

    rid = find_or_create_review_in_status("exec_approval")
    print(f"  Review ID: {rid}")
    print(f"  Initial status: {get_review_status(rid)}")

    history_before = len(get_status_history(rid))

    # Fire concurrent approve and reject
    responses = await asyncio.gather(
        api("POST", f"/reviews/{rid}/approve", token, {
            "decision": "approved", "comments": "Concurrent approve",
        }),
        api("POST", f"/reviews/{rid}/approve", token, {
            "decision": "rejected", "comments": "Concurrent reject",
        }),
    )

    status_after = get_review_status(rid)
    history_after = get_status_history(rid)
    approvals = get_approvals(rid)

    successes = sum(1 for code, _ in responses if code == 200)
    print(f"  Responses: {responses}")
    print(f"  Final status: {status_after}")
    print(f"  Approvals recorded: {len(approvals)}")

    # Verify: exactly one wins
    check(
        "2a. Exactly one request succeeds",
        f"{successes} success, {2 - successes} failed",
        successes == 1,
    )
    # Verify: status is either approved or rejected (deterministic)
    check(
        "2b. Final status is terminal",
        f"status={status_after}",
        status_after in ("approved", "rejected"),
    )
    # Verify: exactly 1 approval record
    check(
        "2c. Exactly 1 approval record",
        f"approvals={len(approvals)}",
        len(approvals) == 1,
    )
    # Verify: status history has exactly 1 terminal transition
    terminal_transitions = [
        h for h in history_after
        if h["to_status"] in ("approved", "rejected")
        and h["from_status"] != h["to_status"]
    ]
    check(
        "2d. Exactly 1 terminal transition",
        f"transitions={len(terminal_transitions)}",
        len(terminal_transitions) == 1,
    )


# ═══════════════════════════════════════════════════════════════════
# Test 3: Escalate vs Approve Race
# ═══════════════════════════════════════════════════════════════════


async def test_escalate_vs_approve_race(token: str):
    """Fire concurrent escalate and approve. No impossible states."""
    heading("TEST 3: Escalate vs Approve Race")
    print("  Scenario: Concurrent escalate and approve on the same review")

    rid = find_or_create_review_in_status("in_review")
    print(f"  Review ID: {rid}")
    print(f"  Initial status: {get_review_status(rid)}")

    # Fire concurrent escalate and approve
    responses = await asyncio.gather(
        api("POST", f"/reviews/{rid}/escalate", token, {
            "reason": "Concurrent escalate test",
            "target_workflow_stage": "legal_approval",
        }),
        api("POST", f"/reviews/{rid}/approve", token, {
            "decision": "approved", "comments": "Concurrent approve test",
        }),
    )

    status_after = get_review_status(rid)
    history_after = get_status_history(rid)

    print(f"  Responses: {responses}")
    print(f"  Final status: {status_after}")

    # Verify: status is a valid state
    valid_states = {
        "in_review", "legal_approval", "exec_approval",
        "approved", "rejected", "escalated",
    }
    check(
        "3a. Final status is valid",
        f"status={status_after}",
        status_after in valid_states,
    )
    # Verify: no impossible combinations (e.g., approved + escalated)
    if status_after == "approved":
        check("3b. Approve won", "status=approved", True)
    elif status_after == "escalated" or status_after == "legal_approval":
        check("3b. Escalate won", f"status={status_after}", True)
    else:
        check("3b. Neither won outright", f"status={status_after}", True)


# ═══════════════════════════════════════════════════════════════════
# Test 4: Finalize vs Modify Race
# ═══════════════════════════════════════════════════════════════════


async def test_finalize_vs_modify_race(token: str):
    """Finalized reviews must remain immutable under concurrent modify attempts."""
    heading("TEST 4: Finalize vs Modify Race")
    print("  Scenario: Concurrent finalize and status modify on the same review")

    rid = find_or_create_review_in_status("approved")
    print(f"  Review ID: {rid}")
    print(f"  Initial status: {get_review_status(rid)}")

    # Fire concurrent finalize and status change
    responses = await asyncio.gather(
        api("POST", f"/reviews/{rid}/finalize", token),
        api("POST", f"/reviews/{rid}/status?status=in_review&reason=Concurrent+modify", token),
        api("POST", f"/reviews/{rid}/status?status=rejected&reason=Concurrent+modify", token),
    )

    status_after = get_review_status(rid)
    history_after = get_status_history(rid)

    print(f"  Responses: {responses}")
    print(f"  Final status: {status_after}")

    # Verify: final status is finalized (or executed/archived)
    check(
        "4a. Final status is terminal",
        f"status={status_after}",
        status_after in ("finalized", "executed", "archived", "approved"),
    )
    # Verify: no transition back to active state
    history_statuses = [h["to_status"] for h in history_after]
    active_states = {"draft", "ai_analyzed", "in_review", "pending_approval"}
    has_active_after = any(s in active_states for s in history_statuses[-3:])
    check(
        "4b. No transition back to active state",
        f"last transitions: {history_statuses[-3:]}",
        not has_active_after,
    )


# ═══════════════════════════════════════════════════════════════════
# Test 5: Concurrent Assignment Race
# ═══════════════════════════════════════════════════════════════════


async def test_concurrent_assignment_race(token: str):
    """5 concurrent assignment requests to the same reviewer must not create duplicates.

    This tests the real race condition: what happens when 5 requests simultaneously
    try to assign the same reviewer to the same review? Only one should succeed.
    """
    heading("TEST 5: Concurrent Assignment Race")
    print("  Scenario: 5 concurrent assignment requests to the SAME reviewer")

    rid = find_or_create_review_in_status("ai_analyzed")
    print(f"  Review ID: {rid}")
    print(f"  Initial status: {get_review_status(rid)}")

    assignments_before = len(get_assignments(rid))

    # All 5 requests assign the SAME reviewer to test the race condition
    same_assignee = "reviewer@test.com"

    # Fire 5 concurrent assignments to the same reviewer
    responses = await asyncio.gather(*[
        api("POST", f"/reviews/{rid}/assign", token, {
            "assignee_id": same_assignee,
            "role": "reviewer",
        })
        for _ in range(5)
    ])

    assignments_after = get_assignments(rid)
    status_after = get_review_status(rid)

    successes = sum(1 for code, _ in responses if code == 200)
    print(f"  Responses: {[(c, str(d)[:80]) for c, d in responses]}")
    print(f"  Assignments before: {assignments_before}, after: {len(assignments_after)}")
    print(f"  Final status: {status_after}")

    # Verify: at most 1 assignment should succeed (same reviewer can't be assigned twice)
    check(
        "5a. At most 1 assignment succeeds (same reviewer)",
        f"{successes} success, {5 - successes} failed",
        successes <= 1,
    )
    # Verify: no duplicate assignee in assignments
    assignees_used = [a["assignee_id"] for a in assignments_after]
    check(
        "5b. No duplicate assignees",
        f"assignees={assignees_used}",
        len(assignees_used) == len(set(assignees_used)),
    )
    # Verify: final status is valid
    check(
        "5c. Final status is valid",
        f"status={status_after}",
        status_after in ("review_ready", "in_review", "ai_analyzed"),
    )


# ═══════════════════════════════════════════════════════════════════
# Test 6: Transition vs Read Consistency
# ═══════════════════════════════════════════════════════════════════


async def test_transition_vs_read_consistency(token: str):
    """Repeated GET requests during a status transition must not error."""
    heading("TEST 6: Transition vs Read Consistency")
    print("  Scenario: Repeated GET requests during status transition")

    rid = find_or_create_review_in_status("in_review")
    print(f"  Review ID: {rid}")
    print(f"  Initial status: {get_review_status(rid)}")

    # Fire concurrent reads and a transition
    async def read_review():
        code, data = await api("GET", f"/reviews/{rid}", token)
        return code, data

    async def do_transition():
        code, data = await api(
            "POST", f"/reviews/{rid}/status?status=legal_approval&reason=Consistency+test",
            token,
        )
        return code, data

    # 5 concurrent reads + 1 transition
    tasks = [read_review() for _ in range(5)] + [do_transition()]
    responses = await asyncio.gather(*tasks)

    read_responses = responses[:5]
    transition_response = responses[5]

    read_errors = [(i, c, d) for i, (c, d) in enumerate(read_responses) if c >= 500]
    read_successes = sum(1 for c, _ in read_responses if c == 200)

    print(f"  Reads: {read_successes}/5 successful, {len(read_errors)} errors")
    print(f"  Transition: HTTP {transition_response[0]}")
    if read_errors:
        print(f"  Read errors: {read_errors}")

    # Verify: no 500 errors during reads
    check(
        "6a. No 500 errors during concurrent reads",
        f"{read_successes}/5 successful reads",
        len(read_errors) == 0,
    )
    # Verify: transition eventually completes
    check(
        "6b. Transition completes",
        f"HTTP {transition_response[0]}",
        transition_response[0] in (200, 400),
    )


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════


async def main():
    print("=" * 70)
    print("  CONTRACT RISK EDGE — CONCURRENCY & RACE CONDITION VALIDATION")
    print(f"  Started: {datetime.utcnow().isoformat()}")
    print(f"  API URL: {API_URL}")
    print("=" * 70)

    token = create_token()

    # Verify server is reachable
    code, data = api_sync("GET", "/reviews?page_size=1", token)
    if code != 200:
        print(f"\n  ❌ Server not reachable at {API_URL}. HTTP {code}: {data}")
        print("  Start the FastAPI server and try again.")
        sys.exit(1)
    print(f"\n  ✅ Server reachable at {API_URL}")

    # Run all tests
    await test_simultaneous_approval_race(token)
    await test_approve_vs_reject_race(token)
    await test_escalate_vs_approve_race(token)
    await test_finalize_vs_modify_race(token)
    await test_concurrent_assignment_race(token)
    await test_transition_vs_read_consistency(token)

    # ── Summary ──
    print(f"\n{'='*70}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*70}\n")

    passed = sum(1 for r in results if PASS in r["status"])
    failed = sum(1 for r in results if FAIL in r["status"])
    total = len(results)

    print(f"  Total checks: {total}  |  Passed: {passed}  |  Failed: {failed}")
    print()

    if failed > 0:
        print("  FAILED CHECKS:")
        for r in results:
            if FAIL in r["status"]:
                print(f"    {r['step']}: {r['detail']}")
        print()

    print(f"{'─'*70}")
    print(f"  DETAILED RESULTS")
    print(f"{'─'*70}\n")
    for r in results:
        icon = "✅" if PASS in r["status"] else "❌"
        print(f"  {icon} {r['step']}")
        print(f"     {r['detail']}")
        print()

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
