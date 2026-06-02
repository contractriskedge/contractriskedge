"""Seed compliance frameworks, controls, assessments, and findings for demo tenant.

Creates realistic compliance data for SOC 2, ISO 27001, GDPR, HIPAA, and NIST CSF frameworks
with associated controls, assessments, findings, exceptions, and evidence.

Usage:
    python -m app.scripts.seed_compliance --tenant-id demo-enterprise --reset
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.domains.compliance.models import (
    ComplianceFrameworkModel,
    ComplianceControlModel,
    ComplianceAssessmentModel,
    ComplianceFindingModel,
    ComplianceExceptionModel,
    ComplianceEvidenceModel,
)
from app.kernel.database.models import Tenant

logger = logging.getLogger(__name__)

DEMO_TENANT_ID = "00000000-0000-4000-8000-000000000001"
DEMO_USER_ID = "demo-compliance"

# ── Frameworks ────────────────────────────────────────────────────

FRAMEWORKS = [
    {
        "name": "SOC 2",
        "version": "2.0",
        "description": "Service Organization Control 2 — Trust Services Criteria for security, availability, processing integrity, confidentiality, and privacy.",
        "category": "security",
    },
    {
        "name": "ISO 27001",
        "version": "2022",
        "description": "International standard for information security management systems (ISMS).",
        "category": "security",
    },
    {
        "name": "GDPR",
        "version": "2018",
        "description": "General Data Protection Regulation — EU regulation on data protection and privacy.",
        "category": "privacy",
    },
    {
        "name": "HIPAA",
        "version": "2024",
        "description": "Health Insurance Portability and Accountability Act — US healthcare data privacy and security.",
        "category": "privacy",
    },
    {
        "name": "NIST CSF",
        "version": "2.0",
        "description": "National Institute of Standards and Technology Cybersecurity Framework.",
        "category": "security",
    },
]

# ── Controls per Framework ─────────────────────────────────────────

SOC2_CONTROLS = [
    {"control_id_str": "CC1.1", "name": "Board Oversight", "description": "Board of directors provides oversight of security policies and procedures.", "category": "security", "risk_level": "high", "sort_order": 1},
    {"control_id_str": "CC2.1", "name": "Communication of Security Policies", "description": "Security policies are communicated to all personnel.", "category": "security", "risk_level": "medium", "sort_order": 2},
    {"control_id_str": "CC3.1", "name": "Risk Assessment Process", "description": "Formal risk assessment process identifies and evaluates security risks.", "category": "security", "risk_level": "high", "sort_order": 3},
    {"control_id_str": "CC4.1", "name": "Monitoring Activities", "description": "Controls are continuously monitored for effectiveness.", "category": "security", "risk_level": "medium", "sort_order": 4},
    {"control_id_str": "CC5.1", "name": "Access Control", "description": "Logical and physical access is restricted to authorized users.", "category": "security", "risk_level": "critical", "sort_order": 5},
    {"control_id_str": "CC6.1", "name": "System Monitoring", "description": "System components are monitored for security events and anomalies.", "category": "security", "risk_level": "high", "sort_order": 6},
    {"control_id_str": "CC7.1", "name": "Incident Response", "description": "Security incidents are identified, reported, and remediated.", "category": "security", "risk_level": "critical", "sort_order": 7},
    {"control_id_str": "CC8.1", "name": "Business Continuity", "description": "Business continuity and disaster recovery plans are maintained.", "category": "security", "risk_level": "high", "sort_order": 8},
    {"control_id_str": "CC9.1", "name": "Vendor Management", "description": "Third-party vendors are assessed for security controls.", "category": "security", "risk_level": "medium", "sort_order": 9},
    {"control_id_str": "P1.1", "name": "Privacy Notice", "description": "Privacy notice is published and accessible to data subjects.", "category": "privacy", "risk_level": "high", "sort_order": 10},
]

ISO27001_CONTROLS = [
    {"control_id_str": "A.5.1", "name": "Information Security Policy", "description": "Management defines and reviews information security policy.", "category": "security", "risk_level": "high", "sort_order": 1},
    {"control_id_str": "A.6.1", "name": "Organizational Security", "description": "Internal organization establishes security roles and responsibilities.", "category": "security", "risk_level": "medium", "sort_order": 2},
    {"control_id_str": "A.7.1", "name": "HR Security", "description": "Background checks and employment agreements include security provisions.", "category": "security", "risk_level": "medium", "sort_order": 3},
    {"control_id_str": "A.8.1", "name": "Asset Management", "description": "Information assets are inventoried and classified.", "category": "security", "risk_level": "medium", "sort_order": 4},
    {"control_id_str": "A.9.1", "name": "Access Control Policy", "description": "Access to information and systems is controlled.", "category": "security", "risk_level": "critical", "sort_order": 5},
    {"control_id_str": "A.10.1", "name": "Cryptography", "description": "Cryptographic controls protect data at rest and in transit.", "category": "security", "risk_level": "high", "sort_order": 6},
    {"control_id_str": "A.12.1", "name": "Operations Security", "description": "Operations procedures are documented and monitored.", "category": "security", "risk_level": "medium", "sort_order": 7},
    {"control_id_str": "A.13.1", "name": "Network Security", "description": "Networks are secured and monitored for unauthorized access.", "category": "security", "risk_level": "high", "sort_order": 8},
    {"control_id_str": "A.16.1", "name": "Incident Management", "description": "Security incidents are reported and managed promptly.", "category": "security", "risk_level": "critical", "sort_order": 9},
    {"control_id_str": "A.18.1", "name": "Regulatory Compliance", "description": "Legal and regulatory requirements are identified and addressed.", "category": "compliance", "risk_level": "high", "sort_order": 10},
]

GDPR_CONTROLS = [
    {"control_id_str": "ART.5", "name": "Data Processing Principles", "description": "Personal data processed lawfully, fairly, and transparently.", "category": "privacy", "risk_level": "critical", "sort_order": 1},
    {"control_id_str": "ART.7", "name": "Consent Management", "description": "Consent is obtained, recorded, and withdrawable for data processing.", "category": "privacy", "risk_level": "high", "sort_order": 2},
    {"control_id_str": "ART.15", "name": "Data Subject Access Rights", "description": "Data subjects can access their personal data within 30 days.", "category": "privacy", "risk_level": "high", "sort_order": 3},
    {"control_id_str": "ART.17", "name": "Right to Erasure", "description": "Data subjects can request deletion of personal data.", "category": "privacy", "risk_level": "medium", "sort_order": 4},
    {"control_id_str": "ART.25", "name": "Data Protection by Design", "description": "Privacy controls integrated into system design by default.", "category": "privacy", "risk_level": "high", "sort_order": 5},
    {"control_id_str": "ART.32", "name": "Security of Processing", "description": "Technical and organizational measures ensure data security.", "category": "security", "risk_level": "critical", "sort_order": 6},
    {"control_id_str": "ART.33", "name": "Breach Notification", "description": "Data breaches reported to supervisory authority within 72 hours.", "category": "security", "risk_level": "critical", "sort_order": 7},
    {"control_id_str": "ART.35", "name": "DPIA", "description": "Data Protection Impact Assessments conducted for high-risk processing.", "category": "compliance", "risk_level": "high", "sort_order": 8},
    {"control_id_str": "ART.44", "name": "Cross-Border Data Transfers", "description": "Adequate safeguards for international data transfers.", "category": "privacy", "risk_level": "high", "sort_order": 9},
]

HIPAA_CONTROLS = [
    {"control_id_str": "164.308(a)(1)", "name": "Security Management Process", "description": "Implement policies to prevent, detect, and correct security violations.", "category": "security", "risk_level": "critical", "sort_order": 1},
    {"control_id_str": "164.308(a)(3)", "name": "Workforce Security", "description": "Ensure authorized workforce access to ePHI.", "category": "security", "risk_level": "high", "sort_order": 2},
    {"control_id_str": "164.308(a)(4)", "name": "Information Access Management", "description": "Authorize access to ePHI based on role.", "category": "security", "risk_level": "high", "sort_order": 3},
    {"control_id_str": "164.308(a)(5)", "name": "Security Awareness Training", "description": "Provide security training to all workforce members.", "category": "security", "risk_level": "medium", "sort_order": 4},
    {"control_id_str": "164.308(a)(6)", "name": "Incident Response", "description": "Identify and respond to security incidents involving ePHI.", "category": "security", "risk_level": "critical", "sort_order": 5},
    {"control_id_str": "164.308(a)(7)", "name": "Contingency Planning", "description": "Data backup and disaster recovery for ePHI.", "category": "security", "risk_level": "high", "sort_order": 6},
    {"control_id_str": "164.308(a)(8)", "name": "Business Associate Agreements", "description": "Contracts with business associates ensure ePHI protection.", "category": "compliance", "risk_level": "high", "sort_order": 7},
    {"control_id_str": "164.312(a)(1)", "name": "Access Control", "description": "Unique user IDs and emergency access procedures for ePHI.", "category": "security", "risk_level": "critical", "sort_order": 8},
    {"control_id_str": "164.312(c)(1)", "name": "Integrity Controls", "description": "Mechanisms to ensure ePHI is not improperly altered.", "category": "security", "risk_level": "high", "sort_order": 9},
    {"control_id_str": "164.312(e)(1)", "name": "Transmission Security", "description": "Protect ePHI transmitted over electronic networks.", "category": "security", "risk_level": "high", "sort_order": 10},
]

NIST_CONTROLS = [
    {"control_id_str": "ID.AM-1", "name": "Asset Inventory", "description": "Physical devices and systems are inventoried.", "category": "security", "risk_level": "medium", "sort_order": 1},
    {"control_id_str": "ID.GV-1", "name": "Governance Policy", "description": "Cybersecurity policy is established and reviewed.", "category": "governance", "risk_level": "high", "sort_order": 2},
    {"control_id_str": "ID.RA-1", "name": "Risk Assessment", "description": "Cybersecurity risks are assessed and documented.", "category": "security", "risk_level": "high", "sort_order": 3},
    {"control_id_str": "PR.AC-1", "name": "Identity and Access Management", "description": "Identities and credentials are managed.", "category": "security", "risk_level": "critical", "sort_order": 4},
    {"control_id_str": "PR.DS-1", "name": "Data-at-Rest Protection", "description": "Data at rest is protected.", "category": "security", "risk_level": "high", "sort_order": 5},
    {"control_id_str": "PR.DS-2", "name": "Data-in-Transit Protection", "description": "Data in transit is protected.", "category": "security", "risk_level": "high", "sort_order": 6},
    {"control_id_str": "DE.CM-1", "name": "Continuous Monitoring", "description": "Network and system activity is monitored.", "category": "security", "risk_level": "high", "sort_order": 7},
    {"control_id_str": "DE.CM-4", "name": "Malware Detection", "description": "Malicious code is detected.", "category": "security", "risk_level": "critical", "sort_order": 8},
    {"control_id_str": "RS.MI-1", "name": "Incident Mitigation", "description": "Incidents are contained and mitigated.", "category": "security", "risk_level": "critical", "sort_order": 9},
    {"control_id_str": "RC.RP-1", "name": "Recovery Planning", "description": "Recovery processes are executed during/after incidents.", "category": "security", "risk_level": "high", "sort_order": 10},
]

FRAMEWORK_CONTROLS = {
    "SOC 2": SOC2_CONTROLS,
    "ISO 27001": ISO27001_CONTROLS,
    "GDPR": GDPR_CONTROLS,
    "HIPAA": HIPAA_CONTROLS,
    "NIST CSF": NIST_CONTROLS,
}


async def seed_compliance(engine_url: str, tenant_id: str = DEMO_TENANT_ID, reset: bool = False):
    """Seed compliance frameworks, controls, and demo data."""
    engine = create_async_engine(engine_url)

    async with engine.begin() as conn:
        if reset:
            logger.info(f"Resetting compliance data for tenant {tenant_id}...")
            await conn.execute(text(f"DELETE FROM compliance_evidence WHERE tenant_id = '{tenant_id}'::uuid"))
            await conn.execute(text(f"DELETE FROM compliance_exceptions WHERE tenant_id = '{tenant_id}'::uuid"))
            await conn.execute(text(f"DELETE FROM compliance_findings WHERE tenant_id = '{tenant_id}'::uuid"))
            await conn.execute(text(f"DELETE FROM compliance_assessments WHERE tenant_id = '{tenant_id}'::uuid"))
            await conn.execute(text(f"DELETE FROM compliance_controls WHERE tenant_id = '{tenant_id}'::uuid"))
            await conn.execute(text(f"DELETE FROM compliance_frameworks WHERE tenant_id = '{tenant_id}'::uuid"))
            logger.info("Compliance data reset complete.")

    async with AsyncSession(engine) as session:
        framework_map: dict[str, uuid.UUID] = {}
        framework_obj_map: dict[str, ComplianceFrameworkModel] = {}

        # Seed frameworks
        for fw_data in FRAMEWORKS:
            fw_id = uuid.uuid4()
            fw = ComplianceFrameworkModel(
                framework_id=fw_id,
                tenant_id=tenant_id,
                name=fw_data["name"],
                version=fw_data["version"],
                description=fw_data["description"],
                category=fw_data["category"],
                is_active=True,
                created_by=DEMO_USER_ID,
            )
            session.add(fw)
            framework_map[fw_data["name"]] = fw_id
            framework_obj_map[fw_data["name"]] = fw
            logger.info(f"  Created framework: {fw_data['name']} ({fw_id})")

        await session.flush()  # Ensure frameworks are persisted before adding controls

        # Seed controls for each framework
        total_controls = 0
        for fw_name, controls in FRAMEWORK_CONTROLS.items():
            fw_id = framework_map[fw_name]
            for ctrl_data in controls:
                ctrl = ComplianceControlModel(
                    control_id=uuid.uuid4(),
                    framework_id=fw_id,
                    tenant_id=tenant_id,
                    control_id_str=ctrl_data["control_id_str"],
                    name=ctrl_data["name"],
                    description=ctrl_data["description"],
                    category=ctrl_data["category"],
                    risk_level=ctrl_data["risk_level"],
                    is_active=True,
                    sort_order=ctrl_data["sort_order"],
                    created_by=DEMO_USER_ID,
                )
                session.add(ctrl)
                total_controls += 1

            # Update framework control count
            count_stmt = select(func.count()).select_from(ComplianceControlModel).where(
                ComplianceControlModel.framework_id == fw_id,
                ComplianceControlModel.tenant_id == tenant_id,
            )
            count = (await session.execute(count_stmt)).scalar() or 0
            fw_obj = framework_obj_map[fw_name]
            fw_obj.control_count = count
            logger.info(f"  Added {count} controls to {fw_name}")

        await session.commit()
        logger.info(f"Seeded {len(FRAMEWORKS)} frameworks with {total_controls} controls.")

        # ── Create demo assessments ─────────────────────────────────
        now = datetime.utcnow()

        # SOC 2 Assessment - completed
        soc2_id = framework_map["SOC 2"]
        soc2_assessment = ComplianceAssessmentModel(
            assessment_id=uuid.uuid4(),
            framework_id=soc2_id,
            tenant_id=tenant_id,
            name="SOC 2 Type II — Q1 2026 Assessment",
            description="Quarterly SOC 2 Type II assessment covering all trust services criteria.",
            status="completed",
            score=87.5,
            total_controls=10,
            passed_controls=8,
            failed_controls=2,
            compliance_percentage=80.0,
            started_at=now - timedelta(days=45),
            completed_at=now - timedelta(days=5),
            created_by=DEMO_USER_ID,
        )
        session.add(soc2_assessment)

        # ISO 27001 Assessment - in progress
        iso_id = framework_map["ISO 27001"]
        iso_assessment = ComplianceAssessmentModel(
            assessment_id=uuid.uuid4(),
            framework_id=iso_id,
            tenant_id=tenant_id,
            name="ISO 27001 Internal Audit — June 2026",
            description="Annual internal audit for ISO 27001 certification maintenance.",
            status="in_progress",
            score=None,
            total_controls=10,
            passed_controls=0,
            failed_controls=0,
            compliance_percentage=None,
            started_at=now - timedelta(days=2),
            completed_at=None,
            created_by=DEMO_USER_ID,
        )
        session.add(iso_assessment)

        # GDPR Assessment - draft
        gdpr_id = framework_map["GDPR"]
        gdpr_assessment = ComplianceAssessmentModel(
            assessment_id=uuid.uuid4(),
            framework_id=gdpr_id,
            tenant_id=tenant_id,
            name="GDPR Readiness Assessment — H1 2026",
            description="Annual GDPR compliance readiness review.",
            status="draft",
            score=None,
            total_controls=9,
            passed_controls=0,
            failed_controls=0,
            compliance_percentage=None,
            started_at=None,
            completed_at=None,
            created_by=DEMO_USER_ID,
        )
        session.add(gdpr_assessment)

        await session.flush()

        # ── Seed findings for SOC 2 assessment ──────────────────────
        findings_data = [
            {"title": "Access Control Gaps", "description": "3 users have excessive privileges beyond their role requirements.", "severity": "high", "control_id_str": "CC5.1", "risk_score": 7.5, "due": 30, "assigned": "demo-admin"},
            {"title": "Incident Response Documentation", "description": "Incident response playbook not updated in 14 months.", "severity": "medium", "control_id_str": "CC7.1", "risk_score": 5.0, "due": 60, "assigned": "demo-admin"},
            {"title": "Vendor Risk Assessment Backlog", "description": "3 critical vendors have not been reassessed in 12 months.", "severity": "high", "control_id_str": "CC9.1", "risk_score": 6.8, "due": 45, "assigned": "demo-procurement"},
            {"title": "Privacy Notice Outdated", "description": "Privacy notice does not reflect new data processing activities.", "severity": "medium", "control_id_str": "P1.1", "risk_score": 4.2, "due": 90, "assigned": "demo-legal"},
        ]

        # Map control_id_str to actual control IDs for SOC 2
        soc2_ctrl_map = {}
        result = await session.execute(
            select(ComplianceControlModel).where(
                ComplianceControlModel.framework_id == soc2_id,
                ComplianceControlModel.tenant_id == tenant_id,
            )
        )
        for ctrl in result.scalars().all():
            soc2_ctrl_map[ctrl.control_id_str] = ctrl.control_id

        for fd in findings_data:
            finding = ComplianceFindingModel(
                finding_id=uuid.uuid4(),
                assessment_id=soc2_assessment.assessment_id,
                control_id=soc2_ctrl_map.get(fd["control_id_str"]),
                tenant_id=tenant_id,
                title=fd["title"],
                description=fd["description"],
                severity=fd["severity"],
                status="open",
                risk_score=fd["risk_score"],
                due_date=now + timedelta(days=fd["due"]),
                assigned_to=fd["assigned"],
                created_by=DEMO_USER_ID,
            )
            session.add(finding)

        # ── Seed compliance exceptions ──────────────────────────────
        exceptions_data = [
            {
                "control_id_str": "CC5.1",
                "title": "Legacy System Access Exception",
                "justification": "Legacy ERP system does not support role-based access control. Migration scheduled for Q3 2026.",
                "risk_assessment": "Medium risk — legacy system is air-gapped with additional monitoring.",
                "status": "approved",
                "approved_by": "demo-executive",
                "approved_at": now - timedelta(days=30),
                "expires_at": now + timedelta(days=180),
            },
        ]

        for ex_data in exceptions_data:
            exception = ComplianceExceptionModel(
                exception_id=uuid.uuid4(),
                control_id=soc2_ctrl_map.get(ex_data["control_id_str"]),
                tenant_id=tenant_id,
                title=ex_data["title"],
                justification=ex_data["justification"],
                risk_assessment=ex_data["risk_assessment"],
                status=ex_data["status"],
                approved_by=ex_data["approved_by"],
                approved_at=ex_data["approved_at"],
                expires_at=ex_data["expires_at"],
                created_by=DEMO_USER_ID,
            )
            session.add(exception)

        # ── Seed evidence ──────────────────────────────────────────
        evidence_data = [
            {"evidence_id": "ev_access_logs_001", "evidence_type": "log", "framework": "SOC 2", "control_id": "CC5.1", "description": "Access log exports from production systems for March 2026.", "status": "validated", "validated_by": "demo-auditor"},
            {"evidence_id": "ev_incident_report_001", "evidence_type": "report", "framework": "SOC 2", "control_id": "CC7.1", "description": "Incident response test results from Q1 2026 tabletop exercise.", "status": "collected", "validated_by": None},
            {"evidence_id": "ev_training_001", "evidence_type": "training_record", "framework": "HIPAA", "control_id": "164.308(a)(5)", "description": "HIPAA security awareness training completion records for all staff.", "status": "validated", "validated_by": "demo-compliance"},
            {"evidence_id": "ev_dpia_001", "evidence_type": "assessment", "framework": "GDPR", "control_id": "ART.35", "description": "DPIA for new customer data analytics platform.", "status": "collected", "validated_by": None},
        ]

        for ev_data in evidence_data:
            evidence = ComplianceEvidenceModel(
                evidence_id=ev_data["evidence_id"],
                tenant_id=tenant_id,
                evidence_type=ev_data["evidence_type"],
                framework=ev_data["framework"],
                control_id=ev_data["control_id"],
                description=ev_data["description"],
                status=ev_data["status"],
                validated_by=ev_data["validated_by"],
                validated_at=now - timedelta(days=10) if ev_data["validated_by"] else None,
            )
            session.add(evidence)

        await session.commit()
        logger.info(f"Seeded {len(findings_data)} findings, {len(exceptions_data)} exceptions, {len(evidence_data)} evidence records.")
        logger.info("Compliance seeding complete.")

    await engine.dispose()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed compliance frameworks and controls")
    parser.add_argument("--tenant-id", default=DEMO_TENANT_ID, help="Tenant ID to seed")
    parser.add_argument("--reset", action="store_true", help="Reset existing compliance data before seeding")
    args = parser.parse_args()

    engine_url = settings.database_url
    asyncio.run(seed_compliance(engine_url, tenant_id=args.tenant_id, reset=args.reset))
