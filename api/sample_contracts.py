"""Sample contracts for testing the redline engine and risk analysis.

Provides 10 full-length sample contracts across 5 contract types (MSA, NDA,
Software License, Employment, Lease) with clauses covering all 8 redline
clause types. Each contract is realistic and ready for testing.

Usage:
    from sample_contracts import SAMPLE_CONTRACTS, get_contract, list_contracts

    # List available contracts
    print(list_contracts())

    # Get a specific contract
    msa = get_contract("msa_techservices")

    # Get all contracts of a type
    ndas = [c for c in SAMPLE_CONTRACTS if c["contract_type"] == "nda"]
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

# ── Contract Type Labels ────────────────────────────────────────────────────

CONTRACT_TYPE_LABELS: Dict[str, str] = {
    "msa": "Master Service Agreement",
    "nda": "Non-Disclosure Agreement",
    "license": "Software License Agreement",
    "employment": "Employment Agreement",
    "lease": "Commercial Lease Agreement",
}

# ── 1. Master Service Agreement — TechServices ──────────────────────────────

MSA_TECHSERVICES: Dict[str, Any] = {
    "contract_id": "sample-msa-001",
    "contract_type": "msa",
    "title": "Master Service Agreement — TechSolutions Inc. & ClientCo",
    "parties": {
        "provider": "TechSolutions Inc., a Delaware corporation",
        "client": "ClientCo LLC, a New York limited liability company",
    },
    "effective_date": "January 15, 2026",
    "governing_law": "New York",
    "deal_size_tier": "large",
    "industry": "technology",
    "scenario": "Enterprise IT managed services, $2.5M annual contract, 3-year term",
    "clauses": {
        "liability_caps": {
            "section": "10. Limitation of Liability",
            "original_text": (
                "10.1 EXCLUSION OF DAMAGES. IN NO EVENT SHALL EITHER PARTY BE LIABLE TO THE "
                "OTHER FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, "
                "INCLUDING BUT NOT LIMITED TO LOST PROFITS, LOST REVENUE, OR LOST DATA, EVEN IF "
                "ADVISED OF THE POSSIBILITY THEREOF.\n\n"
                "10.2 LIABILITY CAP. EACH PARTY'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR "
                "RELATED TO THIS AGREEMENT, WHETHER IN CONTRACT, TORT, OR OTHERWISE, SHALL NOT "
                "EXCEED $50,000.\n\n"
                "10.3 NO EXCLUSIONS. The limitations set forth in this Section 10 shall apply "
                "notwithstanding the failure of essential purpose of any limited remedy and "
                "regardless of the cause of action."
            ),
            "risk_issues": [
                "$50K cap is too low for a $2.5M contract (only 2% of contract value)",
                "No carve-outs for fraud, IP infringement, confidentiality, or indemnification",
                "'Failure of essential purpose' language may be challenged under UCC 2-719",
                "No mutual cap — applies to both parties equally but provider has more exposure",
            ],
        },
        "indemnification": {
            "section": "11. Indemnification",
            "original_text": (
                "11.1 Provider Indemnity. Provider shall indemnify, defend, and hold harmless "
                "Client from and against any and all claims, losses, damages, liabilities, costs, "
                "and expenses (including reasonable attorneys' fees) arising out of or relating "
                "to this Agreement or the Services provided hereunder.\n\n"
                "11.2 Client Indemnity. Client shall indemnify, defend, and hold harmless Provider "
                "from and against any and all claims arising out of or relating to Client's use "
                "of the Services.\n\n"
                "11.3 Control of Defense. The indemnifying party shall have sole control of the "
                "defense and settlement of any claim. The indemnified party shall cooperate as "
                "reasonably requested."
            ),
            "risk_issues": [
                "Provider indemnity is overly broad — 'arising out of or relating to' covers everything",
                "No limitation to claims caused by provider's negligence or breach",
                "No IP infringement indemnity specifically",
                "Client indemnity has no 'proportionate fault' limitation",
                "Sole control of defense with no settlement consent right for indemnified party",
            ],
        },
        "ip_ownership": {
            "section": "12. Intellectual Property",
            "original_text": (
                "12.1 Ownership. All work product, deliverables, software, documentation, and "
                "other materials created by Provider under this Agreement shall be owned "
                "exclusively by Client.\n\n"
                "12.2 Pre-Existing IP. Provider retains ownership of all pre-existing tools, "
                "libraries, and methodologies used in performing the Services.\n\n"
                "12.3 License. Client receives a non-exclusive, non-transferable, royalty-free "
                "license to use any pre-existing IP incorporated into the deliverables."
            ),
            "risk_issues": [
                "No express assignment language — 'work made for hire' alone may be insufficient",
                "License to pre-existing IP is non-transferable — restricts M&A flexibility",
                "No moral rights waiver",
                "No warranty that deliverables don't infringe third-party IP",
                "No definition of 'pre-existing tools, libraries, and methodologies'",
            ],
        },
        "payment_terms": {
            "section": "4. Fees and Payment",
            "original_text": (
                "4.1 Fees. Client shall pay Provider the fees set forth in each Statement of "
                "Work.\n\n"
                "4.2 Invoicing. Provider shall invoice Client monthly in arrears. All invoices "
                "are due within 30 days of receipt.\n\n"
                "4.3 Late Payment. Late payments shall accrue interest at 1.5% per month.\n\n"
                "4.4 Auto-Renewal. This Agreement shall automatically renew for successive "
                "one-year terms unless either party provides notice of non-renewal at least 30 "
                "days prior to the end of the then-current term.\n\n"
                "4.5 Price Increases. Provider may increase fees annually upon 30 days notice."
            ),
            "risk_issues": [
                "Auto-renewal with only 30 days notice — easy to miss",
                "No cap on annual price increases",
                "No obligation to provide renewal pricing in advance",
                "Late payment interest rate may be usurious in some states (18% APR)",
                "No suspension of service right for non-payment",
                "No setoff rights provision",
            ],
        },
        "governing_law": {
            "section": "15. Governing Law",
            "original_text": (
                "15.1 Governing Law. This Agreement shall be governed by the laws of the State "
                "of New York.\n\n"
                "15.2 Venue. The parties submit to the exclusive jurisdiction of the courts "
                "located in New York County, New York.\n\n"
                "15.3 Waiver of Jury Trial. Each party waives any right to trial by jury."
            ),
            "risk_issues": [
                "Exclusive venue in NYC may be inconvenient for remote parties",
                "No arbitration option for cost-effective dispute resolution",
                "Jury waiver has no exception for fraud or willful misconduct",
                "No 'knowing and voluntary' acknowledgment for jury waiver enforceability",
                "No injunctive relief carve-out for IP/confidentiality breaches",
            ],
        },
        "termination_rights": {
            "section": "13. Term and Termination",
            "original_text": (
                "13.1 Term. This Agreement shall commence on the Effective Date and continue "
                "for an initial term of three (3) years.\n\n"
                "13.2 Termination for Convenience. Provider may terminate this Agreement at any "
                "time upon 90 days written notice. Client may not terminate for convenience.\n\n"
                "13.3 Termination for Cause. Either party may terminate this Agreement upon 30 "
                "days written notice of a material breach that remains uncured. Provider may "
                "terminate immediately if Client fails to pay any amount when due.\n\n"
                "13.4 Effect of Termination. Upon termination, Client's access to the Services "
                "shall be immediately terminated. Provider shall have no obligation to retain "
                "Client's data."
            ),
            "risk_issues": [
                "Termination for convenience is one-sided — only provider can terminate",
                "No cure period for payment breach — immediate termination is disproportionate",
                "No post-termination data retrieval or transition assistance",
                "No survival clause for key provisions (confidentiality, indemnification)",
                "No early termination fee or wind-down compensation",
            ],
        },
        "confidentiality": {
            "section": "9. Confidentiality",
            "original_text": (
                "9.1 Definition. Confidential Information means all information disclosed by "
                "one party to the other in connection with this Agreement.\n\n"
                "9.2 Obligations. The receiving party shall maintain the confidentiality of "
                "Confidential Information and shall not disclose it to third parties.\n\n"
                "9.3 Term. Confidentiality obligations shall survive for a period of two (2) "
                "years following termination of this Agreement.\n\n"
                "9.4 Exclusions. Confidential Information does not include information that is "
                "publicly known or independently developed."
            ),
            "risk_issues": [
                "Definition is overly broad — no marking requirement or oral confirmation process",
                "'Maintain confidentiality' is vague — no standard of care specified",
                "No need-to-know access limitation",
                "No breach notification obligation",
                "2-year survival is too short for trade secrets (should be perpetual)",
                "No compelled disclosure notice provision",
                "'Independently developed' exclusion has no documentation requirement",
            ],
        },
        "force_majeure": {
            "section": "14. Force Majeure",
            "original_text": (
                "14.1 Force Majeure. Neither party shall be liable for delays or failures in "
                "performance resulting from acts of God, war, terrorism, or natural disasters.\n\n"
                "14.2 Effect. Performance shall be excused for the duration of the force majeure "
                "event."
            ),
            "risk_issues": [
                "No coverage for pandemics, cyberattacks, or government actions",
                "No notice requirement",
                "No mitigation obligation",
                "No termination right for extended force majeure",
                "No exclusion for payment obligations",
                "No definition of 'acts of God' — vague and subject to dispute",
            ],
        },
    },
}

# ── 2. Non-Disclosure Agreement — Standard Mutual NDA ───────────────────────

NDA_STANDARD: Dict[str, Any] = {
    "contract_id": "sample-nda-001",
    "contract_type": "nda",
    "title": "Mutual Non-Disclosure Agreement — DataPartner LLC & ClientCo",
    "parties": {
        "disclosing_party": "Each party (as Disclosing Party)",
        "receiving_party": "Each party (as Receiving Party)",
    },
    "effective_date": "February 1, 2026",
    "governing_law": "Delaware",
    "deal_size_tier": "medium",
    "industry": "technology",
    "scenario": "Mutual NDA for strategic partnership evaluation, $500K potential deal",
    "clauses": {
        "confidentiality": {
            "section": "1. Definition of Confidential Information",
            "original_text": (
                "1.1 'Confidential Information' means any and all information disclosed by "
                "one party (the 'Disclosing Party') to the other party (the 'Receiving Party') "
                "in connection with the Purpose, whether disclosed orally, in writing, or in "
                "any other form, including but not limited to business plans, financial data, "
                "customer information, technical data, trade secrets, and product roadmaps.\n\n"
                "1.2 Exclusions. Confidential Information does not include information that: "
                "(a) is or becomes publicly known through no fault of the Receiving Party; "
                "(b) was rightfully in the Receiving Party's possession prior to disclosure; "
                "(c) is rightfully disclosed to the Receiving Party by a third party without "
                "restriction; or (d) is independently developed by the Receiving Party without "
                "use of the Disclosing Party's Confidential Information."
            ),
            "risk_issues": [
                "No requirement to mark written information as confidential",
                "No requirement to confirm oral disclosures in writing within a reasonable time",
                "'Independently developed' exclusion has no documentation burden of proof",
                "No 'should have known' catch-all for unmarked information",
            ],
        },
        "confidentiality_obligations": {
            "section": "2. Obligations",
            "original_text": (
                "2.1 The Receiving Party shall: (a) use reasonable care to protect the "
                "Confidential Information from unauthorized use or disclosure; (b) limit access "
                "to Confidential Information to those employees with a need to know; and (c) not "
                "use Confidential Information except for the Purpose.\n\n"
                "2.2 The Receiving Party may disclose Confidential Information if required by "
                "law, provided that the Receiving Party gives the Disclosing Party prompt notice "
                "of such requirement.\n\n"
                "2.3 Upon the Disclosing Party's request, the Receiving Party shall return or "
                "destroy all Confidential Information."
            ),
            "risk_issues": [
                "'Reasonable care' is subjective — 'same degree of care' is stronger",
                "No specific security measures required (encryption, access controls)",
                "No breach notification timeline — 'prompt' is vague",
                "No obligation to certify destruction of Confidential Information",
                "No obligation to continue protecting retained copies (e.g., backups)",
            ],
        },
        "term": {
            "section": "5. Term",
            "original_text": (
                "5.1 This Agreement shall commence on the Effective Date and continue for a "
                "period of two (2) years.\n\n"
                "5.2 The obligations of confidentiality shall survive for a period of three (3) "
                "years following termination of this Agreement.\n\n"
                "5.3 Trade secrets shall be protected for as long as they remain trade secrets "
                "under applicable law."
            ),
            "risk_issues": [
                "3-year confidentiality term is short for sensitive business information",
                "No automatic termination provision for expired purpose",
                "No transition period for returning materials after termination",
            ],
        },
    },
}

# ── 3. Software License Agreement — CloudSoft Perpetual License ─────────────

SOFTWARE_LICENSE: Dict[str, Any] = {
    "contract_id": "sample-license-001",
    "contract_type": "license",
    "title": "Software License Agreement — CloudSoft Inc. & Enterprise Client",
    "parties": {
        "licensor": "CloudSoft Inc., a Delaware corporation",
        "licensee": "Enterprise Corp., a New York corporation",
    },
    "effective_date": "March 1, 2026",
    "governing_law": "Delaware",
    "deal_size_tier": "enterprise",
    "industry": "technology",
    "scenario": "Perpetual software license for enterprise CRM platform, $5M license fee, 20% annual maintenance",
    "clauses": {
        "ip_ownership": {
            "section": "2. License Grant",
            "original_text": (
                "2.1 License Grant. Licensor grants Licensee a non-exclusive, non-transferable, "
                "worldwide license to use the Licensed Software for Licensee's internal business "
                "purposes.\n\n"
                "2.2 Restrictions. Licensee shall not: (a) modify, adapt, or create derivative "
                "works of the Licensed Software; (b) reverse engineer, decompile, or disassemble "
                "the Licensed Software; (c) rent, lease, sublicense, or distribute the Licensed "
                "Software to third parties; or (d) use the Licensed Software to provide "
                "services to third parties.\n\n"
                "2.3 Ownership. Licensor retains all right, title, and interest in and to the "
                "Licensed Software, including all intellectual property rights. Licensee "
                "acquires no ownership rights.\n\n"
                "2.4 Feedback. Licensee may provide feedback regarding the Licensed Software. "
                "Licensor may use such feedback without restriction or compensation."
            ),
            "risk_issues": [
                "Non-transferable license restricts M&A activity (asset sales, mergers)",
                "'Internal business purposes' may be too narrow for some use cases",
                "Feedback clause gives licensor unlimited rights without compensation",
                "No right to use for disaster recovery or business continuity",
                "No license to third-party contractors working for licensee",
            ],
        },
        "liability_caps": {
            "section": "8. Limitation of Liability",
            "original_text": (
                "8.1 EXCLUSION OF DAMAGES. IN NO EVENT SHALL LICENSOR BE LIABLE FOR ANY "
                "INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES.\n\n"
                "8.2 LIABILITY CAP. LICENSOR'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR "
                "RELATED TO THIS AGREEMENT SHALL NOT EXCEED THE LICENSE FEES PAID BY LICENSEE "
                "IN THE PRECEDING 12 MONTHS.\n\n"
                "8.3 IP INFRINGEMENT. THE FOREGOING LIMITATIONS SHALL NOT APPLY TO CLAIMS "
                "ARISING FROM LICENSOR'S INFRINGEMENT OF THIRD-PARTY INTELLECTUAL PROPERTY "
                "RIGHTS."
            ),
            "risk_issues": [
                "Liability cap is one-sided — only limits licensor's liability",
                "No cap on licensee's liability (e.g., breach of license restrictions)",
                "Cap tied to 12 months fees — may be too low for perpetual license",
                "No carve-out for breach of confidentiality",
                "No carve-out for fraud or willful misconduct",
            ],
        },
        "indemnification": {
            "section": "9. Indemnification",
            "original_text": (
                "9.1 IP Indemnity. Licensor shall defend and indemnify Licensee against any "
                "third-party claim that the Licensed Software infringes a U.S. patent, copyright, "
                "or trade secret.\n\n"
                "9.2 Exclusions. Licensor shall have no obligation under this Section to the "
                "extent the claim arises from: (a) Licensee's modification of the Software; "
                "(b) combination of the Software with products not provided by Licensor; or "
                "(c) use of the Software in violation of this Agreement.\n\n"
                "9.3 Remedy. If the Software becomes subject to an infringement claim, Licensor "
                "may: (i) procure the right to continue using the Software; (ii) modify the "
                "Software to be non-infringing; or (iii) terminate the license and refund the "
                "license fee, depreciated on a straight-line basis over 36 months."
            ),
            "risk_issues": [
                "Indemnity only covers U.S. IP rights — not international",
                "No duty to defend — only indemnify after final judgment",
                "Refund on depreciated basis is unfair for perpetual license",
                "No obligation to cover attorneys' fees and defense costs",
                "No indemnity for trade secret misappropriation claims",
            ],
        },
        "termination_rights": {
            "section": "7. Term and Termination",
            "original_text": (
                "7.1 Term. This Agreement shall commence on the Effective Date and continue "
                "in perpetuity unless terminated as provided herein.\n\n"
                "7.2 Termination for Breach. Either party may terminate this Agreement upon 30 "
                "days written notice of a material breach that remains uncured.\n\n"
                "7.3 Termination for Insolvency. This Agreement shall automatically terminate "
                "if either party becomes insolvent, files for bankruptcy, or makes an assignment "
                "for the benefit of creditors.\n\n"
                "7.4 Effect of Termination. Upon termination, Licensee shall immediately cease "
                "use of the Licensed Software and certify in writing that all copies have been "
                "destroyed."
            ),
            "risk_issues": [
                "Automatic termination for insolvency may violate automatic stay under bankruptcy code",
                "No transition period for license termination",
                "No obligation to provide data export or migration assistance",
                "No survival of key provisions (confidentiality, limitation of liability)",
                "No license to continue using for post-termination transition",
            ],
        },
        "payment_terms": {
            "section": "3. Fees and Maintenance",
            "original_text": (
                "3.1 License Fee. Licensee shall pay a one-time license fee of $5,000,000 upon "
                "execution of this Agreement.\n\n"
                "3.2 Maintenance Fee. Licensee shall pay an annual maintenance fee equal to 20% "
                "of the license fee, payable in advance.\n\n"
                "3.3 Maintenance Increase. Licensor may increase the maintenance fee annually "
                "by up to the greater of 5% or the CPI increase.\n\n"
                "3.4 Late Payment. Late payments shall accrue interest at 1.5% per month."
            ),
            "risk_issues": [
                "No cap on maintenance increases tied to CPI — could be significant in high inflation",
                "No suspension of maintenance if fees disputed in good faith",
                "No audit right for usage compliance",
                "No most-favored-customer pricing protection",
                "Late fee at 1.5%/month (18% APR) may be usurious in some states",
            ],
        },
    },
}

# ── 4. Employment Agreement — Senior Engineer ───────────────────────────────

EMPLOYMENT_AGREEMENT: Dict[str, Any] = {
    "contract_id": "sample-employment-001",
    "contract_type": "employment",
    "title": "Employment Agreement — Senior Software Engineer",
    "parties": {
        "employer": "TechSolutions Inc.",
        "employee": "John Doe",
    },
    "effective_date": "January 1, 2026",
    "governing_law": "California",
    "deal_size_tier": "medium",
    "industry": "technology",
    "scenario": "Senior software engineer hire, $220K base salary, equity package, California employee",
    "clauses": {
        "ip_ownership": {
            "section": "6. Intellectual Property",
            "original_text": (
                "6.1 Assignment. Employee hereby assigns to Company all right, title, and "
                "interest in and to any and all inventions, discoveries, improvements, and "
                "original works of authorship (collectively, 'Inventions') that Employee "
                "conceives, develops, or reduces to practice during the period of employment.\n\n"
                "6.2 Exclusions. Inventions that Employee develops entirely on Employee's own "
                "time, without use of Company's equipment, supplies, facilities, or trade secret "
                "information, and that do not relate to Company's business or actual or "
                "anticipated research or development, are excluded.\n\n"
                "6.3 Disclosure. Employee shall promptly disclose all Inventions to Company."
            ),
            "risk_issues": [
                "Assignment is extremely broad — covers everything during employment",
                "Exclusion for own-time inventions is narrow and hard to prove",
                "'Relate to Company's business' is vague and could cover personal projects",
                "No obligation for Company to prosecute patents on assigned inventions",
                "No compensation for assigned inventions beyond salary",
            ],
        },
        "confidentiality": {
            "section": "5. Confidentiality",
            "original_text": (
                "5.1 Employee acknowledges that during employment, Employee will have access "
                "to Company's Confidential Information.\n\n"
                "5.2 Employee shall not, during or after employment, disclose or use any "
                "Confidential Information except as necessary to perform duties.\n\n"
                "5.3 Upon termination, Employee shall return all Company property and "
                "Confidential Information.\n\n"
                "5.4 Confidentiality obligations shall survive indefinitely."
            ),
            "risk_issues": [
                "No definition of Confidential Information",
                "No exception for compelled disclosure (subpoena, court order)",
                "No exception for reporting legal violations (whistleblower protections)",
                "Indefinite survival may be unenforceable for non-trade-secret information",
                "No obligation to provide advance notice of compelled disclosure",
            ],
        },
        "non_compete": {
            "section": "7. Non-Competition",
            "original_text": (
                "7.1 Non-Compete. During employment and for a period of twelve (12) months "
                "following termination for any reason, Employee shall not, directly or indirectly, "
                "engage in any business that competes with Company in any geographic area where "
                "Company does business.\n\n"
                "7.2 Non-Solicitation. Employee shall not, during the restricted period, solicit "
                "or encourage any Company employee to leave employment or any Company customer "
                "to reduce its business with Company.\n\n"
                "7.3 Non-Disparagement. Employee shall not make any statements that disparage "
                "Company or its officers, directors, or employees."
            ),
            "risk_issues": [
                "Non-compete is likely unenforceable in California (CA Bus & Prof Code § 16600)",
                "'Any business that competes' is overly broad",
                "'Any geographic area where Company does business' is worldwide and unreasonable",
                "No exception for ownership of passive investments (e.g., less than 1% of public company)",
                "No garden leave or compensation during restricted period",
                "Non-solicit of employees has no exception for general public solicitations",
            ],
        },
        "termination_rights": {
            "section": "4. Termination",
            "original_text": (
                "4.1 At-Will Employment. Employment is at-will and may be terminated by either "
                "party at any time, with or without cause or advance notice.\n\n"
                "4.2 Severance. Upon termination without cause, Employee shall receive: (a) "
                "three (3) months of base salary continuation; (b) COBRA reimbursement for three "
                "(3) months; and (c) accelerated vesting of 12 months of unvested equity.\n\n"
                "4.3 Termination for Cause. If Employee is terminated for cause, no severance "
                "shall be payable.\n\n"
                "4.4 Resignation. If Employee resigns without good reason, no severance shall "
                "be payable."
            ),
            "risk_issues": [
                "No definition of 'cause' — leaves room for employer to avoid severance",
                "No definition of 'good reason' for resignation",
                "Severance conditioned on release of claims (not stated but implied)",
                "No notice period for resignation",
                "No obligation to provide transition assistance",
            ],
        },
    },
}

# ── 5. Commercial Lease Agreement ───────────────────────────────────────────

COMMERCIAL_LEASE: Dict[str, Any] = {
    "contract_id": "sample-lease-001",
    "contract_type": "lease",
    "title": "Commercial Lease Agreement — Prime Office Properties & TenantCo",
    "parties": {
        "landlord": "Prime Office Properties LLC",
        "tenant": "TenantCo Inc.",
    },
    "effective_date": "April 1, 2026",
    "governing_law": "New York",
    "deal_size_tier": "large",
    "industry": "real_estate",
    "scenario": "Class A office space, 15,000 sq ft, 5-year lease, $75/sq ft annually, NYC",
    "clauses": {
        "payment_terms": {
            "section": "3. Rent and Additional Rent",
            "original_text": (
                "3.1 Base Rent. Tenant shall pay Base Rent in equal monthly installments of "
                "$93,750, payable in advance on the first day of each month.\n\n"
                "3.2 Rent Escalation. Base Rent shall increase annually by the greater of (a) "
                "four percent (4%) or (b) the percentage increase in CPI, but in no event less "
                "than three percent (3%).\n\n"
                "3.3 Additional Rent. Tenant shall pay its proportionate share of operating "
                "expenses, real estate taxes, and utilities as Additional Rent.\n\n"
                "3.4 Late Payment. Late payments shall incur a late fee of 5% of the overdue "
                "amount plus interest at 1.5% per month.\n\n"
                "3.5 Security Deposit. Tenant shall provide a security deposit of $281,250 "
                "(three months' Base Rent)."
            ),
            "risk_issues": [
                "Rent escalation has a 3% floor regardless of market conditions",
                "Operating expenses pass-through has no cap or audit right",
                "Late fee of 5% plus 1.5%/month interest may be excessive",
                "Security deposit amount is very high (3 months)",
                "No specification of interest on security deposit",
                "No grace period for late payment before late fee accrues",
            ],
        },
        "indemnification": {
            "section": "8. Indemnification and Insurance",
            "original_text": (
                "8.1 Tenant Indemnity. Tenant shall indemnify, defend, and hold harmless "
                "Landlord from and against any and all claims, damages, losses, liabilities, "
                "and expenses (including reasonable attorneys' fees) arising out of or relating "
                "to: (a) Tenant's use or occupancy of the Premises; (b) any activity, work, or "
                "thing done or permitted by Tenant; or (c) any breach of this Lease by Tenant.\n\n"
                "8.2 Landlord Indemnity. Landlord shall indemnify Tenant for claims arising "
                "from Landlord's negligence in operating the Building."
            ),
            "risk_issues": [
                "Tenant indemnity is extremely broad — 'arising out of or relating to' use of premises",
                "No carve-out for Landlord's own negligence",
                "Landlord indemnity is limited to 'negligence in operating the Building' — too narrow",
                "No mutual waiver of subrogation",
                "No cap on tenant's indemnification obligations",
            ],
        },
        "termination_rights": {
            "section": "12. Default and Remedies",
            "original_text": (
                "12.1 Event of Default. The following shall constitute an Event of Default: "
                "(a) failure to pay Rent when due; (b) failure to perform any other obligation "
                "under this Lease; (c) Tenant's insolvency or bankruptcy; or (d) abandonment "
                "of the Premises.\n\n"
                "12.2 Cure Period. Tenant shall have ten (10) days to cure a monetary default "
                "and thirty (30) days to cure a non-monetary default.\n\n"
                "12.3 Remedies. Upon an Event of Default, Landlord may: (a) terminate this "
                "Lease; (b) re-enter and re-take possession of the Premises; (c) accelerate "
                "all Rent due for the remainder of the Term; and (d) recover all costs of "
                "re-letting.\n\n"
                "12.4 Landlord Default. Landlord shall not be in default unless Tenant gives "
                "Landlord thirty (30) days written notice and Landlord fails to cure within "
                "a reasonable time."
            ),
            "risk_issues": [
                "10-day cure period for monetary default is very short",
                "No distinction between material and immaterial non-monetary defaults",
                "Acceleration of all remaining rent is a harsh remedy",
                "Landlord default provision is vague ('reasonable time') and one-sided",
                "Automatic default for bankruptcy may violate automatic stay",
                "No right for tenant to terminate for landlord's failure to maintain premises",
            ],
        },
        "force_majeure": {
            "section": "22. Force Majeure",
            "original_text": (
                "22.1 Landlord shall not be liable for delays in performance caused by strikes, "
                "materials shortages, or other causes beyond Landlord's reasonable control.\n\n"
                "22.2 Tenant's obligation to pay Rent shall not be excused by force majeure."
            ),
            "risk_issues": [
                "Force majeure only protects Landlord — not mutual",
                "No coverage for pandemics, government closures, or utility failures",
                "No notice requirement",
                "No termination right for extended force majeure",
                "No abatement of rent if premises are unusable due to force majeure",
            ],
        },
        "assignment": {
            "section": "14. Assignment and Subletting",
            "original_text": (
                "14.1 Tenant shall not assign this Lease or sublet any portion of the Premises "
                "without Landlord's prior written consent, which may be withheld in Landlord's "
                "sole and absolute discretion.\n\n"
                "14.2 Any assignment or sublease without consent shall be void.\n\n"
                "14.3 Landlord may recapture the Premises upon notice of proposed assignment."
            ),
            "risk_issues": [
                "Consent in 'sole and absolute discretion' is unreasonably restrictive",
                "No exception for assignments to affiliates or in connection with M&A",
                "Recapture right allows landlord to terminate lease if tenant finds a subtenant",
                "No sharing of sublease profit with tenant",
                "Any unauthorized assignment voids the lease — harsh remedy",
            ],
        },
    },
}

# ── 6. Master Service Agreement — Healthcare SaaS ───────────────────────────

MSA_HEALTHCARE: Dict[str, Any] = {
    "contract_id": "sample-msa-002",
    "contract_type": "msa",
    "title": "Master Service Agreement — HealthData SaaS & Regional Hospital",
    "parties": {
        "provider": "HealthData SaaS Inc., a Massachusetts corporation",
        "client": "Regional Hospital System, a non-profit healthcare provider",
    },
    "effective_date": "February 15, 2026",
    "governing_law": "Massachusetts",
    "deal_size_tier": "enterprise",
    "industry": "healthcare",
    "scenario": "HIPAA-regulated EHR data analytics platform, $8M over 5 years, includes PHI processing",
    "clauses": {
        "confidentiality": {
            "section": "9. Confidentiality and Data Protection",
            "original_text": (
                "9.1 Confidential Information. Includes all information disclosed by either "
                "party.\n\n"
                "9.2 HIPAA. Provider shall comply with applicable HIPAA requirements. A Business "
                "Associate Agreement is attached as Exhibit B.\n\n"
                "9.3 Data Security. Provider shall implement reasonable security measures to "
                "protect Client's data.\n\n"
                "9.4 Breach Notification. Provider shall notify Client of any security incident "
                "involving Client's data."
            ),
            "risk_issues": [
                "Definition of Confidential Information is too vague",
                "'Reasonable security measures' is subjective — no specific standards (NIST, SOC 2)",
                "Breach notification has no timeline — 'promptly' or specific hours",
                "No data retention or deletion policy",
                "No audit right for client to verify compliance",
                "No data localization or processing location restrictions",
            ],
        },
        "liability_caps": {
            "section": "10. Limitation of Liability",
            "original_text": (
                "10.1 EXCLUSION. NEITHER PARTY SHALL BE LIABLE FOR INDIRECT DAMAGES.\n\n"
                "10.2 CAP. EACH PARTY'S LIABILITY SHALL NOT EXCEED $500,000.\n\n"
                "10.3 DATA. PROVIDER SHALL HAVE NO LIABILITY FOR LOSS OR CORRUPTION OF DATA."
            ),
            "risk_issues": [
                "No liability for data loss is unacceptable for a healthcare data platform",
                "$500K cap is far too low for an $8M contract handling PHI",
                "No carve-out for HIPAA violations or regulatory fines",
                "No carve-out for breach of confidentiality",
                "No carve-out for fraud or willful misconduct",
            ],
        },
        "termination_rights": {
            "section": "13. Term and Termination",
            "original_text": (
                "13.1 Term. Five (5) years from Effective Date.\n\n"
                "13.2 Termination for Cause. Either party may terminate for material breach "
                "with 30 days cure period.\n\n"
                "13.3 Termination for Convenience. Neither party may terminate for convenience.\n\n"
                "13.4 Data Export. Upon termination, Provider shall provide Client's data in "
                "a commonly used format within 30 days.\n\n"
                "13.5 Transition Assistance. Provider shall provide up to 90 days of transition "
                "assistance at then-current rates."
            ),
            "risk_issues": [
                "No termination for convenience — locks both parties in for 5 years",
                "No termination for non-appropriation of funds (important for government entities)",
                "Transition assistance at 'then-current rates' could be very expensive",
                "No obligation to certify deletion of Client's data after transition",
                "30 days may be insufficient for large healthcare data sets",
            ],
        },
    },
}

# ── 7. SaaS Subscription Agreement — Startup-Friendly ───────────────────────

SAAS_AGREEMENT: Dict[str, Any] = {
    "contract_id": "sample-saas-001",
    "contract_type": "msa",
    "title": "SaaS Subscription Agreement — FastTrack SaaS & Startup Client",
    "parties": {
        "provider": "FastTrack SaaS Inc.",
        "client": "StartupCo LLC",
    },
    "effective_date": "May 1, 2026",
    "governing_law": "California",
    "deal_size_tier": "small",
    "industry": "technology",
    "scenario": "Project management SaaS, $24K/year, month-to-month, startup-friendly terms",
    "clauses": {
        "payment_terms": {
            "section": "4. Subscription Fees",
            "original_text": (
                "4.1 Fees. Client shall pay the subscription fees as set forth in the Order "
                "Form.\n\n"
                "4.2 Payment Terms. Fees are due within 30 days of invoice. Client may pay "
                "monthly or annually at Client's option.\n\n"
                "4.3 Late Payment. Late payments shall accrue interest at 1.0% per month.\n\n"
                "4.4 No Refunds. All fees are non-refundable except as expressly provided.\n\n"
                "4.5 Taxes. Client shall pay all applicable taxes."
            ),
            "risk_issues": [
                "No price protection or cap on future price increases",
                "No most-favored-customer pricing clause",
                "'All applicable taxes' may include taxes provider should bear",
                "No suspension right for non-payment — provider must keep serving",
            ],
        },
        "termination_rights": {
            "section": "6. Term and Termination",
            "original_text": (
                "6.1 Term. Month-to-month, commencing on the Start Date.\n\n"
                "6.2 Termination. Either party may terminate at any time upon 30 days written "
                "notice.\n\n"
                "6.3 Data Export. Upon termination, Client may export its data during the "
                "notice period.\n\n"
                "6.4 Refund. If Client terminates, Client shall receive a pro-rata refund of "
                "any prepaid fees."
            ),
            "risk_issues": [
                "30 days may be too short for enterprise clients to migrate",
                "Data export only available during notice period — not after termination",
                "No format specification for data export",
                "No certification of data deletion",
                "No transition assistance",
            ],
        },
        "liability_caps": {
            "section": "7. Limitation of Liability",
            "original_text": (
                "7.1 EXCLUSION. NEITHER PARTY SHALL BE LIABLE FOR INDIRECT DAMAGES.\n\n"
                "7.2 CAP. EACH PARTY'S LIABILITY SHALL NOT EXCEED THE FEES PAID IN THE "
                "PRECEDING 12 MONTHS.\n\n"
                "7.3 CARVE-OUTS. Section 7.1 and 7.2 shall not apply to: (a) breach of "
                "confidentiality; (b) indemnification obligations; (c) fraud or willful "
                "misconduct; or (d) infringement of intellectual property rights."
            ),
            "risk_issues": [
                "Fair and balanced for a startup-friendly SaaS agreement",
                "Carve-outs are comprehensive and market standard",
                "Cap tied to 12 months fees is proportional to contract value",
            ],
        },
    },
}

# ── 8. Independent Contractor Agreement ─────────────────────────────────────

CONTRACTOR_AGREEMENT: Dict[str, Any] = {
    "contract_id": "sample-contractor-001",
    "contract_type": "service_agreement",
    "title": "Independent Contractor Agreement — Freelance Developer",
    "parties": {
        "company": "TechSolutions Inc.",
        "contractor": "Jane Smith (Freelance Developer)",
    },
    "effective_date": "June 1, 2026",
    "governing_law": "New York",
    "deal_size_tier": "small",
    "industry": "technology",
    "scenario": "Freelance web developer, $150/hour, 6-month project, remote work",
    "clauses": {
        "ip_ownership": {
            "section": "5. Intellectual Property",
            "original_text": (
                "5.1 Work Product. All deliverables, code, designs, and other materials created "
                "by Contractor under this Agreement ('Work Product') shall be the sole and "
                "exclusive property of Company.\n\n"
                "5.2 Assignment. Contractor hereby irrevocably assigns to Company all right, "
                "title, and interest in the Work Product.\n\n"
                "5.3 Work for Hire. The Work Product shall be considered a work made for hire "
                "to the maximum extent permitted by law.\n\n"
                "5.4 Contractor retains ownership of its pre-existing tools and methodologies."
            ),
            "risk_issues": [
                "No license back for pre-existing tools incorporated into Work Product",
                "No definition of 'pre-existing tools and methodologies'",
                "No moral rights waiver",
                "No warranty that Work Product doesn't infringe third-party IP",
                "No representation that contractor has right to assign Work Product",
            ],
        },
        "indemnification": {
            "section": "8. Indemnification",
            "original_text": (
                "8.1 Contractor shall indemnify, defend, and hold harmless Company from any "
                "claims arising out of Contractor's services under this Agreement.\n\n"
                "8.2 Company shall indemnify Contractor from claims arising out of Company's "
                "use of the Work Product."
            ),
            "risk_issues": [
                "Contractor indemnity is overly broad — covers all claims from services",
                "No limitation to claims caused by contractor's negligence or breach",
                "No IP infringement indemnity from contractor",
                "No control of defense provisions",
                "No cap on indemnification obligations",
            ],
        },
        "termination_rights": {
            "section": "3. Term and Termination",
            "original_text": (
                "3.1 Term. This Agreement shall commence on June 1, 2026 and continue until "
                "December 31, 2026.\n\n"
                "3.2 Termination for Convenience. Company may terminate this Agreement at any "
                "time upon 14 days written notice. Contractor may not terminate for convenience.\n\n"
                "3.3 Termination for Cause. Either party may terminate for material breach "
                "with 10 days cure period.\n\n"
                "3.4 Payment upon Termination. Contractor shall be paid for all Services "
                "performed through the date of termination."
            ),
            "risk_issues": [
                "Termination for convenience is one-sided — only company can terminate",
                "14 days notice is short for contractor who may have turned down other work",
                "No compensation for work in progress or committed resources",
                "No transition assistance obligation",
                "No survival of IP assignment and confidentiality provisions",
            ],
        },
    },
}

# ── Master List ──────────────────────────────────────────────────────────────

SAMPLE_CONTRACTS: List[Dict[str, Any]] = [
    MSA_TECHSERVICES,
    NDA_STANDARD,
    SOFTWARE_LICENSE,
    EMPLOYMENT_AGREEMENT,
    COMMERCIAL_LEASE,
    MSA_HEALTHCARE,
    SAAS_AGREEMENT,
    CONTRACTOR_AGREEMENT,
]


def get_contract(contract_id: str) -> Optional[Dict[str, Any]]:
    """Get a sample contract by its ID.

    Args:
        contract_id: The contract_id to look up (e.g., 'sample-msa-001').

    Returns:
        The contract dict, or None if not found.
    """
    for contract in SAMPLE_CONTRACTS:
        if contract["contract_id"] == contract_id:
            return contract
    return None


def list_contracts() -> List[Dict[str, str]]:
    """List all available sample contracts.

    Returns:
        A list of dicts with contract_id, title, type, and industry.
    """
    return [
        {
            "contract_id": c["contract_id"],
            "title": c["title"],
            "contract_type": c["contract_type"],
            "industry": c["industry"],
            "deal_size_tier": c["deal_size_tier"],
            "clause_count": len(c["clauses"]),
        }
        for c in SAMPLE_CONTRACTS
    ]


def get_clauses_by_type(clause_type: str) -> List[Dict[str, Any]]:
    """Get all clauses of a specific redline type across all sample contracts.

    Args:
        clause_type: One of: liability_caps, indemnification, ip_ownership,
                     payment_terms, governing_law, termination_rights,
                     confidentiality, force_majeure.

    Returns:
        List of dicts with contract info and the clause text.
    """
    results = []
    for contract in SAMPLE_CONTRACTS:
        if clause_type in contract["clauses"]:
            clause = contract["clauses"][clause_type]
            results.append({
                "contract_id": contract["contract_id"],
                "contract_title": contract["title"],
                "section": clause["section"],
                "original_text": clause["original_text"],
                "risk_issues": clause.get("risk_issues", []),
            })
    return results


def print_contract_summary(contract_id: str) -> None:
    """Print a formatted summary of a sample contract.

    Args:
        contract_id: The contract_id to display.
    """
    contract = get_contract(contract_id)
    if not contract:
        print(f"Contract '{contract_id}' not found.")
        return

    print(f"\n{'='*70}")
    print(f"CONTRACT: {contract['title']}")
    print(f"{'='*70}")
    print(f"  ID:             {contract['contract_id']}")
    print(f"  Type:           {CONTRACT_TYPE_LABELS.get(contract['contract_type'], contract['contract_type'])}")
    print(f"  Industry:       {contract['industry']}")
    print(f"  Deal Size:      {contract['deal_size_tier']}")
    print(f"  Governing Law:  {contract['governing_law']}")
    print(f"  Effective Date: {contract['effective_date']}")
    print(f"  Scenario:       {contract['scenario']}")
    print(f"\n  Parties:")
    for role, party in contract["parties"].items():
        print(f"    {role.replace('_', ' ').title()}: {party}")
    print(f"\n  Clauses ({len(contract['clauses'])}):")
    for clause_type, clause in contract["clauses"].items():
        print(f"    {clause['section']}")
        issues = clause.get("risk_issues", [])
        if issues:
            print(f"      Risk issues: {len(issues)}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    # Print summary of all contracts
    for c in SAMPLE_CONTRACTS:
        print_contract_summary(c["contract_id"])

    # Example: Get all liability cap clauses
    print("\n--- All Liability Cap Clauses ---\n")
    for item in get_clauses_by_type("liability_caps"):
        print(f"Contract: {item['contract_title']}")
        print(f"Section: {item['section']}")
        print(f"Text:\n{item['original_text'][:200]}...")
        print()
