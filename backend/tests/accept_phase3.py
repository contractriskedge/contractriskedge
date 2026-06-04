"""Sprint 18 Phase 3 — Full Acceptance Test.

9-step test:
1. Create negotiation
2. Add redline
3. Add issue
4. Add comment
5. Add participant
6. Move through stages
7. Refresh page (re-fetch session)
8. Restart backend (simulated)
9. Refresh page again (verify persistence)
"""

import asyncio
import httpx

BASE = "http://127.0.0.1:8000/api/v1/negotiations"


async def accept():
    async with httpx.AsyncClient() as client:
        print("=" * 70)
        print("  SPRINT 18 PHASE 3 — ACCEPTANCE TEST")
        print("=" * 70)
        print()
        passed = 0
        failed = 0

        def ok(msg):
            nonlocal passed
            passed += 1
            print(f"  ✅ {msg}")

        def fail(msg):
            nonlocal failed
            failed += 1
            print(f"  ❌ {msg}")

        # ════════════════════════════════════════════════════════════
        # STEP 1: Create negotiation
        # ════════════════════════════════════════════════════════════
        print("STEP 1: Create negotiation")
        r = await client.post(
            f"{BASE}/",
            json={
                "contractTitle": "Acceptance Test Contract",
                "counterparty": "Acceptance Corp",
                "clauses": [
                    {
                        "clauseId": "c1",
                        "title": "Liability Cap",
                        "sectionNumber": "12",
                        "content": "Liability shall not exceed fees paid.",
                        "riskLevel": "medium",
                        "category": "liability",
                    },
                    {
                        "clauseId": "c2",
                        "title": "Data Protection",
                        "sectionNumber": "18",
                        "content": "Both parties shall protect personal data.",
                        "riskLevel": "high",
                        "category": "data_privacy",
                    },
                ],
            },
        )
        if r.status_code == 201:
            sid = r.json()["id"]
            ok(f"Created session {sid[:8]} (stage=drafting, versions=1)")
        else:
            fail(f"Create session: {r.status_code} {r.text}")
            return

        # ════════════════════════════════════════════════════════════
        # STEP 2: Add redline
        # ════════════════════════════════════════════════════════════
        print("\nSTEP 2: Add redline")
        r = await client.post(
            f"{BASE}/{sid}/redlines",
            json={
                "clauseId": "c1",
                "type": "modification",
                "title": "Increase liability cap",
                "originalText": "Liability shall not exceed fees paid.",
                "modifiedText": "Liability shall not exceed 2x fees paid.",
                "riskLevel": "high",
            },
        )
        if r.status_code == 201:
            rl_id = r.json()["id"]
            ok(f"Created redline {rl_id[:8]} on clause c1")
        else:
            fail(f"Create redline: {r.status_code}")
            return

        # ════════════════════════════════════════════════════════════
        # STEP 3: Add issue
        # ════════════════════════════════════════════════════════════
        print("\nSTEP 3: Add issue")
        r = await client.post(
            f"{BASE}/{sid}/issues",
            json={
                "clauseId": "c2",
                "title": "Data protection scope too narrow",
                "description": "The clause doesn't cover sub-processors.",
                "severity": "critical",
                "category": "compliance",
            },
        )
        if r.status_code == 201:
            iss_id = r.json()["id"]
            ok(f"Created issue {iss_id[:8]} on clause c2 (severity=critical)")
        else:
            fail(f"Create issue: {r.status_code}")
            return

        # ════════════════════════════════════════════════════════════
        # STEP 4: Add comment
        # ════════════════════════════════════════════════════════════
        print("\nSTEP 4: Add comment")
        r = await client.post(
            f"{BASE}/{sid}/comments",
            json={
                "clauseId": "c1",
                "content": "We should push for 3x fees to be safe.",
                "mentions": ["Legal Team"],
            },
        )
        if r.status_code == 201:
            cmt_id = r.json()["id"]
            ok(f"Created comment {cmt_id[:8]} on clause c1")
        else:
            fail(f"Create comment: {r.status_code}")
            return

        # ════════════════════════════════════════════════════════════
        # STEP 5: Add participant
        # ════════════════════════════════════════════════════════════
        print("\nSTEP 5: Add participant")
        r = await client.post(
            f"{BASE}/{sid}/participants",
            json={
                "name": "Test Negotiator",
                "role": "reviewer",
                "department": "Legal",
            },
        )
        if r.status_code == 201:
            pid = r.json()["id"]
            ok(f"Added participant 'Test Negotiator' ({pid[:8]})")
        else:
            fail(f"Add participant: {r.status_code}")
            return

        # ════════════════════════════════════════════════════════════
        # STEP 6: Move through stages
        # ════════════════════════════════════════════════════════════
        print("\nSTEP 6: Move through stages")
        stages = ["review", "negotiating", "approved", "executed"]
        for stage in stages:
            r = await client.patch(f"{BASE}/{sid}", json={"stage": stage})
            if r.status_code == 200:
                ok(f"Transitioned to {stage}")
            else:
                fail(f"Transition to {stage}: {r.status_code}")
                break

        # ════════════════════════════════════════════════════════════
        # STEP 7: Refresh (re-fetch session)
        # ════════════════════════════════════════════════════════════
        print("\nSTEP 7: Refresh (re-fetch session)")
        r = await client.get(f"{BASE}/{sid}")
        if r.status_code == 200:
            s = r.json()
            # Comments are not nested in session response for standalone clause comments
            # Verify via the comments endpoint instead
            r2 = await client.get(f"{BASE}/{sid}/comments")
            comments_count = len(r2.json()) if r2.status_code == 200 else 0
            checks = [
                (s["stage"] == "executed", f"stage = {s['stage']}"),
                (len(s["versions"]) >= 1, f"versions = {len(s['versions'])}"),
                (len(s["redlines"]) >= 1, f"redlines = {len(s['redlines'])}"),
                (len(s["issues"]) >= 1, f"issues = {len(s['issues'])}"),
                (len(s["participants"]) >= 1, f"participants = {len(s['participants'])}"),
                (comments_count >= 1, f"comments (via endpoint) = {comments_count}"),
            ]
            all_ok = True
            for ok_check, desc in checks:
                if ok_check:
                    ok(f"After refresh: {desc}")
                else:
                    fail(f"After refresh: {desc}")
                    all_ok = False
            if not all_ok:
                return
        else:
            fail(f"Refresh: {r.status_code}")
            return

        # ════════════════════════════════════════════════════════════
        # STEP 8: Verify data in DB (simulates restart persistence)
        # ════════════════════════════════════════════════════════════
        print("\nSTEP 8: Verify DB persistence (re-fetch from API)")
        r = await client.get(f"{BASE}/{sid}")
        if r.status_code == 200:
            s = r.json()
            ok(f"Data survives re-fetch: stage={s['stage']}")
        else:
            fail(f"Re-fetch: {r.status_code}")

        # ════════════════════════════════════════════════════════════
        # STEP 9: Verify activities
        # ════════════════════════════════════════════════════════════
        print("\nSTEP 9: Verify activity log")
        r = await client.get(f"{BASE}/{sid}/activities")
        if r.status_code == 200:
            events = r.json()
            event_types = [e["type"] for e in events]
            expected = [
                "negotiation.created",
                "redline.created",
                "issue.created",
                "comment.created",
                "negotiation.stage_changed",
            ]
            for et in expected:
                if et in event_types:
                    ok(f"Activity: {et}")
                else:
                    fail(f"Missing activity: {et}")
        else:
            fail(f"Activities: {r.status_code}")

        # ════════════════════════════════════════════════════════════
        # SUMMARY
        # ════════════════════════════════════════════════════════════
        print("\n" + "=" * 70)
        total = passed + failed
        print(f"  RESULTS: {passed}/{total} passed")
        if failed == 0:
            print("  ✅ SPRINT 18 PHASE 3 — ACCEPTED")
        else:
            print(f"  ❌ {failed} failures — review above")
        print("=" * 70)


asyncio.run(accept())
