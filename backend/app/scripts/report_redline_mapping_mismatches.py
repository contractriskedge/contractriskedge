#!/usr/bin/env python3
"""Report and optionally repair redlines with invalid finding mappings.

Usage:
  python -m app.scripts.report_redline_mapping_mismatches
  python -m app.scripts.report_redline_mapping_mismatches --repair
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from sqlalchemy import select

from app.domains.review.mapping_validation import validate_redline_finding_mapping
from app.domains.review.models import RedlineStatus, ReviewFinding, ReviewRedline
from app.database import get_async_session


async def run(repair: bool = False) -> int:
    mismatches: list[dict] = []
    total_checked = 0
    async with get_async_session() as session:
        result = await session.execute(select(ReviewRedline))
        redlines = result.scalars().all()
        total_checked = len(redlines)
        finding_ids = [r.finding_id for r in redlines if r.finding_id]
        findings_by_id: dict[str, ReviewFinding] = {}
        if finding_ids:
            f_result = await session.execute(
                select(ReviewFinding).where(ReviewFinding.finding_id.in_(finding_ids))
            )
            findings_by_id = {
                str(f.finding_id): f for f in f_result.scalars().all()
            }

        for redline in redlines:
            linked = (
                findings_by_id.get(str(redline.finding_id))
                if redline.finding_id
                else None
            )
            mapping = validate_redline_finding_mapping(redline, linked)
            if mapping.valid:
                continue
            entry = {
                "redline_id": str(redline.redline_id),
                "review_id": str(redline.review_id),
                "status": str(redline.status.value if hasattr(redline.status, "value") else redline.status),
                "finding_id": mapping.finding_id,
                "finding_title": mapping.finding_title,
                "finding_category": mapping.finding_category,
                "redline_title": mapping.redline_title,
                "redline_category": mapping.redline_category,
                "warning": mapping.warning,
            }
            mismatches.append(entry)
            if repair:
                redline.status = RedlineStatus.INVALID_MAPPING

        if repair and mismatches:
            await session.commit()

    report = {
        "total_redlines_checked": total_checked,
        "invalid_mapping_count": len(mismatches),
        "mismatches": mismatches,
    }
    print(json.dumps(report, indent=2))
    return 1 if mismatches else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Set status=invalid_mapping on mismatched redlines",
    )
    args = parser.parse_args()
    code = asyncio.run(run(repair=args.repair))
    sys.exit(code)


if __name__ == "__main__":
    main()
