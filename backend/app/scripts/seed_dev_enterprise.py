"""Enterprise demo dataset for the DEV tenant.

Replaces the test-fixture `completed-contract.pdf` pollution with 100+
realistic enterprise contracts spanning the major agreement types:
MSA, SOW, SaaS, DPA, NDA, Vendor, Purchase, License, Partnership, etc.

Each contract has:
- Unique name, vendor, contract number
- Realistic financial value (USD)
- Realistic risk score (0-10)
- Lifecycle state: ai_analyzed, in_review, approved, pending_renewal, expired
- Workflow stage: intake, ai_review, procurement, legal_ops, security, etc.
- Document metadata: vendor, contract_type, financial_value, effective_date,
  expiration_date, renewal_date, last_review_date, owner, geography, etc.
- Findings, redlines, audit events, assignments, escalations

Run with: PYTHONPATH=. python -m app.scripts.seed_dev_enterprise --reset
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.domains.ingestion.models import UploadSession, IngestionState
from app.domains.ingestion.batch_models import BatchUpload  # noqa: F401  (FK target for upload_sessions.batch_id)
from app.domains.review.models import (
    ContractReview, ReviewFinding, ReviewRedline,
    ReviewStatus, FindingResolution, RedlineStatus,
    ReviewAssignment, ReviewStatusHistory, ReviewApproval,
)
from app.domains.admin.models import AdminUser


logger = logging.getLogger(__name__)

DEV_TENANT_ID = "00000000-0000-4000-8000-000000000001"
DEV_USER_IDS = [
    "dev-user",
    "user-legal-ops",
    "user-reviewer",
    "user-compliance",
    "user-executive",
    "user-ai-ops",
]

# ── Lifecycle showcase (one contract per stage) ─────────────────────────────

LIFECYCLE_SHOWCASE = [
    {
        "name": "Draft — Vendor Onboarding MSA",
        "vendor": "Northwind Logistics",
        "type": "MSA",
        "value": 850_000,
        "risk": 4.2,
        "lifecycle": "draft",
        "review_status": ReviewStatus.DRAFT,
        "workflow_stage": "intake",
        "contract_number": "C06202601",
        "renewal": "+365d",
        "sla_status": "on_track",
        "sla_breached": False,
    },
    {
        "name": "Review — SaaS Platform Agreement",
        "vendor": "CloudPeak Systems",
        "type": "SaaS",
        "value": 1_920_000,
        "risk": 7.1,
        "lifecycle": "review",
        "review_status": ReviewStatus.IN_REVIEW,
        "workflow_stage": "reviewer",
        "contract_number": "C06202602",
        "renewal": "+180d",
        "sla_status": "on_track",
        "sla_breached": False,
    },
    {
        "name": "Approved — Professional Services SOW",
        "vendor": "Summit Consulting Group",
        "type": "SOW",
        "value": 640_000,
        "risk": 4.5,
        "lifecycle": "approved",
        "review_status": ReviewStatus.APPROVED,
        "workflow_stage": "executive",
        "contract_number": "C06202603",
        "renewal": "+270d",
        "sla_status": "on_track",
        "sla_breached": False,
    },
    {
        "name": "Active — Enterprise Support MSA",
        "vendor": "Atlas Infrastructure",
        "type": "MSA",
        "value": 3_100_000,
        "risk": 3.2,
        "lifecycle": "active",
        "review_status": ReviewStatus.EXECUTED,
        "workflow_stage": "executed",
        "contract_number": "C06202604",
        "renewal": "+540d",
        "sla_status": "on_track",
        "sla_breached": False,
    },
    {
        "name": "Expiring — Data Processing Agreement",
        "vendor": "Prism Analytics Co",
        "type": "DPA",
        "value": 0,
        "risk": 6.4,
        "lifecycle": "expiring",
        "review_status": ReviewStatus.EXECUTED,
        "workflow_stage": "executed",
        "contract_number": "C06202605",
        "renewal": "+45d",
        "sla_status": "critical_overdue",
        "sla_breached": True,
    },
    {
        "name": "Closed — Legacy NDA (Archived)",
        "vendor": "EuroLegal Partners",
        "type": "NDA",
        "value": 0,
        "risk": 1.8,
        "lifecycle": "closed",
        "review_status": ReviewStatus.ARCHIVED,
        "workflow_stage": "archived",
        "contract_number": "C06202606",
        "renewal": "-120d",
        "sla_status": "on_track",
        "sla_breached": False,
    },
]

# ── Realistic enterprise contract fixtures ────────────────────────────
# Each contract has a unique name, vendor, type, value, risk profile, and
# lifecycle state designed to populate the repository without duplicates.

VENDORS = [
    "Neon Systems", "Apex Cloud", "Vector Labs", "Helix Partners",
    "OmniCorp International", "DataSync LLC", "Quantum Networks",
    "Pinnacle Software", "StellarCloud", "Meridian Health",
    "Beacon Analytics", "Catalyst AI", "Summit Logistics",
    "Vanguard Security", "Atlas Consulting", "Zenith Marketing",
    "Prism Data Co", "Echo Communications", "Onyx Manufacturing",
    "Halcyon Insurance", "Lumen Energy", "Crestwood Hospitality",
    "Northstar Finance", "Rivera & Associates", "Ironclad Defense",
    "Sapphire Biotech", "Vermilion Studios", "Tundra Outdoor",
    "Magnolia Foods", "Cobalt Robotics",
]

OWNERS = [
    ("Mike Johnson", "user-reviewer", "Procurement"),
    ("Sarah Chen", "user-legal-ops", "Legal Ops"),
    ("Lisa Patel", "user-compliance", "Compliance"),
    ("David Williams", "user-executive", "Executive"),
    ("Alex Kim", "user-viewer", "Viewer"),
    ("Jordan Taylor", "user-ai-ops", "AI Ops"),
]

GEOGRAPHIES = ["North America", "EMEA", "APAC", "LATAM", "Global"]
PRIORITIES = ["critical", "high", "medium", "low"]

# Contract name templates by type
CONTRACT_NAMES = {
    "MSA": [
        "Global Strategic Vendor MSA",
        "Enterprise Cloud Infrastructure MSA",
        "Data Center Colocation Services MSA",
        "APAC Regional Procurement MSA",
        "EMEA Supply Chain Master Agreement",
        "North America Logistics MSA",
        "Enterprise Cybersecurity MSA",
        "Global Software Reseller MSA",
        "Healthcare Procurement MSA",
        "Manufacturing Equipment MSA",
    ],
    "SOW": [
        "Strategic Consulting SOW",
        "IT Transformation SOW",
        "Cloud Migration SOW",
        "Digital Marketing Campaign SOW",
        "Regulatory Compliance Audit SOW",
        "Data Engineering SOW",
        "Security Penetration Testing SOW",
        "ERP Implementation SOW",
        "Brand Strategy SOW",
        "Customer Experience Design SOW",
    ],
    "SaaS": [
        "Enterprise CRM Platform License",
        "AI/ML Platform Enterprise Agreement",
        "Enterprise Analytics Suite",
        "Collaboration Platform Renewal",
        "DevOps Toolchain License",
        "Customer Data Platform Agreement",
        "Marketing Automation Subscription",
        "Enterprise Search Platform",
        "BI & Reporting Suite",
        "Workforce Management Platform",
    ],
    "DPA": [
        "EU Data Processing Addendum",
        "APAC Data Transfer Agreement",
        "US Healthcare Data Processing",
        "California Consumer Privacy DPA",
        "GDPR Data Processing Addendum",
        "Brazil LGPD Compliance Addendum",
        "Cross-Border Data Transfer Agreement",
        "Employee Data Processing Agreement",
        "Customer Data Handling DPA",
        "Vendor Data Sharing Addendum",
    ],
    "NDA": [
        "Mutual Non-Disclosure Agreement",
        "One-Way Confidentiality Agreement",
        "Project-Specific NDA",
        "M&A Due Diligence NDA",
        "Vendor Evaluation NDA",
        "Partnership Exploration NDA",
        "Patent Disclosure NDA",
        "Technical Information NDA",
        "Financial Information NDA",
        "Pre-Engagement NDA",
    ],
    "Vendor Agreement": [
        "Preferred Vendor Supply Agreement",
        "Hardware Procurement Agreement",
        "Maintenance Services Agreement",
        "Equipment Lease Agreement",
        "Office Supplies Framework",
        "Janitorial Services Agreement",
        "Catering Services Agreement",
        "Translation Services Agreement",
        "Courier & Logistics Agreement",
        "Marketing Print Services Agreement",
    ],
    "Purchase Agreement": [
        "Asset Purchase Agreement",
        "Bulk Software Purchase Order",
        "Hardware Purchase Agreement",
        "Furniture Procurement Contract",
        "Vehicle Fleet Purchase",
        "Real Estate Acquisition",
        "Domain & IP Purchase Agreement",
        "Equipment Trade-In Agreement",
    ],
    "Partnership": [
        "Strategic Alliance Agreement",
        "Joint Marketing Partnership",
        "Channel Partner Agreement",
        "Reseller Partnership Contract",
        "Co-Development Partnership",
        "Referral Partnership Agreement",
        "Technology Partnership MOU",
    ],
    "License": [
        "Enterprise Software License",
        "Patent License Agreement",
        "Trademark License Contract",
        "Open Source Contribution Agreement",
        "Data License Agreement",
        "Brand Usage License",
    ],
    "Renewal": [
        "Cloud Infrastructure Renewal",
        "Software License Renewal",
        "Support Contract Renewal",
        "Maintenance Agreement Renewal",
        "Subscription Plan Renewal",
        "Service Contract Extension",
    ],
}

CONTRACT_TYPES = list(CONTRACT_NAMES.keys())
RENEWAL_OUTCOMES = ["+15d", "+30d", "+45d", "+60d", "+90d", "+120d", "+180d", "+365d"]
SLA_STATUSES = ["on_track", "on_track", "on_track", "warning", "warning", "overdue"]
RISK_PROFILE_FOR_TYPE = {
    "DPA": (7.5, 9.5),
    "MSA": (5.5, 8.8),
    "SaaS": (4.0, 7.5),
    "Vendor Agreement": (3.5, 6.5),
    "SOW": (2.5, 5.5),
    "Purchase Agreement": (4.5, 7.0),
    "NDA": (1.5, 4.5),
    "Partnership": (4.0, 7.0),
    "License": (3.5, 6.5),
    "Renewal": (5.0, 8.0),
}
VALUE_PROFILE_FOR_TYPE = {
    "DPA": (0, 0),
    "MSA": (1_500_000, 5_600_000),
    "SaaS": (480_000, 2_400_000),
    "Vendor Agreement": (75_000, 950_000),
    "SOW": (350_000, 3_500_000),
    "Purchase Agreement": (200_000, 1_800_000),
    "NDA": (0, 0),
    "Partnership": (250_000, 2_000_000),
    "License": (150_000, 1_200_000),
    "Renewal": (350_000, 3_800_000),
}
LIFECYCLE_FOR_TYPE = {
    "DPA": "under_review",
    "MSA": ["under_review", "active", "active", "pending_renewal"],
    "SaaS": ["active", "active", "active", "under_review", "pending_renewal"],
    "Vendor Agreement": ["active", "active", "under_review"],
    "SOW": ["active", "active", "under_review", "approved"],
    "Purchase Agreement": ["active", "active", "under_review"],
    "NDA": ["active", "active", "expired", "expired"],
    "Partnership": ["active", "active", "under_review"],
    "License": ["active", "active", "pending_renewal"],
    "Renewal": ["pending_renewal", "pending_renewal", "active"],
}


def _filename(name: str) -> str:
    """Generate a plausible enterprise filename from a contract name."""
    safe = name.lower()
    for ch in "/&:'\"\\":
        safe = safe.replace(ch, "")
    safe = safe.replace(" ", "_").replace(",", "")
    return f"{safe}.pdf"


def _generate_contracts():
    """Generate a deduplicated list of contract fixtures."""
    contracts = []
    seen_names = set()
    seq = 1
    for ctype, names in CONTRACT_NAMES.items():
        for name in names:
            if name in seen_names:
                continue
            seen_names.add(name)
            vmin, vmax = VALUE_PROFILE_FOR_TYPE[ctype]
            rmin, rmax = RISK_PROFILE_FOR_TYPE[ctype]
            vendor = random.choice(VENDORS)
            owner_name, owner_id, owner_dept = random.choice(OWNERS)
            value = random.randint(vmin, vmax) if vmax > 0 else 0
            risk = round(random.uniform(rmin, rmax), 1)
            lifecycles = LIFECYCLE_FOR_TYPE[ctype]
            if isinstance(lifecycles, str):
                lifecycle = lifecycles
            else:
                lifecycle = random.choice(lifecycles)
            renewal = random.choice(RENEWAL_OUTCOMES)
            geography = random.choice(GEOGRAPHIES)
            priority = "critical" if risk >= 8 else "high" if risk >= 6 else "medium" if risk >= 4 else "low"
            sla = random.choice(SLA_STATUSES)
            overdue = (renewal.startswith("-"))
            contract_number = f"CT-{2026}-{seq:05d}"
            seq += 1
            contracts.append({
                "name": name,
                "vendor": vendor,
                "type": ctype,
                "value": value,
                "risk": risk,
                "status": lifecycle,
                "renewal": renewal,
                "owner_name": owner_name,
                "owner_id": owner_id,
                "owner_dept": owner_dept,
                "geography": geography,
                "priority": priority,
                "sla_status": sla,
                "sla_breached": overdue,
                "contract_number": contract_number,
            })
    # Add a few more unique ones for variety
    extra = [
        ("Statement of Work #47 — Q3 Marketing Push", "SOW", "Zenith Marketing", 1_200_000, 4.2),
        ("Strategic Partnership — Healthcare", "Partnership", "Meridian Health", 4_500_000, 6.8),
        ("Telecommunications Services Agreement", "Vendor Agreement", "Echo Communications", 680_000, 4.1),
        ("Cybersecurity Retainer Agreement", "Vendor Agreement", "Vanguard Security", 950_000, 5.7),
        ("Logistics & Freight Forwarding SOW", "SOW", "Summit Logistics", 2_100_000, 3.8),
        ("Enterprise Search Platform License", "License", "Pinnacle Software", 875_000, 4.4),
        ("Marketing Analytics Subscription", "SaaS", "Beacon Analytics", 540_000, 3.6),
        ("Cross-Border Data Transfer Agreement", "DPA", "Prism Data Co", 0, 8.4),
        ("Equipment Lease — Manufacturing Line 3", "Vendor Agreement", "Onyx Manufacturing", 3_400_000, 5.2),
        ("Data Center Power & Cooling Services", "Vendor Agreement", "Lumen Energy", 1_900_000, 6.1),
    ]
    for name, ctype, vendor, value, risk in extra:
        if name in seen_names:
            continue
        seen_names.add(name)
        owner_name, owner_id, owner_dept = random.choice(OWNERS)
        lifecycles = LIFECYCLE_FOR_TYPE[ctype]
        lifecycle = lifecycles if isinstance(lifecycles, str) else random.choice(lifecycles)
        renewal = random.choice(RENEWAL_OUTCOMES)
        priority = "critical" if risk >= 8 else "high" if risk >= 6 else "medium" if risk >= 4 else "low"
        sla = random.choice(SLA_STATUSES)
        overdue = (renewal.startswith("-"))
        contract_number = f"CT-{2026}-{seq:05d}"
        seq += 1
        contracts.append({
            "name": name,
            "vendor": vendor,
            "type": ctype,
            "value": value,
            "risk": risk,
            "status": lifecycle,
            "renewal": renewal,
            "owner_name": owner_name,
            "owner_id": owner_id,
            "owner_dept": owner_dept,
            "geography": random.choice(GEOGRAPHIES),
            "priority": priority,
            "sla_status": sla,
            "sla_breached": overdue,
            "contract_number": contract_number,
        })
    return contracts


async def seed_dev_tenant(engine_url: str, reset: bool = False) -> int:
    """Seed the dev tenant with 100+ realistic enterprise contracts.

    Returns the number of contracts seeded.
    """
    engine = create_async_engine(engine_url)

    # Cleanup
    if reset:
        logger.info("Resetting dev tenant data...")
        async with engine.begin() as conn:
            for t in [
                "review_status_history", "review_redlines", "review_findings",
                "review_assignments", "review_escalations", "review_approvals",
                "review_comments", "contract_document_versions", "contract_reviews",
                "ai_findings", "ai_redlines", "ai_execution_runs", "bulk_actions",
                "upload_sessions",
            ]:
                try:
                    await conn.execute(
                        text(f'DELETE FROM "{t}" WHERE tenant_id = :tid'),
                        {"tid": DEV_TENANT_ID},
                    )
                except Exception as e:
                    logger.warning("  %s: skipped (%s)", t, e.__class__.__name__)
        logger.info("Dev tenant data reset complete.")

    contracts = [dict(c) for c in LIFECYCLE_SHOWCASE] + _generate_contracts()
    logger.info("Seeding %d enterprise contracts for dev tenant %s", len(contracts), DEV_TENANT_ID)

    now = datetime.utcnow()
    rng = random.Random(42)  # deterministic seed for reproducible demos

    async with AsyncSession(engine) as session:
        # Pre-fetch a user id we can attribute activity to
        result = await session.execute(
            select(AdminUser).where(AdminUser.tenant_id == DEV_TENANT_ID).limit(1)
        )
        seed_user = result.scalar_one_or_none()
        if not seed_user:
            # Create the dev admin if missing
            seed_user = AdminUser(
                user_id="dev-user",
                tenant_id=DEV_TENANT_ID,
                email="dev@contractriskedge.local",
                name="Development Admin",
                role="admin",
                is_active=True,
            )
            session.add(seed_user)
            await session.flush()

        for i, c in enumerate(contracts):
            upload_id = uuid.uuid4()
            review_id = uuid.uuid4()
            file_size = 1_500_000 + (i * 137_000) % 4_000_000
            created_at = now - timedelta(days=60 + i * 2)
            effective_date = created_at + timedelta(days=7)
            renewal_days = int(c["renewal"].replace("+", "").replace("-", "").replace("d", ""))
            is_overdue = c["renewal"].startswith("-")
            expiration_date = effective_date + timedelta(days=365 if not is_overdue else 200)
            renewal_date = expiration_date if not is_overdue else now - timedelta(days=renewal_days)
            last_review_date = created_at + timedelta(days=14)
            days_to_renewal = (renewal_date - now).days if not is_overdue else -renewal_days
            sla_deadline = renewal_date
            overdue_hours = float(max(0, -days_to_renewal) * 24) if is_overdue else 0.0

            # Lifecycle showcase fixtures carry explicit review/workflow fields
            if "review_status" in c:
                review_status = c["review_status"]
                workflow_stage = c["workflow_stage"]
                if c.get("lifecycle") == "expiring":
                    expiration_date = now + timedelta(days=45)
                    renewal_date = expiration_date
                    sla_deadline = now - timedelta(days=30)
                    overdue_hours = 720.0
                if c.get("lifecycle") == "closed":
                    expiration_date = now - timedelta(days=120)
                    renewal_date = expiration_date
                if c.get("lifecycle") == "active":
                    expiration_date = now + timedelta(days=540)
                    renewal_date = expiration_date
            else:
                # Map legacy lifecycle labels to ReviewStatus
                status_map = {
                    "under_review": ReviewStatus.IN_REVIEW,
                    "active": ReviewStatus.APPROVED,
                    "pending_renewal": ReviewStatus.APPROVED,
                    "expired": ReviewStatus.CLOSED,
                    "approved": ReviewStatus.APPROVED,
                }
                workflow_map = {
                    "under_review": "reviewer",
                    "active": "executed",
                    "pending_renewal": "executive",
                    "expired": "archived",
                    "approved": "executed",
                }
                review_status = status_map.get(c["status"], ReviewStatus.AI_ANALYZED)
                workflow_stage = workflow_map.get(c["status"], "ai_review")

            owner_name = c.get("owner_name") or "Development Admin"
            owner_id = c.get("owner_id") or seed_user.user_id

            finding_count = 0 if c.get("lifecycle") == "draft" else rng.randint(2, 18)
            terminal_lifecycle = c.get("lifecycle") in ("approved", "active", "expiring", "closed")
            legacy_terminal = c.get("status") in ("active", "expired", "approved")
            completed_at = (
                last_review_date + timedelta(days=2)
                if ("review_status" in c and terminal_lifecycle) or legacy_terminal
                else None
            )

            def _iso_date(dt) -> str:
                if hasattr(dt, "date"):
                    return dt.date().isoformat()
                return str(dt)[:10]

            metadata = {
                "name": c["name"],
                "vendor": c["vendor"],
                "contract_type": c["type"],
                "contract_number": c["contract_number"],
                "financial_value": c["value"],
                "currency": "USD",
                "effective_date": effective_date.isoformat(),
                "expiration_date": _iso_date(expiration_date),
                "renewal_date": _iso_date(renewal_date),
                "last_review_date": last_review_date.isoformat(),
                "owner": owner_name,
                "owner_id": owner_id,
                "geography": c.get("geography") or random.choice(GEOGRAPHIES),
                "risk_score": c["risk"] / 10.0,
                "ai_confidence": 0.85 + rng.random() * 0.10,
                "auto_renew": c.get("lifecycle") == "expiring" or rng.random() > 0.5,
                "description": f"{c['name']} with {c['vendor']} — governs {c['type'].lower()} engagement.",
                "tags": [c["type"].lower(), "lifecycle-showcase" if "review_status" in c else c.get("priority", "medium"), "demo"],
            }

            sla_status = c.get("sla_status", "on_track")
            sla_breached = c.get("sla_breached", is_overdue)
            if c.get("lifecycle") == "expiring":
                sla_status = "critical_overdue"
                sla_breached = True

            session.add(UploadSession(
                upload_id=upload_id,
                tenant_id=DEV_TENANT_ID,
                user_id=seed_user.user_id,
                filename=_filename(c["name"]),
                content_type="application/pdf",
                file_size=file_size,
                storage_key=f"dev/{DEV_TENANT_ID}/{_filename(c['name'])}",
                storage_bucket="contractrisk-documents",
                ingestion_state=IngestionState.REVIEW_READY,
                client_checksum_sha256=uuid.uuid4().hex,
                server_checksum_sha256=uuid.uuid4().hex,
                created_at=created_at,
                updated_at=last_review_date,
            ))

            session.add(ContractReview(
                review_id=review_id,
                upload_id=upload_id,
                tenant_id=DEV_TENANT_ID,
                status=review_status,
                assigned_to=owner_id if c.get("lifecycle") == "review" or (rng.random() > 0.3 and "review_status" not in c) else None,
                assigned_by=seed_user.user_id if c.get("lifecycle") == "review" or rng.random() > 0.3 else None,
                assigned_at=last_review_date if c.get("lifecycle") == "review" or rng.random() > 0.3 else None,
                started_at=last_review_date if review_status == ReviewStatus.IN_REVIEW else None,
                workflow_stage=workflow_stage,
                priority=c.get("priority") or ("high" if c["risk"] >= 6 else "medium"),
                sla_deadline=sla_deadline,
                sla_breached=sla_breached,
                sla_status=sla_status,
                overdue_hours=overdue_hours if c.get("lifecycle") == "expiring" else overdue_hours,
                finding_count=finding_count,
                redline_count=0 if c.get("lifecycle") == "draft" else rng.randint(0, 6),
                comment_count=0 if c.get("lifecycle") == "draft" else rng.randint(0, 4),
                escalation_count=1 if (c["risk"] >= 8 and rng.random() > 0.5 and "review_status" not in c) else 0,
                is_deleted=False,
                document_metadata=metadata,
                created_by=seed_user.user_id,
                created_at=created_at,
                updated_at=last_review_date,
                completed_at=completed_at,
            ))

        # Seed audit history: status transitions for a sample of contracts
        result = await session.execute(
            select(ContractReview).where(ContractReview.tenant_id == DEV_TENANT_ID).limit(20)
        )
        sample_reviews = result.scalars().all()
        for review in sample_reviews:
            session.add(ReviewStatusHistory(
                history_id=uuid.uuid4(),
                review_id=review.review_id,
                tenant_id=DEV_TENANT_ID,
                from_status=ReviewStatus.UPLOADED,
                to_status=ReviewStatus.AI_ANALYZED,
                changed_by=seed_user.user_id,
                reason="Initial AI analysis completed",
                created_at=review.created_at + timedelta(minutes=5),
            ))
            if review.status in (ReviewStatus.IN_REVIEW, ReviewStatus.APPROVED):
                session.add(ReviewStatusHistory(
                    history_id=uuid.uuid4(),
                    review_id=review.review_id,
                    tenant_id=DEV_TENANT_ID,
                    from_status=ReviewStatus.AI_ANALYZED,
                    to_status=ReviewStatus.IN_REVIEW,
                    changed_by=review.assigned_to or seed_user.user_id,
                    reason=f"Assigned to {review.assigned_to or 'reviewer'}",
                    created_at=(review.assigned_at or review.created_at) + timedelta(hours=1),
                ))
            if review.status == ReviewStatus.APPROVED:
                session.add(ReviewStatusHistory(
                    history_id=uuid.uuid4(),
                    review_id=review.review_id,
                    tenant_id=DEV_TENANT_ID,
                    from_status=ReviewStatus.IN_REVIEW,
                    to_status=ReviewStatus.APPROVED,
                    changed_by="user-executive",
                    reason="Executive approval — all SLA conditions met",
                    created_at=review.completed_at or (review.updated_at or now),
                ))

        # Seed assignments for the in-review / assigned ones
        result = await session.execute(
            select(ContractReview).where(
                ContractReview.tenant_id == DEV_TENANT_ID,
                ContractReview.assigned_to.is_not(None),
            )
        )
        assigned_reviews = result.scalars().all()
        for review in assigned_reviews:
            session.add(ReviewAssignment(
                assignment_id=uuid.uuid4(),
                review_id=review.review_id,
                tenant_id=DEV_TENANT_ID,
                assignee_id=review.assigned_to,
                assigned_by=seed_user.user_id,
                role="reviewer",
                due_date=review.sla_deadline,
                created_at=review.assigned_at or review.created_at,
            ))

        # Seed escalations for high-risk contracts
        result = await session.execute(
            select(ContractReview).where(
                ContractReview.tenant_id == DEV_TENANT_ID,
                ContractReview.escalation_count > 0,
            )
        )
        escalated_reviews = result.scalars().all()
        for review in escalated_reviews:
            session.add(ReviewStatusHistory(
                history_id=uuid.uuid4(),
                review_id=review.review_id,
                tenant_id=DEV_TENANT_ID,
                from_status=ReviewStatus.IN_REVIEW,
                to_status=ReviewStatus.ESCALATED,
                changed_by=review.assigned_to or seed_user.user_id,
                reason="High-risk findings — escalated for legal review",
                created_at=review.created_at + timedelta(days=10),
            ))

        # Seed findings and redlines for a sample of contracts
        result = await session.execute(
            select(ContractReview).where(
                ContractReview.tenant_id == DEV_TENANT_ID,
                ContractReview.finding_count > 0,
            ).limit(30)
        )
        finding_reviews = result.scalars().all()
        for review in finding_reviews:
            md = dict(review.document_metadata) if review.document_metadata else {}
            clause_types = ["indemnification", "limitation_of_liability", "termination", "confidentiality",
                            "data_privacy", "governing_law", "force_majeure", "payment_terms",
                            "ip_ownership", "assignment", "warranty", "compliance"]
            severities = ["critical", "high", "medium", "low"]
            num_findings = rng.randint(2, 6)
            for i in range(num_findings):
                ct = rng.choice(clause_types)
                sev = rng.choice(severities)
                finding_id = uuid.uuid4()
                session.add(ReviewFinding(
                    finding_id=finding_id,
                    review_id=review.review_id,
                    upload_id=review.upload_id,
                    tenant_id=DEV_TENANT_ID,
                    clause_type=ct,
                    severity=sev,
                    title=f"{ct.replace('_', ' ').title()} — {sev.title()} Risk",
                    description=f"AI analysis identified a {sev}-severity issue in the {ct.replace('_', ' ')} clause. "
                                f"The current language creates potential exposure of up to "
                                f"${rng.randint(100, 500)}K in {md.get('geography', 'the applicable jurisdiction')}.",
                    recommendation=f"Consider revising the {ct.replace('_', ' ')} clause to cap liability at "
                                   f"{rng.choice(['1x', '2x', '3x'])} annual fees and align with market standards.",
                    risk_score=round(rng.uniform(0.3, 0.95), 2),
                    resolution=None,
                    chunk_ids=[uuid.uuid4() for _ in range(rng.randint(1, 3))],
                    page_numbers=[rng.randint(1, 25) for _ in range(rng.randint(1, 3))],
                ))
                # Create a redline for ~60% of findings
                if rng.random() < 0.6:
                    session.add(ReviewRedline(
                        redline_id=uuid.uuid4(),
                        review_id=review.review_id,
                        upload_id=review.upload_id,
                        tenant_id=DEV_TENANT_ID,
                        finding_id=finding_id,
                        clause_type=ct,
                        original_text=f"Original {ct.replace('_', ' ')} clause text as found in the contract...",
                        proposed_text=f"Revised {ct.replace('_', ' ')} clause with strengthened protections...",
                        operation=rng.choice(["modification", "replacement", "insertion"]),
                        rationale=f"Mitigates {sev} risk in {ct.replace('_', ' ')} — aligns with market standard.",
                        risk_level=sev,
                        confidence=round(rng.uniform(0.65, 0.98), 2),
                        status="proposed",
                    ))

        await session.commit()
        seeded_count = len(contracts)
        logger.info("Seeded %d contracts for dev tenant", seeded_count)
    await engine.dispose()
    return seeded_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Wipe existing data first")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(seed_dev_tenant(settings.database_url, reset=args.reset))
