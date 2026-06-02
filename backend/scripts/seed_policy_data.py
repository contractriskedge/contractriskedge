"""
Seed policy engine data — legal playbooks, clause standards, policy rules,
approval thresholds, and a sample evaluation.

Run:  python -m scripts.seed_policy_data
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

TENANT_ID = "00000000-0000-4000-8000-000000000001"
DATABASE_URL = "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev"


async def seed():
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # ── 1. Legal Playbooks ─────────────────────────────────
        playbooks = [
            {
                "playbook_id": uuid.uuid4(),
                "tenant_id": TENANT_ID,
                "name": "Commercial Contracts Playbook",
                "description": "Standard policy rules for commercial contract reviews including liability, indemnification, and confidentiality.",
                "jurisdiction": "US",
                "practice_area": "commercial",
                "status": "published",
                "active_version_id": None,
                "version_count": 1,
                "tags": ["commercial", "standard", "liability"],
                "metadata": {},
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "playbook_id": uuid.uuid4(),
                "tenant_id": TENANT_ID,
                "name": "Data Privacy Playbook",
                "description": "GDPR, CCPA, and data protection policy rules for data processing agreements.",
                "jurisdiction": "US-EU",
                "practice_area": "data_privacy",
                "status": "published",
                "active_version_id": None,
                "version_count": 1,
                "tags": ["privacy", "gdpr", "ccpa", "dpa"],
                "metadata": {},
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "playbook_id": uuid.uuid4(),
                "tenant_id": TENANT_ID,
                "name": "Procurement Review Playbook",
                "description": "Policy rules for procurement contracts, SaaS agreements, and vendor MSAs.",
                "jurisdiction": "US",
                "practice_area": "procurement",
                "status": "published",
                "active_version_id": None,
                "version_count": 1,
                "tags": ["procurement", "saas", "vendor"],
                "metadata": {},
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        ]

        for pb in playbooks:
            await session.execute(
                sa_text("""
                    INSERT INTO legal_playbooks
                        (playbook_id, tenant_id, name, description, jurisdiction, practice_area,
                         status, active_version_id, version_count, tags, metadata,
                         created_by, created_at, updated_at)
                    VALUES
                        (:playbook_id, :tenant_id, :name, :description, :jurisdiction, :practice_area,
                         :status, :active_version_id, :version_count, :tags::text[], :metadata::jsonb,
                         :created_by, :created_at, :updated_at)
                """),
                pb,
            )

        # Create a version for each playbook
        for pb in playbooks:
            version_id = uuid.uuid4()
            await session.execute(
                sa_text("""
                    INSERT INTO playbook_versions
                        (version_id, playbook_id, tenant_id, version_number, version_label,
                         change_notes, snapshot, created_by, is_draft, is_active, created_at)
                    VALUES
                        (:version_id, :playbook_id, :tenant_id, 1, 'v1.0',
                         'Initial version', '{}'::jsonb, 'system', FALSE, TRUE, :created_at)
                """),
                {
                    "version_id": version_id,
                    "playbook_id": pb["playbook_id"],
                    "tenant_id": TENANT_ID,
                    "created_at": datetime.now(timezone.utc),
                },
            )
            # Link active version
            await session.execute(
                sa_text("""
                    UPDATE legal_playbooks SET active_version_id = :version_id
                    WHERE playbook_id = :playbook_id
                """),
                {"version_id": version_id, "playbook_id": pb["playbook_id"]},
            )

        # ── 2. Clause Standards ────────────────────────────────
        clause_standards = [
            {
                "clause_id": uuid.uuid4(),
                "playbook_id": playbooks[0]["playbook_id"],
                "tenant_id": TENANT_ID,
                "category": "indemnification",
                "clause_type": "approved",
                "title": "Mutual Indemnification — Standard",
                "body": "Each party agrees to indemnify, defend, and hold harmless the other party from and against any and all claims, damages, losses, and expenses arising out of or relating to its breach of this Agreement.",
                "summary": "Mutual indemnification with standard scope",
                "risk_level": "low",
                "is_active": True,
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "clause_id": uuid.uuid4(),
                "playbook_id": playbooks[0]["playbook_id"],
                "tenant_id": TENANT_ID,
                "category": "limitation_of_liability",
                "clause_type": "approved",
                "title": "Mutual Liability Cap — 2x Fees",
                "body": "Neither party's aggregate liability arising out of or relating to this Agreement shall exceed the total fees paid or payable by Customer to Vendor during the twelve (12) months preceding the event giving rise to such liability.",
                "summary": "Mutual liability capped at 2x annual fees",
                "risk_level": "medium",
                "is_active": True,
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "clause_id": uuid.uuid4(),
                "playbook_id": playbooks[0]["playbook_id"],
                "tenant_id": TENANT_ID,
                "category": "confidentiality",
                "clause_type": "approved",
                "title": "Standard Confidentiality — 3 Year Survival",
                "body": "The receiving party shall maintain the confidentiality of the disclosing party's Confidential Information and shall not disclose such information to any third party without the disclosing party's prior written consent. This obligation shall survive termination of this Agreement for a period of three (3) years.",
                "summary": "Standard NDA with 3-year survival",
                "risk_level": "low",
                "is_active": True,
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "clause_id": uuid.uuid4(),
                "playbook_id": playbooks[1]["playbook_id"],
                "tenant_id": TENANT_ID,
                "category": "data_privacy",
                "clause_type": "approved",
                "title": "DPA Required — GDPR Art 28",
                "body": "To the extent Vendor processes any Personal Data on behalf of Customer, the parties shall enter into a Data Processing Agreement in compliance with applicable data protection laws, including GDPR Art 28.",
                "summary": "Data Processing Agreement required for any personal data processing",
                "risk_level": "critical",
                "is_active": True,
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        ]

        for cs in clause_standards:
            await session.execute(
                sa_text("""
                    INSERT INTO clause_standards
                        (clause_id, playbook_id, tenant_id, category, clause_type,
                         title, body, summary, risk_level, tags, is_active,
                         created_by, created_at, updated_at)
                    VALUES
                        (:clause_id, :playbook_id, :tenant_id, :category::clause_category, :clause_type::clause_type,
                         :title, :body, :summary, :risk_level, '{}'::text[], :is_active,
                         :created_by, :created_at, :updated_at)
                """),
                cs,
            )

        # ── 3. Policy Rules ────────────────────────────────────
        rules = [
            {
                "rule_id": uuid.uuid4(),
                "playbook_id": playbooks[0]["playbook_id"],
                "tenant_id": TENANT_ID,
                "name": "IP Ownership — Customer Retains Deliverables",
                "description": "Customer must retain full ownership of all custom deliverables developed specifically for them.",
                "rule_type": "clause_required",
                "priority": 100,
                "is_active": True,
                "is_mandatory": True,
                "conditions": {
                    "group_id": "g1",
                    "type": "AND",
                    "conditions": [
                        {"condition_id": "c1", "field": "clause.category", "operator": "equals", "value": "intellectual_property", "label": "Clause is IP-related"},
                        {"condition_id": "c2", "field": "clause.text", "operator": "contains", "value": "retains exclusive rights", "label": "Vendor retains exclusive rights"},
                    ],
                },
                "effect": "flag_for_review",
                "target_category": "intellectual_property",
                "tags": ["ip", "ownership", "critical"],
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "rule_id": uuid.uuid4(),
                "playbook_id": playbooks[0]["playbook_id"],
                "tenant_id": TENANT_ID,
                "name": "Liability Cap — Mutual 2x Annual Fees",
                "description": "Liability must be capped at no more than 2x annual contract value, mutually applicable.",
                "rule_type": "value_threshold",
                "priority": 90,
                "is_active": True,
                "is_mandatory": True,
                "conditions": {
                    "group_id": "g2",
                    "type": "AND",
                    "conditions": [
                        {"condition_id": "c3", "field": "clause.category", "operator": "equals", "value": "liability", "label": "Clause is liability-related"},
                        {"condition_id": "c4", "field": "clause.text", "operator": "not_contains", "value": "mutual", "label": "Liability is not mutual"},
                    ],
                },
                "effect": "flag_for_review",
                "target_category": "liability",
                "tags": ["liability", "cap", "mutual", "high"],
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "rule_id": uuid.uuid4(),
                "playbook_id": playbooks[0]["playbook_id"],
                "tenant_id": TENANT_ID,
                "name": "Indemnification — Mutual With IP Carve-out",
                "description": "Indemnification must be mutual with exclusions for IP infringement.",
                "rule_type": "clause_required",
                "priority": 85,
                "is_active": True,
                "is_mandatory": False,
                "conditions": {
                    "group_id": "g3",
                    "type": "AND",
                    "conditions": [
                        {"condition_id": "c5", "field": "clause.category", "operator": "equals", "value": "indemnification", "label": "Clause is indemnification"},
                        {"condition_id": "c6", "field": "clause.text", "operator": "not_contains", "value": "mutual", "label": "Indemnification is one-sided"},
                    ],
                },
                "effect": "flag_for_review",
                "target_category": "indemnification",
                "tags": ["indemnification", "mutual", "ip", "high"],
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "rule_id": uuid.uuid4(),
                "playbook_id": playbooks[1]["playbook_id"],
                "tenant_id": TENANT_ID,
                "name": "Data Privacy — DPA Required",
                "description": "A Data Processing Agreement must be attached for any processing of personal data.",
                "rule_type": "clause_required",
                "priority": 95,
                "is_active": True,
                "is_mandatory": True,
                "conditions": {
                    "group_id": "g5",
                    "type": "AND",
                    "conditions": [
                        {"condition_id": "c9", "field": "clause.category", "operator": "equals", "value": "data_privacy", "label": "Clause is data privacy"},
                        {"condition_id": "c10", "field": "clause.text", "operator": "not_contains", "value": "data processing agreement", "label": "No DPA referenced"},
                    ],
                },
                "effect": "block",
                "target_category": "data_privacy",
                "tags": ["privacy", "dpa", "gdpr", "critical"],
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "rule_id": uuid.uuid4(),
                "playbook_id": playbooks[2]["playbook_id"],
                "tenant_id": TENANT_ID,
                "name": "SLA — 99.9% Uptime Minimum",
                "description": "Vendor must commit to at least 99.9% service availability.",
                "rule_type": "value_threshold",
                "priority": 75,
                "is_active": True,
                "is_mandatory": False,
                "conditions": {
                    "group_id": "g6",
                    "type": "AND",
                    "conditions": [
                        {"condition_id": "c11", "field": "clause.category", "operator": "equals", "value": "sla", "label": "Clause is SLA"},
                        {"condition_id": "c12", "field": "clause.text", "operator": "matches_regex", "value": "99\\.?\\s*9\\s*%", "label": "Uptime below 99.9%"},
                    ],
                },
                "effect": "flag_for_review",
                "target_category": "sla",
                "tags": ["sla", "uptime", "medium"],
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "rule_id": uuid.uuid4(),
                "playbook_id": playbooks[0]["playbook_id"],
                "tenant_id": TENANT_ID,
                "name": "Termination — 30-Day Convenience",
                "description": "Customer must have the right to terminate for convenience with 30 days notice.",
                "rule_type": "clause_required",
                "priority": 70,
                "is_active": True,
                "is_mandatory": False,
                "conditions": {
                    "group_id": "g7",
                    "type": "AND",
                    "conditions": [
                        {"condition_id": "c13", "field": "clause.category", "operator": "equals", "value": "termination", "label": "Clause is termination"},
                        {"condition_id": "c14", "field": "clause.text", "operator": "not_contains", "value": "convenience", "label": "No termination for convenience"},
                    ],
                },
                "effect": "flag_for_review",
                "target_category": "termination",
                "tags": ["termination", "convenience", "medium"],
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        ]

        for rule in rules:
            await session.execute(
                sa_text("""
                    INSERT INTO policy_rules
                        (rule_id, playbook_id, tenant_id, name, description, rule_type,
                         priority, is_active, is_mandatory, conditions, effect,
                         target_category, tags, created_by, created_at, updated_at)
                    VALUES
                        (:rule_id, :playbook_id, :tenant_id, :name, :description, :rule_type,
                         :priority, :is_active, :is_mandatory, :conditions::jsonb, :effect::rule_effect,
                         :target_category, :tags::text[], :created_by, :created_at, :updated_at)
                """),
                rule,
            )

        # ── 4. Approval Thresholds ─────────────────────────────
        thresholds = [
            {
                "threshold_id": uuid.uuid4(),
                "playbook_id": playbooks[0]["playbook_id"],
                "tenant_id": TENANT_ID,
                "name": "High Risk Escalation",
                "description": "Reviews with risk score >= 7 require VP Legal approval",
                "threshold_type": "risk_score",
                "comparison_operator": "greater_than",
                "threshold_value": 7.0,
                "approval_role": "general_counsel",
                "priority": 100,
                "is_active": True,
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "threshold_id": uuid.uuid4(),
                "playbook_id": playbooks[0]["playbook_id"],
                "tenant_id": TENANT_ID,
                "name": "High Value Contract Escalation",
                "description": "Contracts over $1M require CFO approval",
                "threshold_type": "contract_value",
                "comparison_operator": "greater_than",
                "threshold_value": 1000000.0,
                "approval_role": "cfo",
                "priority": 90,
                "is_active": True,
                "created_by": "system",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        ]

        for t in thresholds:
            await session.execute(
                sa_text("""
                    INSERT INTO approval_thresholds
                        (threshold_id, playbook_id, tenant_id, name, description,
                         threshold_type, comparison_operator, threshold_value,
                         approval_role, priority, is_active, created_by, created_at, updated_at)
                    VALUES
                        (:threshold_id, :playbook_id, :tenant_id, :name, :description,
                         :threshold_type, :comparison_operator, :threshold_value,
                         :approval_role, :priority, :is_active, :created_by, :created_at, :updated_at)
                """),
                t,
            )

        await session.commit()
        print(f"✅ Seeded {len(playbooks)} playbooks, {len(clause_standards)} clause standards, "
              f"{len(rules)} policy rules, {len(thresholds)} approval thresholds")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
