"""Sprint 18 Phase 2 — E2E API tests for negotiation endpoints."""

import asyncio
import httpx

BASE = "http://127.0.0.1:8000/api/v1/negotiations"


async def test():
    async with httpx.AsyncClient() as client:
        print("=== SPRINT 18 PHASE 2 — E2E API TESTS ===")
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

        # 1. KPIs
        r = await client.get(f"{BASE}/kpis")
        if r.status_code == 200:
            ok("GET /kpis")
        else:
            fail("GET /kpis", r.status_code)

        # 2. List sessions
        r = await client.get(f"{BASE}/")
        if r.status_code == 200:
            data = r.json()
            ok(f'GET / — {data["pagination"]["total"]} sessions')
        else:
            fail("GET /", r.status_code)

        # 3. Get seeded session
        r = await client.get(f"{BASE}/")
        sessions = r.json()["data"]
        if sessions:
            sid = sessions[0]["id"]
            r = await client.get(f"{BASE}/{sid}")
            if r.status_code == 200:
                s = r.json()
                ok(
                    f'GET /{sid[:8]} — stage={s["stage"]} '
                    f'versions={len(s["versions"])} '
                    f'redlines={len(s["redlines"])} '
                    f'issues={len(s["issues"])} '
                    f'participants={len(s["participants"])}'
                )
            else:
                fail(f"GET /{sid[:8]}", r.status_code)

            # 4. List redlines
            r = await client.get(f"{BASE}/{sid}/redlines")
            if r.status_code == 200:
                ok(f'GET /{sid[:8]}/redlines — {len(r.json())} redlines')
            else:
                fail("GET redlines", r.status_code)

            # 5. List issues
            r = await client.get(f"{BASE}/{sid}/issues")
            if r.status_code == 200:
                ok(f'GET /{sid[:8]}/issues — {len(r.json())} issues')
            else:
                fail("GET issues", r.status_code)

            # 6. List participants
            r = await client.get(f"{BASE}/{sid}/participants")
            if r.status_code == 200:
                ok(f'GET /{sid[:8]}/participants — {len(r.json())} participants')
            else:
                fail("GET participants", r.status_code)

            # 7. List comments
            r = await client.get(f"{BASE}/{sid}/comments")
            if r.status_code == 200:
                ok(f'GET /{sid[:8]}/comments — {len(r.json())} comments')
            else:
                fail("GET comments", r.status_code)

            # 8. Activities
            r = await client.get(f"{BASE}/{sid}/activities")
            if r.status_code == 200:
                ok(f'GET /{sid[:8]}/activities — {len(r.json())} events')
            else:
                fail("GET activities", r.status_code)

            # 9. Create redline
            r = await client.post(
                f"{BASE}/{sid}/redlines",
                json={
                    "clauseId": "c4",
                    "type": "modification",
                    "title": "Test redline via API",
                    "originalText": "Old text",
                    "modifiedText": "New text",
                },
            )
            if r.status_code == 201:
                rl_id = r.json()["id"]
                ok(f"POST /{sid[:8]}/redlines — created {rl_id[:8]}")

                # 10. Update redline status
                r = await client.patch(
                    f"{BASE}/{sid}/redlines/{rl_id}",
                    json={"status": "accepted"},
                )
                if r.status_code == 200:
                    ok(f'PATCH redline — status={r.json()["status"]}')
                else:
                    fail("PATCH redline", r.status_code)
            else:
                fail("POST redline", r.status_code)

            # 11. Create issue
            r = await client.post(
                f"{BASE}/{sid}/issues",
                json={
                    "clauseId": "c4",
                    "title": "Test issue via API",
                    "description": "Testing issue creation",
                    "severity": "major",
                    "category": "legal",
                },
            )
            if r.status_code == 201:
                iss_id = r.json()["id"]
                ok(f"POST /{sid[:8]}/issues — created {iss_id[:8]}")

                # 12. Update issue
                r = await client.patch(
                    f"{BASE}/{sid}/issues/{iss_id}",
                    json={"status": "in_review"},
                )
                if r.status_code == 200:
                    ok(f'PATCH issue — status={r.json()["status"]}')
                else:
                    fail("PATCH issue", r.status_code)
            else:
                fail("POST issue", r.status_code)

            # 13. Create comment
            r = await client.post(
                f"{BASE}/{sid}/comments",
                json={
                    "clauseId": "c1",
                    "content": "Test comment via API",
                    "mentions": ["Sarah Chen"],
                },
            )
            if r.status_code == 201:
                cmt_id = r.json()["id"]
                ok(f"POST /{sid[:8]}/comments — created {cmt_id[:8]}")

                # 14. Resolve comment
                r = await client.patch(
                    f"{BASE}/{sid}/comments/{cmt_id}/resolve"
                )
                if r.status_code == 200:
                    ok(f'PATCH comment resolve — status={r.json()["status"]}')
                else:
                    fail("PATCH comment resolve", r.status_code)
            else:
                fail("POST comment", r.status_code)

            # 15. Add participant
            r = await client.post(
                f"{BASE}/{sid}/participants",
                json={
                    "name": "API Test User",
                    "role": "reviewer",
                    "department": "Engineering",
                },
            )
            if r.status_code == 201:
                pid = r.json()["id"]
                ok(f'POST /{sid[:8]}/participants — added {r.json()["name"]}')

                # 16. Update participant role
                r = await client.patch(
                    f"{BASE}/{sid}/participants/{pid}",
                    json={"role": "approver"},
                )
                if r.status_code == 200:
                    ok(f'PATCH participant — role={r.json()["role"]}')
                else:
                    fail("PATCH participant", r.status_code)

                # 17. Remove participant
                r = await client.delete(f"{BASE}/{sid}/participants/{pid}")
                if r.status_code == 204:
                    ok("DELETE participant — 204")
                else:
                    fail("DELETE participant", r.status_code)
            else:
                fail("POST participant", r.status_code)

            # 18. Update session stage
            r = await client.patch(f"{BASE}/{sid}", json={"stage": "approved"})
            if r.status_code == 200:
                ok(f'PATCH /{sid[:8]} — stage={r.json()["stage"]}')
            else:
                fail("PATCH session stage", r.status_code)

        # 19. Create new session
        r = await client.post(
            f"{BASE}/",
            json={
                "contractTitle": "E2E Test Contract",
                "counterparty": "E2E Corp",
                "clauses": [
                    {
                        "clauseId": "c1",
                        "title": "Test",
                        "sectionNumber": "1",
                        "content": "Test",
                        "riskLevel": "low",
                        "category": "general",
                    }
                ],
            },
        )
        if r.status_code == 201:
            new_id = r.json()["id"]
            ok(f"POST / — created {new_id[:8]}")

            # 20. Delete new session
            r = await client.delete(f"{BASE}/{new_id}")
            if r.status_code == 204:
                ok(f"DELETE /{new_id[:8]} — 204")
            else:
                fail("DELETE session", r.status_code)
        else:
            fail("POST /", r.status_code)

        print()
        print(f"=== RESULTS: {passed} passed, {failed} failed ===")


asyncio.run(test())
