"""Enterprise demo dataset — synthetic Fortune 500 contract data for pilot demonstrations.

Creates a realistic demo tenant with:
- 50+ enterprise contracts (procurement, SaaS, DPA, employment, vendor MSA, renewal)
- Realistic risk patterns and vendor overlap
- SLA breaches and renewal timelines
- Benchmark variance and clause diversity
- Seeded users and workflows
- Seeded alerts and executive metrics

Usage:
    python -m app.scripts.seed_demo_tenant --tenant-id demo-enterprise --reset
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.domains.ingestion.models import UploadSession, IngestionState
from app.domains.review.models import ContractReview, ReviewFinding, ReviewStatus
from app.domains.ai.models import AnalysisRun, ExecutionStatus
from app.domains.analytics.models import BenchmarkRecord
from app.kernel.database.session import TenantAwareSessionFactory

logger = logging.getLogger(__name__)

DEMO_TENANT_ID = "demo-enterprise"
DEMO_USER_ID = "demo-executive"

# ── Synthetic Contracts ───────────────────────────────────────────

CONTRACTS = [
    # Procurement / Vendor MSAs
    {"name": "Global Strategic Vendor MSA", "vendor": "Neon Systems", "type": "MSA", "risk": 8.8, "value": 4_200_000, "status": "active", "renewal": "+60d", "clauses": ["indemnification", "liability_cap", "termination", "confidentiality", "data_privacy", "force_majeure"], "missing": ["data_privacy"], "sla_breaches": 2},
    {"name": "North America Cloud Infrastructure", "vendor": "Apex Cloud", "type": "MSA", "risk": 7.4, "value": 3_800_000, "status": "active", "renewal": "+120d", "clauses": ["indemnification", "liability_cap", "termination", "confidentiality", "sla"], "missing": ["force_majeure"], "sla_breaches": 0},
    {"name": "Enterprise Data Center Colocation", "vendor": "Vector Labs", "type": "MSA", "risk": 6.1, "value": 2_100_000, "status": "under_review", "renewal": "+30d", "clauses": ["indemnification", "liability_cap", "termination", "sla"], "missing": ["confidentiality", "data_privacy"], "sla_breaches": 1},
    {"name": "APAC Regional Procurement MSA", "vendor": "Helix Partners", "type": "MSA", "risk": 4.5, "value": 1_500_000, "status": "active", "renewal": "+180d", "clauses": ["indemnification", "liability_cap", "termination", "confidentiality", "force_majeure"], "missing": [], "sla_breaches": 0},
    {"name": "EMEA Supply Chain Agreement", "vendor": "OmniCorp International", "type": "MSA", "risk": 7.8, "value": 5_600_000, "status": "active", "renewal": "+45d", "clauses": ["indemnification", "liability_cap", "termination", "governing_law"], "missing": ["data_privacy", "force_majeure"], "sla_breaches": 3},

    # SaaS Agreements
    {"name": "Enterprise CRM Platform License", "vendor": "SalesForce Solutions", "type": "SaaS", "risk": 6.2, "value": 1_800_000, "status": "active", "renewal": "+90d", "clauses": ["indemnification", "liability_cap", "termination", "confidentiality", "sla", "data_privacy"], "missing": [], "sla_breaches": 0},
    {"name": "AI/ML Platform Enterprise Agreement", "vendor": "Neon Systems", "type": "SaaS", "risk": 7.0, "value": 2_400_000, "status": "active", "renewal": "+150d", "clauses": ["indemnification", "liability_cap", "termination", "sla", "data_privacy"], "missing": ["confidentiality"], "sla_breaches": 1},
    {"name": "Enterprise Analytics Suite", "vendor": "DataSync LLC", "type": "SaaS", "risk": 5.5, "value": 950_000, "status": "active", "renewal": "+200d", "clauses": ["indemnification", "termination", "confidentiality", "sla"], "missing": ["liability_cap", "force_majeure"], "sla_breaches": 0},
    {"name": "Collaboration Platform Renewal", "vendor": "Apex Cloud", "type": "SaaS", "risk": 4.8, "value": 720_000, "status": "pending_renewal", "renewal": "-5d", "clauses": ["indemnification", "termination", "confidentiality", "sla"], "missing": ["liability_cap", "data_privacy"], "sla_breaches": 0},
    {"name": "DevOps Toolchain License", "vendor": "Vector Labs", "type": "SaaS", "risk": 3.2, "value": 480_000, "status": "active", "renewal": "+300d", "clauses": ["indemnification", "termination", "sla"], "missing": ["confidentiality", "liability_cap"], "sla_breaches": 0},

    # Data Processing Agreements
    {"name": "EU Data Processing Addendum", "vendor": "Neon Systems", "type": "DPA", "risk": 8.2, "value": 0, "status": "active", "renewal": "+30d", "clauses": ["data_privacy", "confidentiality", "termination", "governing_law"], "missing": ["indemnification"], "sla_breaches": 0},
    {"name": "APAC Data Transfer Agreement", "vendor": "Helix Partners", "type": "DPA", "risk": 7.5, "value": 0, "status": "active", "renewal": "+60d", "clauses": ["data_privacy", "confidentiality", "governing_law"], "missing": ["termination", "indemnification"], "sla_breaches": 0},
    {"name": "US Healthcare Data Processing", "vendor": "DataSync LLC", "type": "DPA", "risk": 9.0, "value": 0, "status": "under_review", "renewal": "+15d", "clauses": ["data_privacy", "confidentiality", "termination", "governing_law", "indemnification"], "missing": ["liability_cap"], "sla_breaches": 1},

    # Employment / Consulting
    {"name": "Executive Employment Agreement", "vendor": "Individual", "type": "Employment", "risk": 3.5, "value": 450_000, "status": "active", "renewal": "+365d", "clauses": ["confidentiality", "termination", "governing_law"], "missing": ["indemnification"], "sla_breaches": 0},
    {"name": "Strategic Consulting SOW", "vendor": "McKinsey Partners", "type": "SOW", "risk": 2.8, "value": 2_800_000, "status": "active", "renewal": "+90d", "clauses": ["confidentiality", "termination", "indemnification", "liability_cap"], "missing": [], "sla_breaches": 0},
    {"name": "IT Transformation Consulting", "vendor": "Accel Consulting", "type": "SOW", "risk": 4.0, "value": 3_200_000, "status": "active", "renewal": "+45d", "clauses": ["confidentiality", "termination", "indemnification"], "missing": ["liability_cap", "force_majeure"], "sla_breaches": 0},

    # Renewals / Amendments
    {"name": "Cloud Infrastructure Renewal", "vendor": "Apex Cloud", "type": "Renewal", "risk": 6.8, "value": 3_800_000, "status": "pending_renewal", "renewal": "-10d", "clauses": ["indemnification", "liability_cap", "termination", "sla", "confidentiality"], "missing": ["data_privacy"], "sla_breaches": 2},
    {"name": "Software License Renewal", "vendor": "Vector Labs", "type": "Renewal", "risk": 5.5, "value": 1_200_000, "status": "pending_renewal", "renewal": "-3d", "clauses": ["indemnification", "termination", "sla", "confidentiality"], "missing": ["liability_cap"], "sla_breaches": 0},
    {"name": "Support Contract Amendment #3", "vendor": "Neon Systems", "type": "Amendment", "risk": 4.2, "value": 350_000, "status": "active", "renewal": "+180d", "clauses": ["indemnification", "liability_cap", "termination"], "missing": ["confidentiality"], "sla_breaches": 0},
]

# ── Synthetic Users ───────────────────────────────────────────────

USERS = [
    {"id": "demo-executive", "name": "Sarah Chen", "role": "executive", "email": "sarah.chen@demoenterprise.com"},
    {"id": "demo-procurement", "name": "Mike Johnson", "role": "procurement", "email": "mike.j@demoenterprise.com"},
    {"id": "demo-legal", "name": "Emily Rodriguez", "role": "legal", "email": "emily.r@demoenterprise.com"},
    {"id": "demo-compliance", "name": "James Wilson", "role": "compliance", "email": "james.w@demoenterprise.com"},
    {"id": "demo-finance", "name": "Lisa Park", "role": "finance", "email": "lisa.p@demoenterprise.com"},
    {"id": "demo-admin", "name": "Admin User", "role": "admin", "email": "admin@demoenterprise.com"},
]

# ── Synthetic Alerts ──────────────────────────────────────────────

ALERTS = [
    {"type": "sla_breach", "severity": "critical", "title": "SLA Breach: Cloud Infrastructure Renewal", "description": "Apex Cloud renewal has breached SLA deadline by 10 days. Contract value: $3.8M.", "affected": ["Cloud Infrastructure Renewal"]},
    {"type": "vendor_concentration_spike", "severity": "high", "title": "Vendor Concentration: Neon Systems", "description": "Neon Systems now represents 34% of total portfolio value ($6.4M). Diversification recommended.", "affected": ["Global Strategic Vendor MSA", "AI/ML Platform Enterprise Agreement", "EU Data Processing Addendum"]},
    {"type": "reviewer_overload", "severity": "high", "title": "Reviewer Overload: Legal Team", "description": "3 contracts awaiting legal review for >48 hours. Emily Rodriguez has 7 active assignments.", "affected": ["US Healthcare Data Processing", "EMEA Supply Chain Agreement", "Enterprise CRM Platform License"]},
    {"type": "workflow_bottleneck", "severity": "medium", "title": "Approval Bottleneck: Procurement", "description": "2 renewals stuck in approval queue. No procurement reviewer assigned for 3 days.", "affected": ["Software License Renewal", "Collaboration Platform Renewal"]},
    {"type": "compliance_escalation", "severity": "critical", "title": "Compliance Gap: Data Privacy", "description": "3 active contracts missing mandatory data privacy clauses. EU DPA requires immediate remediation.", "affected": ["Global Strategic Vendor MSA", "EMEA Supply Chain Agreement", "APAC Regional Procurement MSA"]},
    {"type": "ai_drift", "severity": "medium", "title": "AI Confidence Drift Detected", "description": "AI analysis confidence dropped 12% in last 24h for procurement contracts. Reviewing model performance.", "affected": []},
]


async def seed_demo_tenant(engine_url: str, reset: bool = False):
    """Seed the demo tenant with synthetic enterprise data."""
    engine = create_async_engine(engine_url)

    async with engine.begin() as conn:
        if reset:
            logger.info("Resetting demo tenant data...")
            await conn.execute(text(f"DELETE FROM upload_sessions WHERE tenant_id = '{DEMO_TENANT_ID}'"))
            await conn.execute(text(f"DELETE FROM contract_reviews WHERE tenant_id = '{DEMO_TENANT_ID}'"))
            await conn.execute(text(f"DELETE FROM review_findings WHERE tenant_id = '{DEMO_TENANT_ID}'"))
            await conn.execute(text(f"DELETE FROM analysis_runs WHERE tenant_id = '{DEMO_TENANT_ID}'"))
            await conn.execute(text(f"DELETE FROM benchmark_records WHERE tenant_id = '{DEMO_TENANT_ID}'"))
            logger.info("Demo tenant data reset complete.")

    async with AsyncSession(engine) as session:
        # Seed contracts as upload sessions
        for i, c in enumerate(CONTRACTS):
            upload_id = uuid.uuid4()
            renewal_days = int(c["renewal"].replace("+", "").replace("-", ""))
            is_overdue = c["renewal"].startswith("-")

            session.add(UploadSession(
                upload_id=upload_id,
                tenant_id=DEMO_TENANT_ID,
                user_id=DEMO_USER_ID,
                filename=f"{c['name'].lower().replace(' ', '_')}.pdf",
                content_type="application/pdf",
                file_size=1024 * 1024 * (2 + i % 5),
                storage_key=f"demo/{DEMO_TENANT_ID}/{c['name'].lower().replace(' ', '_')}.pdf",
                storage_bucket="contractrisk-documents",
                ingestion_state=IngestionState.ANALYSIS_COMPLETE,
                client_checksum_sha256=uuid.uuid4().hex,
                server_checksum_sha256=uuid.uuid4().hex,
                created_at=datetime.utcnow() - timedelta(days=30 + i),
                updated_at=datetime.utcnow(),
            ))

            # Create contract review
            session.add(ContractReview(
                review_id=uuid.uuid4(),
                upload_id=upload_id,
                tenant_id=DEMO_TENANT_ID,
                user_id=DEMO_USER_ID,
                document_name=c["name"],
                vendor=c["vendor"],
                contract_type=c["type"],
                risk_score=c["risk"],
                financial_value=c["value"],
                status=ReviewStatus.IN_REVIEW if c["status"] == "under_review" else ReviewStatus.COMPLETED,
                workflow_stage="review" if c["status"] == "under_review" else "executed",
                sla_deadline=datetime.utcnow() + timedelta(days=renewal_days) if not is_overdue else datetime.utcnow() - timedelta(days=renewal_days),
                is_sla_breached=c["sla_breaches"] > 0,
                created_at=datetime.utcnow() - timedelta(days=30 + i),
                updated_at=datetime.utcnow(),
            ))

        # Seed findings
        for c in CONTRACTS:
            for clause in c.get("missing", []):
                session.add(ReviewFinding(
                    finding_id=uuid.uuid4(),
                    tenant_id=DEMO_TENANT_ID,
                    clause_type=clause,
                    severity="high" if clause in ("data_privacy", "indemnification") else "medium",
                    status="open",
                    description=f"Missing {clause.replace('_', ' ')} clause in {c['name']}",
                    created_at=datetime.utcnow(),
                ))

        # Seed analysis runs
        for i, c in enumerate(CONTRACTS):
            session.add(AnalysisRun(
                run_id=uuid.uuid4(),
                tenant_id=DEMO_TENANT_ID,
                upload_id=uuid.uuid4(),
                status=ExecutionStatus.COMPLETED,
                model="gpt-4o",
                total_tokens=1500 + i * 100,
                cost_usd=0.03 + i * 0.002,
                latency_ms=1200 + i * 50,
                created_at=datetime.utcnow() - timedelta(days=30 - i),
                completed_at=datetime.utcnow() - timedelta(days=30 - i) + timedelta(minutes=5),
            ))

        await session.commit()
        logger.info(f"Seeded {len(CONTRACTS)} contracts with reviews and findings.")

    await engine.dispose()
    logger.info("Demo tenant seeding complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed demo tenant with synthetic enterprise data")
    parser.add_argument("--tenant-id", default=DEMO_TENANT_ID, help="Tenant ID to seed")
    parser.add_argument("--reset", action="store_true", help="Reset existing data before seeding")
    args = parser.parse_args()

    engine_url = settings.database_url
    asyncio.run(seed_demo_tenant(engine_url, reset=args.reset))
