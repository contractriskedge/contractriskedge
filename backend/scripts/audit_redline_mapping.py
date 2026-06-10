"""
Redline Mapping Audit Script.

Audits every redline with a linked finding and reports category mismatches.
Run: python -m scripts.audit_redline_mapping
"""
import asyncio
import os
from collections import Counter
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text as sa_text


def _normalize(cat: str | None) -> str:
    if not cat:
        return ""
    return cat.lower().replace("_", " ").replace("-", " ").strip()


def _is_match(fc: str, rc: str) -> bool:
    if not fc or not rc:
        return True  # can't determine
    if fc == rc:
        return True
    # Handle combined categories (e.g. liability_indemnity ↔ indemnification)
    fc_parts = set(fc.replace("_", " ").replace("-", " ").split())
    rc_parts = set(rc.replace("_", " ").replace("-", " ").split())
    if fc_parts & rc_parts:
        return True
    if len(fc) > 3 and len(rc) > 3:
        if fc in rc or rc in fc:
            return True
    return False


async def audit():
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev",
    )
    engine = create_async_engine(dsn)

    async with engine.connect() as conn:
        rows = await conn.execute(
            sa_text("""
                SELECT
                    rl.review_id,
                    rl.finding_id,
                    rf.clause_type AS finding_category,
                    rf.title AS finding_title,
                    rf.recommendation AS finding_recommendation,
                    rl.redline_id,
                    rl.clause_type AS redline_category,
                    rl.status AS redline_status,
                    rl.created_at
                FROM review_redlines rl
                LEFT JOIN review_findings rf ON rl.finding_id = rf.finding_id
                WHERE rl.finding_id IS NOT NULL
                ORDER BY rl.created_at DESC
            """)
        )
        results = rows.fetchall()

    mismatches = []
    for r in results:
        fc = _normalize(r.finding_category)
        rc = _normalize(r.redline_category)
        if not _is_match(fc, rc):
            mismatches.append(r)

    print("=" * 100)
    print("REDLINE MAPPING AUDIT REPORT")
    print("=" * 100)
    print(f"Total redlines with linked findings: {len(results)}")
    print(f"Mismatches found: {len(mismatches)}")
    print()

    if mismatches:
        print("--- MISMATCHES ---")
        for r in mismatches:
            print(f"  Review: {str(r.review_id)[:8]}...")
            print(f"  Finding: {str(r.finding_id)[:8]}...")
            print(f"    Category: {r.finding_category}")
            print(f"    Title: {r.finding_title}")
            print(f"  Redline: {str(r.redline_id)[:8]}...")
            print(f"    Category: {r.redline_category}")
            print(f"    Status: {r.redline_status}")
            print()

    print("--- SUMMARY BY FINDING CATEGORY ---")
    fc_counts: Counter[str] = Counter()
    for r in results:
        fc_counts[r.finding_category or "NULL"] += 1
    for cat, count in fc_counts.most_common():
        print(f"  {cat}: {count}")

    print()
    print("--- SUMMARY BY REDLINE CATEGORY (mismatched) ---")
    rc_counts: Counter[str] = Counter()
    for r in mismatches:
        rc_counts[r.redline_category or "NULL"] += 1
    for cat, count in rc_counts.most_common():
        print(f"  {cat}: {count}")

    print()
    print("--- ALL REDLINES (first 20) ---")
    for r in results[:20]:
        fc = _normalize(r.finding_category)
        rc = _normalize(r.redline_category)
        status = "OK" if _is_match(fc, rc) else "MISMATCH"
        print(
            f"  [{status}] Finding={r.finding_category or '?'} "
            f"→ Redline={r.redline_category or '?'} "
            f"(Status={r.redline_status})"
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(audit())
