"""Seed compliance frameworks and controls for SOC 2, ISO 27001, GDPR, HIPAA, NIST CSF."""

from __future__ import annotations

import asyncio
import uuid
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev"
TENANT_ID = "00000000-0000-4000-8000-000000000001"


FRAMEWORKS = [
    {
        "name": "SOC 2",
        "version": "2.0",
        "description": "Service Organization Control 2 — trust services criteria for security, availability, processing integrity, confidentiality, and privacy.",
        "category": "security",
        "controls": [
            ("CC6.1", "Access Control Policy", "Logical and physical access controls are in place.", "high", 1),
            ("CC6.2", "User Access Provisioning", "Access is provisioned based on job requirements.", "high", 2),
            ("CC6.6", "Backup and Recovery", "Data is backed up and recoverable.", "high", 3),
            ("CC6.7", "Encryption", "Data is encrypted at rest and in transit.", "high", 4),
            ("CC6.8", "Audit Logging", "System events are logged and monitored.", "high", 5),
            ("CC7.1", "Incident Response", "Security incidents are detected and responded to.", "critical", 6),
            ("CC7.2", "Vulnerability Management", "Vulnerabilities are identified and remediated.", "high", 7),
        ],
    },
    {
        "name": "ISO 27001",
        "version": "2022",
        "description": "International standard for information security management systems (ISMS).",
        "category": "security",
        "controls": [
            ("A.5.1.1", "Information Security Policy", "Management direction for information security.", "high", 1),
            ("A.6.1.1", "Roles and Responsibilities", "Information security roles are defined.", "medium", 2),
            ("A.8.1.1", "Asset Inventory", "Information assets are identified and inventoried.", "medium", 3),
            ("A.9.1.2", "Access Control Policy", "Access to information is controlled.", "high", 4),
            ("A.12.4.1", "Event Logging", "Events are logged for investigation.", "high", 5),
            ("A.16.1.1", "Incident Management", "Security incidents are managed.", "critical", 6),
            ("A.18.1.1", "Compliance with Legal Requirements", "Legal and regulatory requirements are identified.", "high", 7),
        ],
    },
    {
        "name": "GDPR",
        "version": "2018",
        "description": "General Data Protection Regulation — EU data privacy and protection regulation.",
        "category": "privacy",
        "controls": [
            ("Art.5", "Data Processing Principles", "Personal data is processed lawfully, fairly, and transparently.", "critical", 1),
            ("Art.7", "Consent Management", "Consent is obtained and documented.", "high", 2),
            ("Art.17", "Right to Erasure", "Data subjects can request deletion.", "high", 3),
            ("Art.32", "Security of Processing", "Appropriate technical measures are in place.", "critical", 4),
            ("Art.33", "Breach Notification", "Data breaches are reported within 72 hours.", "critical", 5),
            ("Art.35", "Data Protection Impact Assessment", "DPIAs are conducted for high-risk processing.", "high", 6),
        ],
    },
    {
        "name": "HIPAA",
        "version": "2023",
        "description": "Health Insurance Portability and Accountability Act — US healthcare data privacy and security.",
        "category": "healthcare",
        "controls": [
            ("164.308(a)(1)", "Security Management Process", "Risk analysis and management policies.", "critical", 1),
            ("164.308(a)(3)", "Workforce Security", "Workforce access to ePHI is authorized.", "high", 2),
            ("164.308(a)(5)", "Security Awareness Training", "Workforce is trained on security.", "medium", 3),
            ("164.308(a)(6)", "Incident Response", "Security incidents are reported and managed.", "critical", 4),
            ("164.312(a)(1)", "Access Control", "ePHI access is restricted.", "high", 5),
            ("164.312(c)(1)", "Integrity Controls", "ePHI is not improperly altered.", "high", 6),
            ("164.312(d)", "Person or Entity Authentication", "Users are uniquely identified.", "high", 7),
        ],
    },
    {
        "name": "NIST CSF",
        "version": "2.0",
        "description": "National Institute of Standards and Technology Cybersecurity Framework.",
        "category": "security",
        "controls": [
            ("ID.AM-1", "Asset Management", "Physical devices and systems are inventoried.", "medium", 1),
            ("ID.GV-1", "Governance", "Cybersecurity policy is established.", "high", 2),
            ("ID.RM-1", "Risk Management", "Risk management processes are established.", "high", 3),
            ("PR.AC-1", "Access Control", "Identities and credentials are managed.", "high", 4),
            ("PR.DS-1", "Data Security", "Data at rest is protected.", "high", 5),
            ("DE.CM-1", "Continuous Monitoring", "The network is monitored for threats.", "high", 6),
            ("RS.CO-1", "Response Communications", "Incident response plans are communicated.", "critical", 7),
        ],
    },
]


async def seed() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with AsyncSession(engine) as session:
        # Check if frameworks already exist
        result = await session.execute(
            text("SELECT COUNT(*) FROM compliance_frameworks WHERE tenant_id = :tid"),
            {"tid": TENANT_ID},
        )
        existing = result.scalar() or 0
        if existing > 0:
            logger.info("Found %d existing frameworks — skipping seed", existing)
            await engine.dispose()
            return

        for fw_data in FRAMEWORKS:
            controls = fw_data.pop("controls")
            fw_id = uuid.uuid4()

            await session.execute(
                text("""
                    INSERT INTO compliance_frameworks
                        (framework_id, tenant_id, name, version, description, category,
                         is_active, control_count, extra_metadata, created_by)
                    VALUES
                        (:fid, :tid, :name, :version, :desc, :cat,
                         true, :cc, '{}', 'system')
                """),
                {
                    "fid": fw_id,
                    "tid": TENANT_ID,
                    "name": fw_data["name"],
                    "version": fw_data["version"],
                    "desc": fw_data["description"],
                    "cat": fw_data["category"],
                    "cc": len(controls),
                },
            )

            for i, (ctrl_id, ctrl_name, ctrl_desc, risk_level, sort_order) in enumerate(controls):
                await session.execute(
                    text("""
                        INSERT INTO compliance_controls
                            (control_id, framework_id, tenant_id, control_id_str, name,
                             description, category, risk_level, is_active, sort_order,
                             extra_metadata, created_by)
                        VALUES
                            (:cid, :fid, :tid, :cid_str, :name,
                             :desc, :cat, :risk, true, :sort,
                             '{}', 'system')
                    """),
                    {
                        "cid": uuid.uuid4(),
                        "fid": fw_id,
                        "tid": TENANT_ID,
                        "cid_str": ctrl_id,
                        "name": ctrl_name,
                        "desc": ctrl_desc,
                        "cat": fw_data["category"],
                        "risk": risk_level,
                        "sort": sort_order,
                    },
                )

            logger.info("Seeded framework: %s (%d controls)", fw_data["name"], len(controls))

        await session.commit()
        logger.info("Compliance seed complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
