"""Sprint 23 Task 3.2A — Review Data Integrity Audit."""
import asyncio
import sqlalchemy as sa
from app.kernel.database.session import TenantAwareSessionFactory
from app.config import settings


async def audit():
    factory = TenantAwareSessionFactory(database_url=settings.database_url)
    async with await factory.create_session(
        tenant_id="system", user_id="system", user_role="admin"
    ) as session:

        # Get column info
        for tbl in ["review_findings", "review_redlines", "contract_reviews"]:
            r = await session.execute(
                sa.text(
                    f"SELECT column_name, data_type FROM information_schema.columns "
                    f"WHERE table_name='{tbl}' ORDER BY ordinal_position"
                )
            )
            cols = [(row[0], row[1]) for row in r]
            print(f"{tbl}:")
            for c in cols:
                print(f"  {c[0]:30s} {c[1]}")
            print()

        # Row counts
        print("=== ROW COUNTS ===")
        for t in [
            "contract_reviews",
            "review_findings",
            "review_redlines",
            "ai_findings",
            "ai_redlines",
        ]:
            r = await session.execute(sa.text(f"SELECT COUNT(*) FROM {t}"))
            print(f"  {t:30s} {r.scalar():>6d}")

        # finding_count vs actual
        print("\n=== finding_count vs actual review_findings ===")
        r = await session.execute(
            sa.text(
                "SELECT r.review_id::text, r.finding_count, COUNT(rf.finding_id)::int "
                "FROM contract_reviews r "
                "LEFT JOIN review_findings rf ON rf.review_id = r.review_id "
                "GROUP BY r.review_id, r.finding_count "
                "HAVING r.finding_count != COUNT(rf.finding_id) "
                "ORDER BY ABS(r.finding_count - COUNT(rf.finding_id)) DESC "
                "LIMIT 20"
            )
        )
        rows = r.fetchall()
        if rows:
            total_delta = 0
            for row in rows:
                delta = row[1] - row[2]
                total_delta += abs(delta)
                print(f"  {row[0][:36]:36s} claimed={row[1]} actual={row[2]} delta={delta:+d}")
            print(f"  Total mismatched: {len(rows)}, Total delta: {total_delta}")
        else:
            print("  ✅ All match")

        # redline_count vs actual
        print("\n=== redline_count vs actual review_redlines ===")
        r = await session.execute(
            sa.text(
                "SELECT r.review_id::text, r.redline_count, COUNT(rl.redline_id)::int "
                "FROM contract_reviews r "
                "LEFT JOIN review_redlines rl ON rl.review_id = r.review_id "
                "GROUP BY r.review_id, r.redline_count "
                "HAVING r.redline_count != COUNT(rl.redline_id) "
                "ORDER BY ABS(r.redline_count - COUNT(rl.redline_id)) DESC "
                "LIMIT 20"
            )
        )
        rows = r.fetchall()
        if rows:
            for row in rows:
                delta = row[1] - row[2]
                print(f"  {row[0][:36]:36s} claimed={row[1]} actual={row[2]} delta={delta:+d}")
            print(f"  Total mismatched: {len(rows)}")
        else:
            print("  ✅ All match")

        # Orphans
        print("\n=== ORPHANS ===")
        for t in ["review_findings", "review_redlines", "ai_findings", "ai_redlines"]:
            r = await session.execute(
                sa.text(
                    f"SELECT COUNT(*) FROM {t} t "
                    f"LEFT JOIN contract_reviews r ON r.review_id = t.review_id "
                    f"WHERE r.review_id IS NULL"
                )
            )
            print(f"  {t:30s} orphans: {r.scalar()}")

        # Phantom findings
        print("\n=== PHANTOM FINDINGS (claimed>0, none in review_findings) ===")
        r = await session.execute(
            sa.text(
                "SELECT COUNT(*) FROM contract_reviews "
                "WHERE finding_count > 0 "
                "AND NOT EXISTS (SELECT 1 FROM review_findings rf WHERE rf.review_id = contract_reviews.review_id)"
            )
        )
        print(f"  Phantom: {r.scalar()}")

        # AI import gap
        print("\n=== AI FINDINGS IMPORT GAP ===")
        r = await session.execute(
            sa.text(
                "SELECT af.review_id::text, COUNT(af.id)::int, COUNT(rf.finding_id)::int "
                "FROM ai_findings af "
                "LEFT JOIN review_findings rf ON rf.review_id = af.review_id "
                "GROUP BY af.review_id "
                "HAVING COUNT(af.id) != COUNT(rf.finding_id) "
                "ORDER BY COUNT(af.id) DESC "
                "LIMIT 10"
            )
        )
        rows = r.fetchall()
        if rows:
            for row in rows:
                gap = row[1] - row[2]
                print(f"  {row[0][:36]:36s} ai={row[1]} imported={row[2]} gap={gap:+d}")
        else:
            print("  ✅ All ai_findings match review_findings")

        # Reviews without AI
        print("\n=== REVIEWS WITHOUT AI ANALYSIS ===")
        r = await session.execute(
            sa.text(
                "SELECT COUNT(*) FROM contract_reviews "
                "WHERE NOT EXISTS (SELECT 1 FROM ai_findings af WHERE af.review_id = contract_reviews.review_id) "
                "AND NOT EXISTS (SELECT 1 FROM ai_redlines ar WHERE ar.review_id = contract_reviews.review_id) "
                "AND status NOT IN ('draft')"
            )
        )
        print(f"  Without AI: {r.scalar()}")

        # Distribution
        print("\n=== FINDING COUNT DISTRIBUTION ===")
        r = await session.execute(
            sa.text(
                "SELECT finding_count, COUNT(*)::int "
                "FROM contract_reviews "
                "GROUP BY finding_count "
                "ORDER BY finding_count"
            )
        )
        for row in r:
            print(f"  count={row[0]:>3d}  reviews={row[1]:>4d}")

        # Asymmetric
        print("\n=== ASYMMETRIC (findings xor redlines) ===")
        r = await session.execute(
            sa.text(
                "SELECT COUNT(*) FROM contract_reviews "
                "WHERE (finding_count > 0 AND redline_count = 0) "
                "OR (finding_count = 0 AND redline_count > 0)"
            )
        )
        print(f"  Asymmetric: {r.scalar()}")

        # NULL risk with findings
        print("\n=== NULL RISK WITH FINDINGS ===")
        r = await session.execute(
            sa.text(
                "SELECT COUNT(*) FROM contract_reviews "
                "WHERE risk_score IS NULL AND finding_count > 0"
            )
        )
        print(f"  NULL risk with findings: {r.scalar()}")

        # Deep dive: show sample of reviews with mismatched counts
        print("\n=== DEEP DIVE: Mismatched reviews (sample) ===")
        r = await session.execute(
            sa.text(
                "SELECT r.review_id::text, r.document_name, r.status, "
                "r.finding_count, r.redline_count, r.risk_score::text, "
                "(SELECT COUNT(*) FROM review_findings rf WHERE rf.review_id = r.review_id)::int as actual_f, "
                "(SELECT COUNT(*) FROM review_redlines rl WHERE rl.review_id = r.review_id)::int as actual_r "
                "FROM contract_reviews r "
                "WHERE r.finding_count != (SELECT COUNT(*) FROM review_findings rf WHERE rf.review_id = r.review_id) "
                "OR r.redline_count != (SELECT COUNT(*) FROM review_redlines rl WHERE rl.review_id = r.review_id) "
                "ORDER BY r.created_at DESC "
                "LIMIT 15"
            )
        )
        rows = r.fetchall()
        if rows:
            print(f"  {'review_id':36s} {'status':20s} {'claimF':>6s} {'actualF':>6s} {'claimR':>6s} {'actualR':>6s} {'risk'}")
            print(f"  {'-'*36} {'-'*20} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
            for row in rows:
                print(f"  {row[0][:36]:36s} {row[2][:20]:20s} {row[3]:>6d} {row[6]:>6d} {row[4]:>6d} {row[7]:>6d} {row[5]}")
        else:
            print("  ✅ All counts match")

        # Check the _import_ai_findings logic
        print("\n=== IMPORT STATUS ===")
        r = await session.execute(
            sa.text(
                "SELECT COUNT(*) FROM ai_findings af "
                "WHERE NOT EXISTS (SELECT 1 FROM review_findings rf WHERE rf.review_id = af.review_id)"
            )
        )
        print(f"  ai_findings not in review_findings: {r.scalar()}")

        r = await session.execute(
            sa.text(
                "SELECT COUNT(*) FROM ai_redlines ar "
                "WHERE NOT EXISTS (SELECT 1 FROM review_redlines rr WHERE rr.review_id = ar.review_id)"
            )
        )
        print(f"  ai_redlines not in review_redlines: {r.scalar()}")


asyncio.run(audit())
