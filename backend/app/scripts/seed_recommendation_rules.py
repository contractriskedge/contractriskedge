"""Seed clause recommendation rules for the dev tenant.

Run:  python -m app.scripts.seed_recommendation_rules
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text as sa_text

from app.config import settings
from app.kernel.database.sync_session import get_sync_factory

TENANT_ID = "00000000-0000-4000-8000-000000000001"

RULES = [
    # ── Jurisdiction-based ──
    {
        "name": "Jurisdiction is Germany → Data Protection",
        "variable_key": "Jurisdiction", "operator": "=", "condition_value": ["Germany"],
        "clause_type": "data_protection", "recommendation_type": "required", "priority": 100,
    },
    {
        "name": "Jurisdiction is France → Governing Law",
        "variable_key": "Jurisdiction", "operator": "=", "condition_value": ["France"],
        "clause_type": "governing_law", "recommendation_type": "recommended", "priority": 90,
    },
    {
        "name": "Jurisdiction is India → Governing Law",
        "variable_key": "Jurisdiction", "operator": "=", "condition_value": ["India"],
        "clause_type": "governing_law", "recommendation_type": "recommended", "priority": 90,
    },
    {
        "name": "Jurisdiction is UK → Governing Law",
        "variable_key": "Jurisdiction", "operator": "=", "condition_value": ["United Kingdom"],
        "clause_type": "governing_law", "recommendation_type": "recommended", "priority": 90,
    },
    # ── Value-based ──
    {
        "name": "High Value > $1M → Liability Review",
        "variable_key": "ContractValue", "operator": ">", "condition_value": ["1000000"],
        "clause_type": "liability", "recommendation_type": "required", "priority": 100,
    },
    {
        "name": "Medium Value > $250K → Indemnification",
        "variable_key": "ContractValue", "operator": ">", "condition_value": ["250000"],
        "clause_type": "indemnification", "recommendation_type": "recommended", "priority": 80,
    },
    {
        "name": "High Budget > $500K → Liability Review",
        "variable_key": "ProjectBudget", "operator": ">", "condition_value": ["500000"],
        "clause_type": "liability", "recommendation_type": "recommended", "priority": 80,
    },
    {
        "name": "High Fee > $500K → Liability Review",
        "variable_key": "EngagementFee", "operator": ">", "condition_value": ["500000"],
        "clause_type": "liability", "recommendation_type": "recommended", "priority": 80,
    },
    # ── Duration-based ──
    {
        "name": "Long Term ≥ 24 months → Insurance",
        "variable_key": "InitialTerm", "operator": ">=", "condition_value": ["24"],
        "clause_type": "insurance", "recommendation_type": "recommended", "priority": 70,
    },
    {
        "name": "Short Term < 6 months → Fast Payment",
        "variable_key": "InitialTerm", "operator": "<", "condition_value": ["6"],
        "clause_type": "payment", "recommendation_type": "optional", "priority": 50,
    },
    {
        "name": "NDA Long Term > 5yr → Confidentiality",
        "variable_key": "TermYears", "operator": ">=", "condition_value": ["5"],
        "clause_type": "confidentiality", "recommendation_type": "recommended", "priority": 70,
    },
    {
        "name": "Long Engagement ≥ 12mo → Insurance",
        "variable_key": "TermMonths", "operator": ">=", "condition_value": ["12"],
        "clause_type": "insurance", "recommendation_type": "recommended", "priority": 70,
    },
    # ── Payment-based ──
    {
        "name": "Net 60+ → Dispute Resolution",
        "variable_key": "PaymentTerms", "operator": ">=", "condition_value": ["60"],
        "clause_type": "dispute_resolution", "recommendation_type": "recommended", "priority": 70,
    },
    {
        "name": "Net 90+ → Interest Clause",
        "variable_key": "PaymentTerms", "operator": ">=", "condition_value": ["90"],
        "clause_type": "payment", "recommendation_type": "recommended", "priority": 80,
    },
    # ── Data-based ──
    {
        "name": "Delivery Date Set → Warranty",
        "variable_key": "DeliveryDate", "operator": "IS_NOT_EMPTY", "condition_value": [""],
        "clause_type": "warranty", "recommendation_type": "recommended", "priority": 60,
    },
    {
        "name": "Sensitive Data Types → Indemnification",
        "variable_key": "DataTypes", "operator": "IS_NOT_EMPTY", "condition_value": [""],
        "clause_type": "indemnification", "recommendation_type": "recommended", "priority": 80,
    },
]


def seed_rules(dry_run: bool = False) -> int:
    """Seed recommendation rules. Returns count of rules created."""
    from app.kernel.database.sync_session import get_sync_factory

    factory = get_sync_factory()
    session = factory.create_session(tenant_id=TENANT_ID, user_id="system", user_role="admin")

    # Get clause_id mappings
    clause_rows = session.execute(
        sa_text("SELECT id, clause_type FROM template_clauses WHERE tenant_id = :tid"),
        {"tid": TENANT_ID},
    ).fetchall()
    clause_map = {row.clause_type: row.id for row in clause_rows}

    created = 0
    now = datetime.now(timezone.utc)

    for rule_def in RULES:
        clause_id = clause_map.get(rule_def["clause_type"])
        if not clause_id:
            print(f"  SKIP: No clause found for type '{rule_def['clause_type']}'")
            continue

        if dry_run:
            print(f"  WOULD CREATE: {rule_def['name']}")
            created += 1
            continue

        session.execute(
            sa_text("""
                INSERT INTO clause_recommendation_rules
                    (id, tenant_id, name, description, priority, is_active, clause_id,
                     clause_version, recommendation_type, variable_key, operator,
                     condition_value, created_by, created_at)
                VALUES (:id, :tid, :name, :desc, :priority, TRUE, :clause_id, 1,
                        :rec_type, :var_key, :op, :cond_val, 'system', :now)
            """).bindparams(
                cond_val=json.dumps(rule_def["condition_value"]),
            ),
            {
                "id": str(uuid.uuid4()),
                "tid": TENANT_ID,
                "name": rule_def["name"],
                "desc": f"Suggest when {rule_def['variable_key']} {rule_def['operator']} {rule_def['condition_value']}",
                "priority": rule_def["priority"],
                "clause_id": clause_id,
                "rec_type": rule_def["recommendation_type"],
                "var_key": rule_def["variable_key"],
                "op": rule_def["operator"],
                "now": now,
            },
        )
        created += 1

    if not dry_run:
        session.commit()
        print(f"  Committed {created} rules")

    session.close()
    return created


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv
    count = seed_rules(dry_run=dry_run)
    print(f"\n{'Would create' if dry_run else 'Created'} {count} recommendation rules")
