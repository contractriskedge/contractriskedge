#!/usr/bin/env python3
"""Redline coverage audit — findings vs redlines by clause_type.

Usage:
  python scripts/audit_redline_coverage.py
  python scripts/audit_redline_coverage.py --review-id <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def run(review_id: str | None = None) -> dict:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev",
    )
    if dsn.startswith("postgresql://"):
        dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(dsn)
    report: dict = {}

    async with engine.connect() as conn:
        if review_id:
            frows = await conn.execute(
                text("""
                    SELECT finding_id::text, clause_type, severity, title,
                           recommendation IS NOT NULL AND recommendation != '' AS has_rec
                    FROM review_findings WHERE review_id = CAST(:rid AS uuid)
                    ORDER BY created_at
                """),
                {"rid": review_id},
            )
            findings = [dict(r._mapping) for r in frows.fetchall()]
            rrows = await conn.execute(
                text("""
                    SELECT redline_id::text, finding_id::text, clause_type, status
                    FROM review_redlines WHERE review_id = CAST(:rid AS uuid)
                """),
                {"rid": review_id},
            )
            redlines = [dict(r._mapping) for r in rrows.fetchall()]

            from app.domains.review.redline_coverage import audit_finding_redline_coverage

            report = audit_finding_redline_coverage(findings, redlines)
            report["review_id"] = review_id
        else:
            cov = await conn.execute(
                text("""
                    SELECT rf.clause_type,
                           count(*) AS findings,
                           count(rr.redline_id) AS linked_redlines,
                           count(*) - count(rr.redline_id) AS gaps
                    FROM review_findings rf
                    LEFT JOIN review_redlines rr ON rr.finding_id = rf.finding_id
                    GROUP BY rf.clause_type
                    ORDER BY gaps DESC, findings DESC
                """)
            )
            rows = [dict(r._mapping) for r in cov.fetchall()]
            total_f = sum(r["findings"] for r in rows)
            total_linked = sum(r["linked_redlines"] for r in rows)
            report = {
                "scope": "tenant_global",
                "findings": total_f,
                "linked_redlines": total_linked,
                "coverage_pct": round((total_linked / total_f) * 100, 1) if total_f else 100.0,
                "by_clause_type": rows,
                "gaps": [r for r in rows if r["gaps"] > 0],
            }

    await engine.dispose()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-id", help="Audit a single review")
    args = parser.parse_args()
    report = asyncio.run(run(args.review_id))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
