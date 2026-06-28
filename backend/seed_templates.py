"""Seed template library with sample data."""
import asyncio
import json
import uuid

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings


async def seed():
    engine = create_async_engine(settings.database_url)
    session_factory = sessionmaker(engine, class_=AsyncSession)

    async with session_factory() as session:
        tenant_id = "00000000-0000-4000-8000-000000000001"

        # Check if categories already exist
        result = await session.execute(
            sa_text("SELECT COUNT(*) FROM template_categories WHERE tenant_id = :t"),
            {"t": tenant_id},
        )
        count = result.scalar()
        if count and count > 0:
            print(f"Categories already exist ({count}), skipping seed")
            return

        now_sql = sa_text("NOW()")

        # Create categories
        categories = [
            ("Non-Disclosure Agreement", "nda", "FileLock", 1),
            ("Master Service Agreement", "msa", "FileText", 2),
            ("Statement of Work", "sow", "FileEdit", 3),
            ("Purchase Agreement", "purchase", "ShoppingCart", 4),
            ("Software License", "software-license", "Code", 5),
            ("Data Processing Agreement", "dpa", "Shield", 6),
            ("Consulting Agreement", "consulting", "Briefcase", 7),
            ("Employment Agreement", "employment", "Users", 8),
            ("Lease Agreement", "lease", "Building2", 9),
            ("Custom", "custom", "FilePlus", 99),
        ]
        cat_ids = {}
        for name, slug, icon, order in categories:
            cid = str(uuid.uuid4())
            cat_ids[slug] = cid
            await session.execute(
                sa_text("""
                    INSERT INTO template_categories (id, tenant_id, name, slug, icon, display_order, is_active, created_at, updated_at)
                    VALUES (:id, :t, :name, :slug, :icon, :order, true, NOW(), NOW())
                """),
                {"id": cid, "t": tenant_id, "name": name, "slug": slug, "icon": icon, "order": order},
            )

        # Create MSA template
        msa_id = str(uuid.uuid4())
        msa_ver_id = str(uuid.uuid4())
        await session.execute(
            sa_text("""
                INSERT INTO contract_templates (id, tenant_id, category_id, name, description, tags, owner, department, status, usage_count, created_by, created_at, updated_at)
                VALUES (:id, :t, :cat, :name, :desc, :tags, :owner, :dept, :status, :count, :by, NOW(), NOW())
            """),
            {
                "id": msa_id, "t": tenant_id, "cat": cat_ids["msa"],
                "name": "Master Service Agreement",
                "desc": "Standard MSA for professional services engagements.",
                "tags": json.dumps(["MSA", "Services", "Vendor"]),
                "owner": "Legal Team", "dept": "Legal",
                "status": "approved", "count": 12, "by": "admin",
            },
        )

        msa_vars = json.dumps([
            {"key": "CompanyName", "label": "Company Name", "field_type": "text", "is_required": True, "display_order": 1, "section": "Parties"},
            {"key": "VendorName", "label": "Vendor Name", "field_type": "text", "is_required": True, "display_order": 2, "section": "Parties"},
            {"key": "EffectiveDate", "label": "Effective Date", "field_type": "date", "is_required": True, "display_order": 3, "section": "Dates"},
            {"key": "InitialTerm", "label": "Initial Term (months)", "field_type": "number", "is_required": True, "display_order": 4, "section": "Dates"},
            {"key": "ContractValue", "label": "Contract Value", "field_type": "currency", "is_required": True, "display_order": 5, "section": "Financials"},
            {"key": "Currency", "label": "Currency", "field_type": "text", "is_required": True, "display_order": 6, "section": "Financials"},
            {"key": "PaymentTerms", "label": "Payment Terms (days)", "field_type": "number", "is_required": True, "display_order": 7, "section": "Financials"},
            {"key": "Jurisdiction", "label": "Governing Law", "field_type": "text", "is_required": True, "display_order": 8, "section": "Legal"},
            {"key": "BusinessOwner", "label": "Business Owner", "field_type": "text", "is_required": True, "display_order": 9, "section": "Parties"},
        ])

        msa_content = """MASTER SERVICE AGREEMENT

This Master Service Agreement is entered into as of {{EffectiveDate}} by and between {{CompanyName}} ("Company") and {{VendorName}} ("Vendor").

1. SERVICES
Vendor shall provide services as described in each SOW.

2. PAYMENT TERMS
Company shall pay Vendor within {{PaymentTerms}} days. Fees are in {{Currency}}.

3. TERM
This Agreement shall commence on {{EffectiveDate}} for {{InitialTerm}} months.

4. GOVERNING LAW
This Agreement shall be governed by {{Jurisdiction}}.

5. LIMITATION OF LIABILITY
Aggregate liability shall not exceed {{ContractValue}}.

IN WITNESS WHEREOF, the parties have executed this Agreement.

{{CompanyName}}
By: {{BusinessOwner}}

{{VendorName}}
By: {{VendorName}}"""

        await session.execute(
            sa_text("""
                INSERT INTO template_versions (id, tenant_id, template_id, version_number, label, status, variables, placeholder_content, file_name, created_by, created_at)
                VALUES (:id, :t, :tid, :vnum, :label, :status, :vars, :content, :fname, :by, NOW())
            """),
            {
                "id": msa_ver_id, "t": tenant_id, "tid": msa_id,
                "vnum": 3, "label": "v3.2 - Updated liability", "status": "approved",
                "vars": msa_vars, "content": msa_content, "fname": "MSA_v3.docx", "by": "admin",
            },
        )
        await session.execute(
            sa_text("UPDATE contract_templates SET current_version_id = :vid WHERE id = :id"),
            {"vid": msa_ver_id, "id": msa_id},
        )

        # Create NDA template
        nda_id = str(uuid.uuid4())
        nda_ver_id = str(uuid.uuid4())
        await session.execute(
            sa_text("""
                INSERT INTO contract_templates (id, tenant_id, category_id, name, description, tags, owner, department, status, usage_count, created_by, created_at, updated_at)
                VALUES (:id, :t, :cat, :name, :desc, :tags, :owner, :dept, :status, :count, :by, NOW(), NOW())
            """),
            {
                "id": nda_id, "t": tenant_id, "cat": cat_ids["nda"],
                "name": "Mutual Non-Disclosure Agreement",
                "desc": "Standard mutual NDA for confidential discussions.",
                "tags": json.dumps(["NDA", "Confidentiality"]),
                "owner": "Legal Team", "dept": "Legal",
                "status": "approved", "count": 25, "by": "admin",
            },
        )

        nda_vars = json.dumps([
            {"key": "CompanyName", "label": "Company Name", "field_type": "text", "is_required": True, "display_order": 1, "section": "Parties"},
            {"key": "VendorName", "label": "Counterparty Name", "field_type": "text", "is_required": True, "display_order": 2, "section": "Parties"},
            {"key": "EffectiveDate", "label": "Effective Date", "field_type": "date", "is_required": True, "display_order": 3, "section": "Dates"},
            {"key": "TermYears", "label": "Term (years)", "field_type": "number", "is_required": True, "display_order": 4, "section": "Dates"},
            {"key": "Jurisdiction", "label": "Governing Law", "field_type": "text", "is_required": True, "display_order": 5, "section": "Legal"},
            {"key": "BusinessOwner", "label": "Business Owner", "field_type": "text", "is_required": True, "display_order": 6, "section": "Parties"},
        ])

        nda_content = """MUTUAL NON-DISCLOSURE AGREEMENT

This NDA is made as of {{EffectiveDate}} by {{CompanyName}} and {{VendorName}}.

1. CONFIDENTIAL INFORMATION
Each party shall protect the other's confidential information for {{TermYears}} years.

2. GOVERNING LAW
This Agreement shall be governed by {{Jurisdiction}}.

IN WITNESS WHEREOF, the parties have executed this Agreement.

{{CompanyName}}
By: {{BusinessOwner}}

{{VendorName}}
By: {{VendorName}}"""

        await session.execute(
            sa_text("""
                INSERT INTO template_versions (id, tenant_id, template_id, version_number, label, status, variables, placeholder_content, file_name, created_by, created_at)
                VALUES (:id, :t, :tid, :vnum, :label, :status, :vars, :content, :fname, :by, NOW())
            """),
            {
                "id": nda_ver_id, "t": tenant_id, "tid": nda_id,
                "vnum": 2, "label": "v2.1 - Updated", "status": "approved",
                "vars": nda_vars, "content": nda_content, "fname": "NDA_v2.docx", "by": "admin",
            },
        )
        await session.execute(
            sa_text("UPDATE contract_templates SET current_version_id = :vid WHERE id = :id"),
            {"vid": nda_ver_id, "id": nda_id},
        )

        # ── SOW Template ─────────────────────────────────────────────
        sow_id = str(uuid.uuid4())
        sow_ver_id = str(uuid.uuid4())
        await session.execute(
            sa_text("""
                INSERT INTO contract_templates (id, tenant_id, category_id, name, description, tags, owner, department, status, usage_count, created_by, created_at, updated_at)
                VALUES (:id, :t, :cat, :name, :desc, :tags, :owner, :dept, :status, :count, :by, NOW(), NOW())
            """),
            {
                "id": sow_id, "t": tenant_id, "cat": cat_ids["sow"],
                "name": "Statement of Work",
                "desc": "Standard SOW for professional services engagements under an MSA.",
                "tags": json.dumps(["SOW", "Services", "Project"]),
                "owner": "Project Team", "dept": "Operations",
                "status": "approved", "count": 8, "by": "admin",
            },
        )

        sow_vars = json.dumps([
            {"key": "ProjectName", "label": "Project Name", "field_type": "text", "is_required": True, "display_order": 1, "section": "Parties"},
            {"key": "CompanyName", "label": "Company Name", "field_type": "text", "is_required": True, "display_order": 2, "section": "Parties"},
            {"key": "VendorName", "label": "Vendor Name", "field_type": "text", "is_required": True, "display_order": 3, "section": "Parties"},
            {"key": "EffectiveDate", "label": "Effective Date", "field_type": "date", "is_required": True, "display_order": 4, "section": "Dates"},
            {"key": "DeliveryDate", "label": "Delivery Date", "field_type": "date", "is_required": True, "display_order": 5, "section": "Dates"},
            {"key": "ProjectBudget", "label": "Project Budget", "field_type": "currency", "is_required": True, "display_order": 6, "section": "Financials"},
            {"key": "Description", "label": "Scope Description", "field_type": "text", "is_required": True, "display_order": 7, "section": "Scope"},
            {"key": "BusinessOwner", "label": "Business Owner", "field_type": "text", "is_required": True, "display_order": 8, "section": "Parties"},
        ])

        sow_content = """STATEMENT OF WORK

Project: {{ProjectName}}

This SOW is entered into as of {{EffectiveDate}} by {{CompanyName}} and {{VendorName}}.

1. SCOPE
{{Description}}

2. BUDGET
The total project budget shall not exceed {{ProjectBudget}}.

3. DELIVERY
All deliverables must be completed by {{DeliveryDate}}.

4. GOVERNANCE
{{BusinessOwner}} shall serve as the primary point of contact.

IN WITNESS WHEREOF, the parties have executed this SOW.

{{CompanyName}}
By: {{BusinessOwner}}

{{VendorName}}
By: {{VendorName}}"""

        await session.execute(
            sa_text("""
                INSERT INTO template_versions (id, tenant_id, template_id, version_number, label, status, variables, placeholder_content, file_name, created_by, created_at)
                VALUES (:id, :t, :tid, :vnum, :label, :status, :vars, :content, :fname, :by, NOW())
            """),
            {
                "id": sow_ver_id, "t": tenant_id, "tid": sow_id,
                "vnum": 1, "label": "v1.0 - Initial", "status": "approved",
                "vars": sow_vars, "content": sow_content, "fname": "SOW_v1.docx", "by": "admin",
            },
        )
        await session.execute(
            sa_text("UPDATE contract_templates SET current_version_id = :vid WHERE id = :id"),
            {"vid": sow_ver_id, "id": sow_id},
        )

        # ── DPA Template ─────────────────────────────────────────────
        dpa_id = str(uuid.uuid4())
        dpa_ver_id = str(uuid.uuid4())
        await session.execute(
            sa_text("""
                INSERT INTO contract_templates (id, tenant_id, category_id, name, description, tags, owner, department, status, usage_count, created_by, created_at, updated_at)
                VALUES (:id, :t, :cat, :name, :desc, :tags, :owner, :dept, :status, :count, :by, NOW(), NOW())
            """),
            {
                "id": dpa_id, "t": tenant_id, "cat": cat_ids["dpa"],
                "name": "Data Processing Agreement",
                "desc": "Standard DPA for GDPR and CCPA compliance.",
                "tags": json.dumps(["DPA", "GDPR", "CCPA", "Privacy"]),
                "owner": "Privacy Team", "dept": "Legal",
                "status": "approved", "count": 15, "by": "admin",
            },
        )

        dpa_vars = json.dumps([
            {"key": "CompanyName", "label": "Company Name", "field_type": "text", "is_required": True, "display_order": 1, "section": "Parties"},
            {"key": "VendorName", "label": "Processor Name", "field_type": "text", "is_required": True, "display_order": 2, "section": "Parties"},
            {"key": "EffectiveDate", "label": "Effective Date", "field_type": "date", "is_required": True, "display_order": 3, "section": "Dates"},
            {"key": "RetentionPeriod", "label": "Retention Period (days)", "field_type": "number", "is_required": True, "display_order": 4, "section": "Dates"},
            {"key": "DataTypes", "label": "Types of Personal Data", "field_type": "text", "is_required": True, "display_order": 5, "section": "Scope"},
            {"key": "Jurisdiction", "label": "Governing Law", "field_type": "text", "is_required": True, "display_order": 6, "section": "Legal"},
            {"key": "BusinessOwner", "label": "Business Owner", "field_type": "text", "is_required": True, "display_order": 7, "section": "Parties"},
        ])

        dpa_content = """DATA PROCESSING AGREEMENT

This DPA is entered into as of {{EffectiveDate}} by {{CompanyName}} and {{VendorName}}.

1. PROCESSING OF PERSONAL DATA
The Processor shall process the following categories of personal data: {{DataTypes}}.

2. RETENTION
Personal data shall be retained for no longer than {{RetentionPeriod}} days.

3. GOVERNING LAW
This DPA shall be governed by {{Jurisdiction}}.

4. CONTACT
{{BusinessOwner}} shall serve as the data protection contact.

IN WITNESS WHEREOF, the parties have executed this DPA.

{{CompanyName}}
By: {{BusinessOwner}}

{{VendorName}}
By: {{VendorName}}"""

        await session.execute(
            sa_text("""
                INSERT INTO template_versions (id, tenant_id, template_id, version_number, label, status, variables, placeholder_content, file_name, created_by, created_at)
                VALUES (:id, :t, :tid, :vnum, :label, :status, :vars, :content, :fname, :by, NOW())
            """),
            {
                "id": dpa_ver_id, "t": tenant_id, "tid": dpa_id,
                "vnum": 1, "label": "v1.0 - Initial", "status": "approved",
                "vars": dpa_vars, "content": dpa_content, "fname": "DPA_v1.docx", "by": "admin",
            },
        )
        await session.execute(
            sa_text("UPDATE contract_templates SET current_version_id = :vid WHERE id = :id"),
            {"vid": dpa_ver_id, "id": dpa_id},
        )

        # ── Consulting Agreement Template ────────────────────────────
        ca_id = str(uuid.uuid4())
        ca_ver_id = str(uuid.uuid4())
        await session.execute(
            sa_text("""
                INSERT INTO contract_templates (id, tenant_id, category_id, name, description, tags, owner, department, status, usage_count, created_by, created_at, updated_at)
                VALUES (:id, :t, :cat, :name, :desc, :tags, :owner, :dept, :status, :count, :by, NOW(), NOW())
            """),
            {
                "id": ca_id, "t": tenant_id, "cat": cat_ids["consulting"],
                "name": "Consulting Agreement",
                "desc": "Standard consulting agreement for independent contractor engagements.",
                "tags": json.dumps(["Consulting", "Services", "Contractor"]),
                "owner": "HR Team", "dept": "Legal",
                "status": "approved", "count": 6, "by": "admin",
            },
        )

        ca_vars = json.dumps([
            {"key": "CompanyName", "label": "Company Name", "field_type": "text", "is_required": True, "display_order": 1, "section": "Parties"},
            {"key": "ConsultantName", "label": "Consultant Name", "field_type": "text", "is_required": True, "display_order": 2, "section": "Parties"},
            {"key": "EffectiveDate", "label": "Effective Date", "field_type": "date", "is_required": True, "display_order": 3, "section": "Dates"},
            {"key": "TermMonths", "label": "Term (months)", "field_type": "number", "is_required": True, "display_order": 4, "section": "Dates"},
            {"key": "EngagementFee", "label": "Engagement Fee", "field_type": "currency", "is_required": True, "display_order": 5, "section": "Financials"},
            {"key": "Jurisdiction", "label": "Governing Law", "field_type": "text", "is_required": True, "display_order": 6, "section": "Legal"},
            {"key": "Scope", "label": "Scope of Work", "field_type": "text", "is_required": True, "display_order": 7, "section": "Scope"},
            {"key": "BusinessOwner", "label": "Business Owner", "field_type": "text", "is_required": True, "display_order": 8, "section": "Parties"},
        ])

        ca_content = """CONSULTING AGREEMENT

This Consulting Agreement is entered into as of {{EffectiveDate}} by {{CompanyName}} and {{ConsultantName}}.

1. SCOPE OF WORK
{{Scope}}

2. COMPENSATION
Company shall pay {{ConsultantName}} a fee of {{EngagementFee}}.

3. TERM
This Agreement shall continue for {{TermMonths}} months.

4. GOVERNING LAW
This Agreement shall be governed by {{Jurisdiction}}.

5. CONTACT
{{BusinessOwner}} shall serve as the primary contact.

IN WITNESS WHEREOF, the parties have executed this Agreement.

{{CompanyName}}
By: {{BusinessOwner}}

{{ConsultantName}}
By: {{ConsultantName}}"""

        await session.execute(
            sa_text("""
                INSERT INTO template_versions (id, tenant_id, template_id, version_number, label, status, variables, placeholder_content, file_name, created_by, created_at)
                VALUES (:id, :t, :tid, :vnum, :label, :status, :vars, :content, :fname, :by, NOW())
            """),
            {
                "id": ca_ver_id, "t": tenant_id, "tid": ca_id,
                "vnum": 1, "label": "v1.0 - Initial", "status": "approved",
                "vars": ca_vars, "content": ca_content, "fname": "Consulting_v1.docx", "by": "admin",
            },
        )
        await session.execute(
            sa_text("UPDATE contract_templates SET current_version_id = :vid WHERE id = :id"),
            {"vid": ca_ver_id, "id": ca_id},
        )

        await session.commit()
        print(f"Seeded {len(categories)} categories, 5 templates (MSA, NDA, SOW, DPA, Consulting)")

        # ── Seed Clause Library ──────────────────────────────────────
        clauses = [
            {"id": str(uuid.uuid4()), "clause_type": "confidentiality", "title": "Confidentiality Obligations",
             "content": "Each party agrees to hold the other's Confidential Information in strict confidence and not to disclose such information to any third party without the prior written consent of the disclosing party. This obligation shall survive the termination of this Agreement.",
             "risk_level": "high", "category": "Standard", "is_required": True, "ai_rewrite_allowed": False},
            {"id": str(uuid.uuid4()), "clause_type": "liability", "title": "Limitation of Liability",
             "content": "Neither party shall be liable to the other for any indirect, incidental, special, consequential, or punitive damages. Total liability shall not exceed the total fees paid under this Agreement.",
             "risk_level": "critical", "category": "Standard", "is_required": True, "ai_rewrite_allowed": True},
            {"id": str(uuid.uuid4()), "clause_type": "payment", "title": "Payment Terms",
             "content": "All invoices shall be payable within thirty (30) days of receipt. Late payments shall accrue interest at the rate of 1.5% per month.",
             "risk_level": "medium", "category": "Financial", "is_required": True, "ai_rewrite_allowed": True},
            {"id": str(uuid.uuid4()), "clause_type": "governing_law", "title": "Governing Law",
             "content": "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of laws principles.",
             "risk_level": "medium", "category": "Legal", "is_required": True, "ai_rewrite_allowed": False},
            {"id": str(uuid.uuid4()), "clause_type": "termination", "title": "Termination for Convenience",
             "content": "Either party may terminate this Agreement upon thirty (30) days written notice. Upon termination, each party shall return or destroy the other's Confidential Information.",
             "risk_level": "low", "category": "Standard", "is_required": False, "ai_rewrite_allowed": True},
            {"id": str(uuid.uuid4()), "clause_type": "indemnification", "title": "Indemnification",
             "content": "Each party shall indemnify, defend, and hold harmless the other party from and against any and all claims, damages, losses, and expenses arising out of or related to a breach of this Agreement.",
             "risk_level": "critical", "category": "Standard", "is_required": False, "ai_rewrite_allowed": True},
            {"id": str(uuid.uuid4()), "clause_type": "insurance", "title": "Insurance Requirements",
             "content": "Vendor shall maintain commercial general liability insurance with limits of not less than $1,000,000 per occurrence and $2,000,000 aggregate.",
             "risk_level": "medium", "category": "Compliance", "is_required": False, "ai_rewrite_allowed": False},
            {"id": str(uuid.uuid4()), "clause_type": "warranty", "title": "Disclaimer of Warranties",
             "content": "EXCEPT AS EXPRESSLY SET FORTH HEREIN, THE SERVICES ARE PROVIDED 'AS IS' AND VENDOR DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING ANY WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.",
             "risk_level": "medium", "category": "Standard", "is_required": False, "ai_rewrite_allowed": False},
            {"id": str(uuid.uuid4()), "clause_type": "dispute_resolution", "title": "Dispute Resolution",
             "content": "Any dispute arising out of this Agreement shall first be resolved through good-faith negotiations. If unresolved, the dispute shall be submitted to binding arbitration in accordance with the rules of the American Arbitration Association.",
             "risk_level": "medium", "category": "Legal", "is_required": False, "ai_rewrite_allowed": False},
            {"id": str(uuid.uuid4()), "clause_type": "data_protection", "title": "Data Protection (GDPR)",
             "content": "Each party shall process personal data in compliance with applicable data protection laws, including the General Data Protection Regulation (GDPR) where applicable. Both parties shall implement appropriate technical and organizational measures.",
             "risk_level": "high", "category": "Compliance", "is_required": False, "ai_rewrite_allowed": True},
        ]

        clause_ids = {}
        for cl in clauses:
            clause_ids[cl["title"]] = cl["id"]
            await session.execute(
                sa_text("""
                    INSERT INTO template_clauses (id, tenant_id, clause_type, title, content, risk_level, category, is_required, ai_rewrite_allowed, status, version, created_by, created_at, updated_at)
                    VALUES (:id, :t, :type, :title, :content, :risk, :cat, :req, :ai, 'published', 1, 'admin', NOW(), NOW())
                """),
                {"id": cl["id"], "t": tenant_id, "type": cl["clause_type"], "title": cl["title"],
                 "content": cl["content"], "risk": cl["risk_level"], "cat": cl["category"],
                 "req": cl["is_required"], "ai": cl["ai_rewrite_allowed"]},
            )

        # Link clauses to templates
        template_links = [
            (msa_id, msa_ver_id, [("Confidentiality Obligations", 0, True), ("Limitation of Liability", 1, True),
             ("Payment Terms", 2, True), ("Governing Law", 3, True),
             ("Termination for Convenience", 4, False), ("Indemnification", 5, False),
             ("Disclaimer of Warranties", 6, False)]),
            (nda_id, nda_ver_id, [("Confidentiality Obligations", 0, True), ("Governing Law", 1, True),
             ("Termination for Convenience", 2, False)]),
            (sow_id, sow_ver_id, [("Payment Terms", 0, True), ("Limitation of Liability", 1, True),
             ("Dispute Resolution", 2, False)]),
            (dpa_id, dpa_ver_id, [("Data Protection (GDPR)", 0, True), ("Confidentiality Obligations", 1, True),
             ("Governing Law", 2, True)]),
            (ca_id, ca_ver_id, [("Limitation of Liability", 0, True), ("Payment Terms", 1, True),
             ("Governing Law", 2, True), ("Indemnification", 3, False),
             ("Insurance Requirements", 4, False)]),
        ]
        for tid, ver_id, refs in template_links:
            for title, order, required in refs:
                await session.execute(
                    sa_text("""INSERT INTO template_clause_refs (id, tenant_id, template_id, template_version_id, clause_id, clause_version, sort_order, is_required, created_at) VALUES (:id, :t, :tid, :ver_id, :cid, 1, :order, :req, NOW())"""),
                    {"id": str(uuid.uuid4()), "t": tenant_id, "tid": tid, "ver_id": ver_id,
                     "cid": clause_ids[title], "order": order, "req": required},
                )

        await session.commit()
        print(f"Seeded {len(clauses)} clauses, linked to 5 templates")

    await engine.dispose()


asyncio.run(seed())
