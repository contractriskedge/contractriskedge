"""
Seed the existing negotiation session with sample clauses and redlines
so the workspace has data to display.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone

# ── Sample clause data based on CONTRACT_03_SaaS_HighRisk.docx ──

SAMPLE_CLAUSES = [
    {
        "clauseId": "clause-001",
        "title": "Limitation of Liability",
        "sectionNumber": "8.1",
        "content": "Neither party shall be liable to the other for any indirect, incidental, special, consequential or punitive damages, including but not limited to loss of profits, loss of data, or business interruption, arising out of or relating to this Agreement, regardless of the form of action, whether in contract, tort, or otherwise, even if such party has been advised of the possibility of such damages. The total cumulative liability of either party arising out of or relating to this Agreement shall not exceed the total fees paid by Customer to Provider during the twelve (12) months immediately preceding the event giving rise to such liability.",
        "riskLevel": "critical",
        "category": "liability",
    },
    {
        "clauseId": "clause-002",
        "title": "Indemnification",
        "sectionNumber": "9.1",
        "content": "Provider agrees to indemnify, defend, and hold Customer harmless from and against any and all claims, damages, losses, liabilities, costs, and expenses arising out of or relating to any third-party claim that the Services infringe any patent, copyright, trademark, or trade secret. Customer agrees to indemnify and hold Provider harmless from any claims arising from Customer's use of the Services in violation of applicable law.",
        "riskLevel": "high",
        "category": "indemnification",
    },
    {
        "clauseId": "clause-003",
        "title": "Data Protection and GDPR",
        "sectionNumber": "10.2",
        "content": "Provider shall implement and maintain appropriate technical and organizational measures to protect Personal Data against accidental or unlawful destruction, loss, alteration, unauthorized disclosure or access. Both parties shall comply with all applicable data protection laws and regulations, including the General Data Protection Regulation (GDPR) where applicable.",
        "riskLevel": "high",
        "category": "gdpr",
    },
    {
        "clauseId": "clause-004",
        "title": "Termination for Convenience",
        "sectionNumber": "11.3",
        "content": "Either party may terminate this Agreement for any reason upon ninety (90) days prior written notice to the other party. In the event of termination, Customer shall pay all fees due through the effective date of termination. Provider shall return or destroy all Customer Confidential Information within thirty (30) days of termination.",
        "riskLevel": "medium",
        "category": "termination",
    },
    {
        "clauseId": "clause-005",
        "title": "Confidentiality",
        "sectionNumber": "7.1",
        "content": "Each party agrees to hold the other's Confidential Information in strict confidence and not to disclose such information to any third party without the prior written consent of the disclosing party. This obligation shall survive termination of this Agreement for a period of three (3) years. Confidential Information shall not include information that is or becomes publicly known through no fault of the receiving party.",
        "riskLevel": "medium",
        "category": "confidentiality",
    },
    {
        "clauseId": "clause-006",
        "title": "Service Level Agreement",
        "sectionNumber": "4.1",
        "content": "Provider shall maintain system availability of at least 99.9% uptime, measured monthly. If Provider fails to meet this SLA, Customer shall be entitled to service credits as follows: (a) 99.0-99.9%: 5% credit; (b) 95.0-98.9%: 10% credit; (c) below 95.0%: 25% credit. Credits shall not exceed 25% of monthly fees and shall be Customer's sole remedy for SLA failures.",
        "riskLevel": "high",
        "category": "sla",
    },
]

SAMPLE_REDLINES = [
    {
        "clauseId": "clause-001",
        "type": "modification",
        "title": "Reduce liability cap from 12 months to 6 months",
        "originalText": "The total cumulative liability of either party arising out of or relating to this Agreement shall not exceed the total fees paid by Customer to Provider during the twelve (12) months immediately preceding the event giving rise to such liability.",
        "modifiedText": "The total cumulative liability of either party arising out of or relating to this Agreement shall not exceed the total fees paid by Customer to Provider during the six (6) months immediately preceding the event giving rise to such liability.",
        "riskLevel": "critical",
        "status": "pending",
        "aiGenerated": True,
    },
    {
        "clauseId": "clause-001",
        "type": "addition",
        "title": "Add liability cap exception for GDPR fines",
        "originalText": "",
        "modifiedText": "Notwithstanding the foregoing, the limitation of liability shall not apply to: (i) either party's indemnification obligations; (ii) either party's breach of confidentiality; (iii) either party's infringement of intellectual property rights; or (iv) damages arising from gross negligence or willful misconduct.",
        "riskLevel": "critical",
        "status": "pending",
        "aiGenerated": True,
    },
    {
        "clauseId": "clause-002",
        "type": "modification",
        "title": "Extend indemnification to cover data breach",
        "originalText": "Provider agrees to indemnify, defend, and hold Customer harmless from and against any and all claims, damages, losses, liabilities, costs, and expenses arising out of or relating to any third-party claim that the Services infringe any patent, copyright, trademark, or trade secret.",
        "modifiedText": "Provider agrees to indemnify, defend, and hold Customer harmless from and against any and all claims, damages, losses, liabilities, costs, and expenses arising out of or relating to: (a) any third-party claim that the Services infringe any patent, copyright, trademark, or trade secret; (b) any data breach or security incident caused by Provider's failure to maintain adequate security measures; and (c) any violation of applicable data protection laws by Provider or its subcontractors.",
        "riskLevel": "high",
        "status": "pending",
        "aiGenerated": True,
    },
    {
        "clauseId": "clause-003",
        "type": "modification",
        "title": "Strengthen GDPR data protection obligations",
        "originalText": "Provider shall implement and maintain appropriate technical and organizational measures to protect Personal Data against accidental or unlawful destruction, loss, alteration, unauthorized disclosure or access.",
        "modifiedText": "Provider shall implement and maintain appropriate technical and organizational measures to protect Personal Data against accidental or unlawful destruction, loss, alteration, unauthorized disclosure or access, including but not limited to: encryption at rest and in transit, regular security assessments, access controls, incident response procedures, and data breach notification within 48 hours.",
        "riskLevel": "high",
        "status": "pending",
        "aiGenerated": True,
    },
    {
        "clauseId": "clause-004",
        "type": "modification",
        "title": "Reduce termination notice from 90 to 30 days",
        "originalText": "Either party may terminate this Agreement for any reason upon ninety (90) days prior written notice to the other party.",
        "modifiedText": "Either party may terminate this Agreement for any reason upon thirty (30) days prior written notice to the other party.",
        "riskLevel": "medium",
        "status": "pending",
        "aiGenerated": False,
    },
    {
        "clauseId": "clause-005",
        "type": "modification",
        "title": "Extend confidentiality survival to 5 years",
        "originalText": "This obligation shall survive termination of this Agreement for a period of three (3) years.",
        "modifiedText": "This obligation shall survive termination of this Agreement for a period of five (5) years.",
        "riskLevel": "medium",
        "status": "pending",
        "aiGenerated": False,
    },
    {
        "clauseId": "clause-006",
        "type": "modification",
        "title": "Increase SLA uptime to 99.95% with higher credits",
        "originalText": "Provider shall maintain system availability of at least 99.9% uptime, measured monthly. If Provider fails to meet this SLA, Customer shall be entitled to service credits as follows: (a) 99.0-99.9%: 5% credit; (b) 95.0-98.9%: 10% credit; (c) below 95.0%: 25% credit.",
        "modifiedText": "Provider shall maintain system availability of at least 99.95% uptime, measured monthly. If Provider fails to meet this SLA, Customer shall be entitled to service credits as follows: (a) 99.9-99.95%: 10% credit; (b) 99.0-99.89%: 20% credit; (c) 95.0-98.9%: 35% credit; (d) below 95.0%: 50% credit.",
        "riskLevel": "high",
        "status": "pending",
        "aiGenerated": True,
    },
]

SAMPLE_ISSUES = [
    {
        "clauseId": "clause-001",
        "title": "Liability cap too low at 12 months",
        "description": "The 12-month liability cap is below market standard for enterprise SaaS. Should be increased to 24 months or removed for key risk areas.",
        "severity": "critical",
        "status": "open",
        "category": "risk",
    },
    {
        "clauseId": "clause-002",
        "title": "Indemnification does not cover data breach",
        "description": "The indemnification clause does not explicitly cover data breach scenarios. This is a significant gap given the sensitivity of data being processed.",
        "severity": "high",
        "status": "open",
        "category": "legal",
    },
    {
        "clauseId": "clause-003",
        "title": "GDPR compliance needs strengthening",
        "description": "The data protection clause lacks specific security measures and breach notification timelines required under GDPR Article 33.",
        "severity": "high",
        "status": "open",
        "category": "compliance",
    },
    {
        "clauseId": "clause-006",
        "title": "SLA credits insufficient",
        "description": "The maximum 25% credit is below industry standard for critical enterprise systems. Market standard is 50% for severe outages.",
        "severity": "medium",
        "status": "open",
        "category": "commercial",
    },
]


async def seed_negotiation():
    """Seed the negotiation session with sample data via direct API calls."""
    import httpx

    session_id = "4f085714-f492-40c8-9bad-900be6c49949"
    base_url = "http://localhost:8000/api/v1"

    # Get auth token
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{base_url}/auth/token", json={"username": "admin", "password": "admin"})
        token = r.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        # 1. Create a version with clauses
        version_data = {
            "label": "Original Contract v1",
            "author": "System",
            "status": "current",
            "clauses": SAMPLE_CLAUSES,
            "changeSummary": "Initial import from CONTRACT_03_SaaS_HighRisk.docx",
        }
        print(f"Creating version with {len(SAMPLE_CLAUSES)} clauses...")
        r = await client.post(
            f"{base_url}/negotiations/{session_id}/versions",
            json=version_data,
            headers=headers,
        )
        if r.status_code in (200, 201):
            print(f"  ✅ Version created: {r.status_code}")
        else:
            print(f"  ❌ Version failed: {r.status_code} — {r.text[:200]}")

        # 2. Create redlines
        print(f"Creating {len(SAMPLE_REDLINES)} redlines...")
        for i, redline in enumerate(SAMPLE_REDLINES):
            r = await client.post(
                f"{base_url}/negotiations/{session_id}/redlines",
                json=redline,
                headers=headers,
            )
            if r.status_code in (200, 201):
                print(f"  ✅ Redline {i+1}: {redline['title'][:50]}")
            else:
                print(f"  ❌ Redline {i+1} failed: {r.status_code} — {r.text[:200]}")

        # 3. Create issues
        print(f"Creating {len(SAMPLE_ISSUES)} issues...")
        for i, issue in enumerate(SAMPLE_ISSUES):
            r = await client.post(
                f"{base_url}/negotiations/{session_id}/issues",
                json=issue,
                headers=headers,
            )
            if r.status_code in (200, 201):
                print(f"  ✅ Issue {i+1}: {issue['title'][:50]}")
            else:
                print(f"  ❌ Issue {i+1} failed: {r.status_code} — {r.text[:200]}")

        # 4. Update session title
        r = await client.patch(
            f"{base_url}/negotiations/{session_id}",
            json={"contractTitle": "CONTRACT_03_SaaS_HighRisk.docx — SaaS Agreement"},
            headers=headers,
        )
        if r.status_code in (200, 201):
            print(f"  ✅ Session title updated")
        else:
            print(f"  ⚠️ Title update: {r.status_code}")

    print("\n✅ Seeding complete! Refresh the negotiation page.")


if __name__ == "__main__":
    asyncio.run(seed_negotiation())
