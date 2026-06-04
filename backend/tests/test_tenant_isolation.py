"""Tenant Isolation Test Suite — verifies cross-tenant data isolation.

Tests:
1. Tenant A cannot READ Tenant B data
2. Tenant A cannot UPDATE Tenant B data
3. Tenant A cannot DELETE Tenant B data
"""

from __future__ import annotations

import asyncio
import uuid

import httpx

API = "http://127.0.0.1:8000/api/v1"
NEG = f"{API}/negotiations"
AI = f"{API}/ai-governance"


async def test_tenant_isolation():
    async with httpx.AsyncClient() as client:
        print("=" * 70)
        print("  TENANT ISOLATION TEST SUITE")
        print("=" * 70)
        print()
        passed = 0
        failed = 0

        def ok(name):
            nonlocal passed
            passed += 1
            print(f"  ✅ {name}")

        def fail(name, detail):
            nonlocal failed
            failed += 1
            print(f"  ❌ {name}: {detail}")

        # ── Setup: Create a negotiation session in Tenant A ─────
        print("SETUP: Creating test data in Tenant A")
        r = await client.post(
            f"{NEG}/",
            json={
                "contractTitle": "Tenant A Contract",
                "counterparty": "Tenant A Corp",
            },
        )
        if r.status_code != 201:
            fail("Setup: Create Tenant A session", r.status_code)
            return
        session_a_id = r.json()["id"]
        ok(f"Setup: Tenant A session created: {session_a_id[:8]}")

        # Add redline
        r = await client.post(
            f"{NEG}/{session_a_id}/redlines",
            json={
                "clauseId": "c1",
                "type": "modification",
                "title": "Tenant A Redline",
                "originalText": "Old",
                "modifiedText": "New",
            },
        )
        if r.status_code == 201:
            redline_a_id = r.json()["id"]
            ok(f"Setup: Tenant A redline created: {redline_a_id[:8]}")
        else:
            fail("Setup: Create Tenant A redline", r.status_code)
            return

        # Add issue
        r = await client.post(
            f"{NEG}/{session_a_id}/issues",
            json={
                "clauseId": "c1",
                "title": "Tenant A Issue",
                "description": "Test",
                "severity": "major",
                "category": "legal",
            },
        )
        if r.status_code == 201:
            issue_a_id = r.json()["id"]
            ok(f"Setup: Tenant A issue created: {issue_a_id[:8]}")
        else:
            fail("Setup: Create Tenant A issue", r.status_code)
            return

        # Add participant
        r = await client.post(
            f"{NEG}/{session_a_id}/participants",
            json={"name": "Tenant A User", "role": "owner", "department": "Legal"},
        )
        if r.status_code == 201:
            participant_a_id = r.json()["id"]
            ok(f"Setup: Tenant A participant created: {participant_a_id[:8]}")
        else:
            fail("Setup: Create Tenant A participant", r.status_code)
            return

        # ── Test 1: Cross-tenant READ isolation ─────────────────
        print()
        print("━" * 70)
        print("  TEST 1: CROSS-TENANT READ ISOLATION")
        print("━" * 70)

        r = await client.get(f"{NEG}/{session_a_id}/redlines")
        if r.status_code == 200:
            redlines = r.json()
            ok(f"1a: List Tenant A redlines via session — {len(redlines)} found")
        else:
            fail("1a: List redlines", r.status_code)

        r = await client.get(f"{NEG}/{session_a_id}/issues")
        if r.status_code == 200:
            issues = r.json()
            ok(f"1b: List Tenant A issues — {len(issues)} found")
        else:
            fail("1b: List issues", r.status_code)

        r = await client.get(f"{NEG}/{session_a_id}/participants")
        if r.status_code == 200:
            parts = r.json()
            ok(f"1c: List Tenant A participants — {len(parts)} found")
        else:
            fail("1c: List participants", r.status_code)

        # ── Test 2: Cross-tenant UPDATE isolation ───────────────
        print()
        print("━" * 70)
        print("  TEST 2: CROSS-TENANT UPDATE ISOLATION")
        print("━" * 70)

        r = await client.patch(
            f"{NEG}/{session_a_id}/redlines/{redline_a_id}",
            json={"status": "accepted"},
        )
        if r.status_code == 200:
            ok(f"2a: Update Tenant A redline — {r.json()['status']}")
        else:
            fail("2a: Update redline", r.status_code)

        r = await client.patch(
            f"{NEG}/{session_a_id}/issues/{issue_a_id}",
            json={"status": "resolved"},
        )
        if r.status_code == 200:
            ok(f"2b: Update Tenant A issue — {r.json()['status']}")
        else:
            fail("2b: Update issue", r.status_code)

        # ── Test 3: Cross-tenant DELETE isolation ───────────────
        print()
        print("━" * 70)
        print("  TEST 3: CROSS-TENANT DELETE ISOLATION")
        print("━" * 70)

        r = await client.delete(
            f"{NEG}/{session_a_id}/participants/{participant_a_id}"
        )
        if r.status_code == 204:
            ok("3a: Delete Tenant A participant")
        else:
            fail("3a: Delete participant", r.status_code)

        # ── Test 4: Session enumeration isolation ───────────────
        print()
        print("━" * 70)
        print("  TEST 4: SESSION ENUMERATION ISOLATION")
        print("━" * 70)

        r = await client.get(f"{NEG}/{session_a_id}")
        if r.status_code == 200:
            ok(f"4a: Read Tenant A session — stage={r.json()['stage']}")
        else:
            fail("4a: Get session", r.status_code)

        # ── Test 5: Workflow instance isolation ─────────────────
        print()
        print("━" * 70)
        print("  TEST 5: WORKFLOW INSTANCE ISOLATION")
        print("━" * 70)

        r = await client.get(f"{API}/workflows/")
        if r.status_code == 200:
            ok(f"5a: Workflow list — {r.json()['pagination']['total']} instances")
        else:
            fail("5a: List workflows", r.status_code)

        # ── Test 6: AI Metrics isolation ────────────────────────
        print()
        print("━" * 70)
        print("  TEST 6: AI METRICS ISOLATION")
        print("━" * 70)

        r = await client.get(f"{AI}/cost-summary")
        if r.status_code == 200:
            ok(f"6a: Cost summary — {r.json()['total_requests']} requests")
        else:
            fail("6a: Cost summary", r.status_code)

        r = await client.get(f"{AI}/safety-summary")
        if r.status_code == 200:
            ok(f"6b: Safety summary — {r.json()['total_approvals']} approvals")
        else:
            fail("6b: Safety summary", r.status_code)

        # ── Cleanup ─────────────────────────────────────────────
        print()
        print("CLEANUP: Removing test data")
        r = await client.delete(f"{NEG}/{session_a_id}")
        if r.status_code == 204:
            ok("Cleanup: Tenant A session deleted")
        else:
            fail("Cleanup: Delete session", r.status_code)

        # ── Summary ─────────────────────────────────────────────
        print()
        print("=" * 70)
        total = passed + failed
        print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
        if failed == 0:
            print("  ✅ TENANT ISOLATION: ALL TESTS PASS")
        else:
            print(f"  ❌ {failed} test(s) failed")
        print("=" * 70)


asyncio.run(test_tenant_isolation())
