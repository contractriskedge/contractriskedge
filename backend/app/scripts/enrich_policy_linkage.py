"""
Backfill policy linkage on review findings and create policy evaluations.

Run after seed_policy_data and when reviews already have findings:
  cd backend && PYTHONPATH=. .venv/bin/python -m app.scripts.enrich_policy_linkage
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text as sa_text

from app.database import get_async_session
from app.domains.ai.repository import AIRepository
from app.domains.review.repository import ReviewRepository
from app.domains.review.service import ReviewService
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext

TENANT_ID = "00000000-0000-4000-8000-000000000001"


async def enrich() -> None:
    async with get_async_session() as session:
        repo = ReviewRepository(session, tenant_id=TENANT_ID)
        service = ReviewService(
            review_repo=repo,
            ai_repo=AIRepository(session, tenant_id=TENANT_ID),
            event_bus=EventBus(),
            user=UserContext(
                id="system",
                email="system@contractedge.local",
                tenant_id=TENANT_ID,
                role="admin",
            ),
            tenant_id=TENANT_ID,
        )

        result = await session.execute(
            sa_text("""
                SELECT DISTINCT cr.review_id::text
                FROM contract_reviews cr
                JOIN review_findings rf ON rf.review_id = cr.review_id
                WHERE cr.tenant_id = :tenant_id
            """),
            {"tenant_id": TENANT_ID},
        )
        review_ids = [row[0] for row in result.fetchall()]
        print(f"Enriching policy linkage for {len(review_ids)} reviews…")

        linked = 0
        for review_id in review_ids:
            await service._sync_review_policy_linkage(review_id)
            r = await session.execute(
                sa_text("""
                    SELECT COUNT(*) FROM review_findings
                    WHERE tenant_id = :tenant_id AND review_id = CAST(:review_id AS uuid)
                      AND rule_id IS NOT NULL
                """),
                {"tenant_id": TENANT_ID, "review_id": review_id},
            )
            linked += r.scalar() or 0

        await session.commit()
        print(f"✅ Done — {linked} findings now have policy rule linkage")


if __name__ == "__main__":
    asyncio.run(enrich())
