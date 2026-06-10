"""
Repair Redline Mapping — sets invalid_mapping status on mismatched redlines.

Run: python -m scripts.repair_redline_mapping
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text as sa_text


def _normalize(cat: str | None) -> str:
    if not cat:
        return ""
    return cat.lower().replace("_", " ").replace("-", " ").strip()


def _is_match(fc: str, rc: str) -> bool:
    """Check if finding category matches redline category.

    Handles combined categories like 'liability_indemnity' which should
    match either 'liability' or 'indemnification'.
    """
    if not fc or not rc:
        return True
    if fc == rc:
        return True
    # Handle combined categories: split both into parts
    fc_parts = set(fc.replace("_", " ").replace("-", " ").split())
    rc_parts = set(rc.replace("_", " ").replace("-", " ").split())
    # If any word overlaps, it's compatible (e.g. liability_indemnity ↔ indemnification)
    if fc_parts & rc_parts:
        return True
    # Check substring containment
    if len(fc) > 3 and len(rc) > 3:
        if fc in rc or rc in fc:
            return True
    return False


async def repair():
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev",
    )
    engine = create_async_engine(dsn)

    async with engine.connect() as conn:
        # Find all mismatched redlines that are NOT already invalid_mapping
        rows = await conn.execute(
            sa_text("""
                SELECT
                    rl.redline_id,
                    rf.clause_type AS finding_category,
                    rl.clause_type AS redline_category,
                    rl.status AS current_status
                FROM review_redlines rl
                JOIN review_findings rf ON rl.finding_id = rf.finding_id
                WHERE rl.finding_id IS NOT NULL
                  AND rl.status NOT IN ('invalid_mapping', 'accepted', 'rejected', 'modified')
                ORDER BY rl.created_at DESC
            """)
        )
        results = rows.fetchall()

        to_fix = []
        for r in results:
            fc = _normalize(r.finding_category)
            rc = _normalize(r.redline_category)
            if not _is_match(fc, rc):
                to_fix.append(r)

        print(f"Redlines to fix (status → invalid_mapping): {len(to_fix)}")
        for r in to_fix:
            print(
                f"  {str(r.redline_id)[:8]}... "
                f"Finding={r.finding_category} → Redline={r.redline_category} "
                f"(current={r.current_status})"
            )

        if to_fix:
            confirm = input("\nApply fixes? (yes/no): ")
            if confirm.lower() == "yes":
                ids = [str(r.redline_id) for r in to_fix]
                # Fix in batches
                batch_size = 20
                for i in range(0, len(ids), batch_size):
                    batch = ids[i : i + batch_size]
                    placeholders = ", ".join(f"'{x}'" for x in batch)
                    await conn.execute(
                        sa_text(f"""
                            UPDATE review_redlines
                            SET status = 'invalid_mapping'
                            WHERE redline_id IN ({placeholders})
                        """)
                    )
                await conn.commit()
                print(f"Updated {len(ids)} redlines to invalid_mapping")
            else:
                print("Skipped.")
        else:
            print("No redlines need fixing.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(repair())
