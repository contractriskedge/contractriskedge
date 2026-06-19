"""
Business ID Service — generates human-readable sequential IDs for all entity types.

Format: {PREFIX}-{YYYYMM}-{SEQUENTIAL}
Examples:
  Finding:   FND-202606-000001
  Policy:    POL-000015
  Playbook:  PB-000008
  Supplier:  SUP-000245 (future)

Usage:
    from app.kernel.utils.business_id import generate_business_id

    finding_id = await generate_business_id(session, tenant_id, "FND")
    # Returns: "FND-202606-000042"
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ── Entity Prefix Registry ────────────────────────────────────────────────

ENTITY_PREFIXES: dict[str, str] = {
    "finding": "FND",
    "policy": "POL",
    "playbook": "PB",
    "supplier": "SUP",
}

# Tables that have a business_id column, mapped by entity type
ENTITY_TABLES: dict[str, str] = {
    "finding": "review_findings",
    "policy": "policy_playbooks",
    "playbook": "policy_playbooks",
}

ENTITY_ID_COLUMNS: dict[str, str] = {
    "finding": "finding_number",
    "policy": "policy_number",
    "playbook": "playbook_number",
}


async def generate_business_id(
    session: AsyncSession,
    tenant_id: str,
    entity_type: str,
    prefix: Optional[str] = None,
    include_month: bool = True,
    seq_width: int = 6,
) -> str:
    """Generate a sequential business ID for any entity type.

    Args:
        session: DB session
        tenant_id: Tenant UUID
        entity_type: Entity type key (e.g. "finding", "policy")
        prefix: Override prefix (defaults from ENTITY_PREFIXES)
        include_month: Whether to include YYYYMM in the ID
        seq_width: Width of the sequential number (zero-padded)

    Returns:
        Business ID string like "FND-202606-000042"

    Raises:
        ValueError: If entity_type is unknown and no prefix given
    """
    if not prefix:
        prefix = ENTITY_PREFIXES.get(entity_type)
        if not prefix:
            raise ValueError(f"Unknown entity type '{entity_type}'. Provide a prefix or register in ENTITY_PREFIXES.")

    now = datetime.utcnow()
    ym = now.strftime("%Y%m") if include_month else ""

    # Use a sequence table for atomic increment
    seq_key = f"{prefix}_{tenant_id}"
    try:
        result = await session.execute(
            text("""
                INSERT INTO business_id_sequences (sequence_key, tenant_id, current_value)
                VALUES (:key, :tid, 1)
                ON CONFLICT (sequence_key) DO UPDATE
                    SET current_value = business_id_sequences.current_value + 1
                RETURNING current_value
            """),
            {"key": seq_key, "tid": tenant_id},
        )
        row = result.fetchone()
        seq = row[0] if row else 1
    except Exception:
        # Fallback if table doesn't exist yet: count existing records
        logger.warning("business_id_sequences table not available, using COUNT fallback")
        table = ENTITY_TABLES.get(entity_type)
        if table and ENTITY_ID_COLUMNS.get(entity_type):
            try:
                col = ENTITY_ID_COLUMNS[entity_type]
                result = await session.execute(
                    text(f"SELECT COUNT(*) + 1 FROM {table} WHERE tenant_id = :tid"),
                    {"tid": tenant_id},
                )
                seq = result.scalar() or 1
            except Exception:
                seq = 1
        else:
            seq = 1

    parts = [prefix]
    if ym:
        parts.append(ym)
    parts.append(f"{seq:0{seq_width}d}")
    return "-".join(parts)
