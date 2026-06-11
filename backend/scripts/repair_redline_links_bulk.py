#!/usr/bin/env python3
"""Bulk repair: re-link redlines to findings by matching clause_type.

Fixes reviews where chunk-overlap linked every redline to the wrong finding
(e.g. all NDA inserts attached to the confidentiality finding).

Usage:
  python scripts/repair_redline_links_bulk.py              # dry-run report
  python scripts/repair_redline_links_bulk.py --apply      # apply fixes
  python scripts/repair_redline_links_bulk.py --review-id <uuid> --apply
"""

from __future__ import annotations

import argparse
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def run(review_id: str | None, apply: bool) -> None:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev",
    )
    if dsn.startswith("postgresql://"):
        dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(dsn)
    review_filter = "AND rl.review_id = CAST(:review_id AS uuid)" if review_id else ""
    params: dict = {}
    if review_id:
        params["review_id"] = review_id

    async with engine.connect() as conn:
        # Mismatched: redline clause_type != linked finding clause_type
        mismatched = await conn.execute(
            text(f"""
                SELECT rl.redline_id::text, rl.review_id::text, rl.clause_type AS redline_ct,
                       rf.clause_type AS finding_ct, rf.title, rl.status,
                       us.filename
                FROM review_redlines rl
                JOIN review_findings rf ON rf.finding_id = rl.finding_id
                JOIN contract_reviews cr ON cr.review_id = rl.review_id
                JOIN upload_sessions us ON us.upload_id = cr.upload_id
                WHERE rl.finding_id IS NOT NULL
                  AND lower(replace(rl.clause_type, '-', '_'))
                      != lower(replace(rf.clause_type, '-', '_'))
                  {review_filter}
                ORDER BY us.filename, rl.clause_type
            """),
            params,
        )
        rows = mismatched.fetchall()
        print(f"Mismatched redline↔finding links: {len(rows)}")
        for r in rows:
            print(
                f"  {r.filename[:40]:40s}  redline={r.redline_ct:22s}  "
                f"finding={r.finding_ct:22s}  status={r.status}"
            )

        invalid = await conn.execute(
            text(f"""
                SELECT count(*) FROM review_redlines rl
                WHERE status = 'invalid_mapping' {review_filter.replace('rl.', '') if review_filter else ''}
            """),
            params,
        )
        print(f"\nRedlines with status=invalid_mapping: {invalid.scalar()}")

        if not apply:
            print("\nDry run only. Pass --apply to re-link by clause_type and reset status to proposed.")
            await engine.dispose()
            return

        if not rows:
            print("\nNothing to repair.")
            await engine.dispose()
            return

        print("\nApplying repairs...")
        async with engine.begin() as tx:
            result = await tx.execute(
                text(f"""
                    UPDATE review_redlines rl
                    SET finding_id = rf.finding_id,
                        status = 'proposed'
                    FROM review_findings rf
                    WHERE rl.review_id = rf.review_id
                      AND lower(replace(rl.clause_type, '-', '_'))
                          = lower(replace(rf.clause_type, '-', '_'))
                      AND (
                        rl.finding_id IS NULL
                        OR rl.finding_id != rf.finding_id
                      )
                      {review_filter}
                """),
                params,
            )
            print(f"Updated {result.rowcount} redline row(s)")

            remaining = await tx.execute(
                text(f"""
                    SELECT count(*) FROM review_redlines rl
                    JOIN review_findings rf ON rf.finding_id = rl.finding_id
                    WHERE lower(replace(rl.clause_type, '-', '_'))
                        != lower(replace(rf.clause_type, '-', '_'))
                      {review_filter}
                """),
                params,
            )
            print(f"Remaining mismatches after repair: {remaining.scalar()}")

            still_invalid = await tx.execute(
                text(f"""
                    SELECT count(*) FROM review_redlines
                    WHERE status = 'invalid_mapping'
                    {('AND review_id = CAST(:review_id AS uuid)' if review_id else '')}
                """),
                params,
            )
            print(f"Still invalid_mapping: {still_invalid.scalar()}")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply repairs (default: dry-run)")
    parser.add_argument("--review-id", help="Limit to one review")
    args = parser.parse_args()
    asyncio.run(run(args.review_id, args.apply))


if __name__ == "__main__":
    main()
