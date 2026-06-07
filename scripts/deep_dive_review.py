"""Deep dive into one affected review."""
import asyncio
import sqlalchemy as sa
from app.kernel.database.session import TenantAwareSessionFactory
from app.config import settings


async def check():
    factory = TenantAwareSessionFactory(database_url=settings.database_url)
    async with await factory.create_session(
        tenant_id="system", user_id="system", user_role="admin"
    ) as session:
        rid = "a7ea3a4f-4025-4127-84ac-e95d383f0867"

        r = await session.execute(
            sa.text(
                "SELECT upload_id, finding_count, redline_count, status "
                "FROM contract_reviews WHERE review_id = :rid"
            ),
            {"rid": rid},
        )
        row = r.fetchone()
        print(f"Review: {rid}")
        print(f"  upload_id: {row[0]}")
        print(f"  finding_count: {row[1]}")
        print(f"  redline_count: {row[2]}")
        print(f"  status: {row[3]}")

        upload_id = str(row[0])

        r = await session.execute(
            sa.text("SELECT COUNT(*) FROM ai_findings WHERE upload_id = :uid"),
            {"uid": upload_id},
        )
        print(f"  ai_findings for this upload: {r.scalar()}")

        r = await session.execute(
            sa.text("SELECT COUNT(*) FROM ai_redlines WHERE upload_id = :uid"),
            {"uid": upload_id},
        )
        print(f"  ai_redlines for this upload: {r.scalar()}")

        r = await session.execute(
            sa.text("SELECT COUNT(*) FROM review_findings WHERE review_id = :rid"),
            {"rid": rid},
        )
        print(f"  review_findings for this review: {r.scalar()}")

        r = await session.execute(
            sa.text("SELECT COUNT(*) FROM review_redlines WHERE review_id = :rid"),
            {"rid": rid},
        )
        print(f"  review_redlines for this review: {r.scalar()}")

        # Find a good review for comparison
        r = await session.execute(
            sa.text(
                "SELECT review_id::text, finding_count FROM contract_reviews "
                "WHERE finding_count > 0 AND EXISTS "
                "(SELECT 1 FROM review_findings rf WHERE rf.review_id = contract_reviews.review_id) "
                "LIMIT 1"
            )
        )
        row = r.fetchone()
        if row:
            print(f"\nGood review: {row[0]} has finding_count={row[1]}")

            # Get its upload_id and compare
            r2 = await session.execute(
                sa.text("SELECT upload_id FROM contract_reviews WHERE review_id = :rid"),
                {"rid": row[0]},
            )
            good_upload = str(r2.fetchone()[0])
            r2 = await session.execute(
                sa.text("SELECT COUNT(*) FROM ai_findings WHERE upload_id = :uid"),
                {"uid": good_upload},
            )
            print(f"  ai_findings for good upload: {r2.scalar()}")


asyncio.run(check())
