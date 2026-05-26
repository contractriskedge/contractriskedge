"""Generate a synthetic benchmark corpus for development and testing.

Creates 10,000+ realistic contract clauses across all 12 risk
categories and 15 contract types for populating the benchmark corpus.
"""

import json
import logging
import os
import random
from datetime import datetime
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("generate_corpus")

random.seed(42)

CONTRACT_TYPES = [
    "non_disclosure", "master_services", "saas_agreement", "software_license",
    "professional_services", "employment_agreement", "supply_agreement",
    "distribution_agreement", "partnership_agreement", "loan_agreement",
    "lease_agreement", "service_level", "statement_of_work",
    "other",
]

INDUSTRIES = [
    "technology", "healthcare", "financial_services", "manufacturing",
    "retail", "energy", "real_estate", "telecommunications",
    "government", "pharmaceuticals",
]

COUNTERPARTY_TYPES = ["enterprise", "smb", "government", "non_profit"]

CLAUSE_TYPES = [
    "indemnification", "liability_caps", "termination", "confidentiality",
    "data_privacy", "compliance", "payment_terms", "force_majeure",
    "assignment", "governing_law", "non_compete", "intellectual_property",
]

# Template clauses for each type with variability
CLAUSE_TEMPLATES: Dict[str, List[str]] = {
    "indemnification": [
        "The {provider} agrees to indemnify, defend, and hold harmless the {client} from and against any and all claims, losses, liabilities, and expenses arising out of or related to this Agreement, except where caused by the {client}'s own negligence.",
        "{provider} shall defend, indemnify, and hold {client} harmless from any third-party claim arising out of {provider}'s breach of this Agreement.",
        "Each party shall indemnify the other against all losses arising from the indemnifying party's breach of its representations and warranties.",
        "{provider} agrees to indemnify {client} against all claims resulting from {provider}'s gross negligence or willful misconduct.",
        "The {provider} shall indemnify and hold harmless the {client} from any and all damages, losses, and expenses arising from any claim of infringement of third-party intellectual property rights.",
    ],
    "liability_caps": [
        "In no event shall either party be liable to the other for any indirect, incidental, special, consequential, or punitive damages. The total aggregate liability of either party shall not exceed ${amount}.",
        "Neither party shall be liable for any indirect or consequential damages. Each party's total liability shall be limited to the fees paid under this Agreement during the {months} months preceding the claim.",
        "EXCEPT FOR BREACHES OF CONFIDENTIALITY, INDEMNIFICATION OBLIGATIONS, OR INFRINGEMENT OF INTELLECTUAL PROPERTY RIGHTS, NEITHER PARTY'S TOTAL LIABILITY SHALL EXCEED ${amount}.",
        "Liability is capped at the total fees paid or payable by client during the twelve (12) month period immediately preceding the event giving rise to the claim.",
        "Neither party shall be liable for any loss of profits, loss of data, or interruption of business. Total liability shall not exceed ${amount}.",
    ],
    "termination": [
        "Either party may terminate this Agreement upon {days} days' prior written notice to the other party.",
        "This Agreement may be terminated by either party for material breach if the breach remains uncured for {days} days after written notice.",
        "Either party may terminate this Agreement immediately upon written notice if the other party becomes insolvent or files for bankruptcy.",
        "This Agreement shall terminate automatically upon the expiration of the Initial Term unless renewed in writing by both parties.",
        "{client} may terminate this Agreement for convenience upon {days} days' notice. {provider} may terminate only for cause.",
    ],
    "confidentiality": [
        "The Receiving Party shall maintain the Confidential Information in strict confidence and shall not disclose it to any third party for a period of {years} years.",
        "Confidential Information shall not be disclosed to any third party without the prior written consent of the Disclosing Party, except as required by law.",
        "The obligations of confidentiality shall survive termination of this Agreement for a period of {years} years.",
        "Each party agrees to protect the other's Confidential Information using the same degree of care it uses to protect its own confidential information.",
        "Confidential Information excludes information that: (a) is or becomes publicly known; (b) was known to the Receiving Party prior to disclosure; or (c) is independently developed.",
    ],
    "payment_terms": [
        "All fees are due within {days} days of invoice date. Late payments shall accrue interest at {rate}% per month.",
        "{client} shall pay {provider} the fees set forth in the applicable Order Form within {days} days of receipt of invoice.",
        "All payments shall be made in United States dollars. Any undisputed amounts not paid when due shall bear interest at {rate}% per month.",
        "Fees are non-refundable except as expressly set forth in this Agreement. Payment obligations are non-cancellable.",
        "{provider} may increase fees annually by up to {rate}% upon {days} days' prior written notice to {client}.",
    ],
    "governing_law": [
        "This Agreement shall be governed by and construed in accordance with the laws of the State of {state}, without regard to its conflict of laws principles.",
        "The parties hereby submit to the exclusive jurisdiction of the federal and state courts located in {city}, {state}.",
        "Any dispute arising out of or relating to this Agreement shall be resolved by binding arbitration in accordance with the rules of the American Arbitration Association.",
        "This Agreement shall be governed by the laws of {state}. The United Nations Convention on Contracts for the International Sale of Goods shall not apply.",
        "The parties agree that any action arising out of this Agreement shall be brought in the courts of {city}, {state}, and each party submits to the personal jurisdiction thereof.",
    ],
    "force_majeure": [
        "Neither party shall be liable for any failure or delay in performance due to causes beyond its reasonable control, including but not limited to acts of God, war, terrorism, pandemics, and government actions.",
        "If a force majeure event continues for more than {days} days, either party may terminate this Agreement without liability.",
        "The party affected by a force majeure event shall promptly notify the other party and shall use reasonable efforts to resume performance.",
        "Force majeure shall not excuse payment obligations. The non-performing party shall provide periodic updates on the status of the force majeure event.",
        "Performance shall be suspended for the duration of the force majeure event and the time for performance shall be extended by the duration of the delay.",
    ],
    "intellectual_property": [
        "All intellectual property rights in any deliverables created under this Agreement shall be the sole and exclusive property of {client}.",
        "{provider} retains all right, title, and interest in and to its pre-existing intellectual property. {client} is granted a non-exclusive license to use such IP solely for the purpose of this Agreement.",
        "{provider} hereby assigns to {client} all right, title, and interest in and to the work product. To the extent any work product does not qualify as a work made for hire, {provider} irrevocably assigns all rights.",
        "Each party retains ownership of its intellectual property. Neither party acquires any license or other intellectual property right except as expressly set forth in this Agreement.",
        "All deliverables shall be considered 'work made for hire' for {client}. To the extent any deliverables do not qualify as such, {provider} assigns all rights to {client}.",
    ],
    "data_privacy": [
        "Each party shall comply with all applicable data protection laws and regulations, including GDPR and CCPA, in its processing of personal data.",
        "{provider} shall implement and maintain appropriate technical and organizational measures to protect personal data against unauthorized access, disclosure, or destruction.",
        "The parties shall enter into a Data Processing Agreement governing the processing of personal data under this Agreement.",
        "{provider} shall notify {client} within {days} days of becoming aware of any data breach involving {client}'s data.",
        "Upon termination of this Agreement, {provider} shall return or destroy all personal data belonging to {client} within {days} days.",
    ],
    "compliance": [
        "Each party represents that it is in compliance with all applicable laws and regulations, including anti-corruption laws and economic sanctions.",
        "{provider} represents that it has implemented an anti-bribery and anti-corruption compliance program consistent with the US Foreign Corrupt Practices Act.",
        "Neither party shall make any payment or transfer anything of value to any government official for the purpose of influencing any act or decision.",
        "The parties shall comply with all applicable export control laws and regulations, including the US Export Administration Regulations.",
        "{provider} shall maintain accurate books and records reflecting all transactions related to this Agreement.",
    ],
    "assignment": [
        "Neither party may assign this Agreement without the prior written consent of the other party, which consent shall not be unreasonably withheld.",
        "Either party may assign this Agreement to an affiliate or in connection with a merger, acquisition, or sale of all or substantially all of its assets.",
        "Any attempted assignment in violation of this section shall be void. This Agreement shall be binding upon and inure to the benefit of the parties' permitted assigns.",
        "{client} may assign this Agreement without {provider}'s consent to any affiliate or in connection with a change of control.",
        "This Agreement may not be assigned by either party without the other's written consent, except that {provider} may assign to a wholly-owned subsidiary.",
    ],
    "non_compete": [
        "During the term of this Agreement and for {months} months thereafter, neither party shall solicit or hire any employee of the other party who was involved in the performance of this Agreement.",
        "The {provider} agrees that for a period of {months} months following termination, it shall not provide services to any competitor of {client}.",
        "Neither party shall, for a period of {months} months after termination, induce any employee of the other party to terminate their employment.",
        "The non-solicitation obligations set forth in this section shall apply to employees with whom the soliciting party had material contact during the preceding {months} months.",
        "Each party agrees not to use the other's Confidential Information to solicit or divert any customer, client, or business opportunity.",
    ],
}

DEAL_SIZE_TIERS = [
    ("<$1M", "small"), ("$1M-$5M", "medium"), ("$5M-$10M", "large"),
    ("$10M-$50M", "enterprise"), (">$50M", "mega"),
]

JURISDICTIONS = [
    "New York", "Delaware", "California", "Texas", "Illinois",
    "Massachusetts", "Florida", "England", "Ontario", "Singapore",
]


def generate_clause(template: str) -> str:
    """Fill in template variables with realistic values."""
    replacements = {
        "{provider}": random.choice(["Provider", "Vendor", "Supplier", "Contractor", "Licensor", "Service Provider"]),
        "{client}": random.choice(["Client", "Customer", "Licensee", "Buyer", "Recipient"]),
        "{amount}": f"{random.choice([50, 100, 250, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000]):,}",
        "{days}": str(random.choice([10, 15, 30, 45, 60, 90, 120])),
        "{months}": str(random.choice([3, 6, 12, 18, 24])),
        "{years}": str(random.choice([1, 2, 3, 5, 7])),
        "{rate}": str(random.choice([0.5, 1.0, 1.5, 2.0])),
        "{state}": random.choice(["Delaware", "New York", "California", "Texas", "Illinois", "Massachusetts"]),
        "{city}": random.choice(["New York", "San Francisco", "Chicago", "Boston", "Austin", "Wilmington"]),
    }
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


def generate_corpus(num_clauses: int = 10000) -> List[Dict[str, Any]]:
    """Generate a synthetic benchmark corpus.

    Args:
        num_clauses: Number of clauses to generate.

    Returns:
        List of benchmark clause dicts.
    """
    corpus = []
    clause_type_cycle = list(CLAUSE_TYPES)

    for i in range(num_clauses):
        clause_type = random.choice(clause_type_cycle)
        template = random.choice(CLAUSE_TEMPLATES[clause_type])
        clause_text = generate_clause(template)

        deal_size_range, deal_tier = random.choice(DEAL_SIZE_TIERS)
        quality = round(random.uniform(0.75, 0.99), 2)

        entry = {
            "clause_text": clause_text,
            "source_document_id": f"synth_doc_{i // 10:05d}",
            "clause_type": clause_type,
            "contract_type": random.choice(CONTRACT_TYPES),
            "industry": random.choice(INDUSTRIES),
            "counterparty_type": random.choice(COUNTERPARTY_TYPES),
            "deal_size_range": deal_size_range,
            "deal_size_tier": deal_tier,
            "jurisdiction": random.choice(JURISDICTIONS),
            "quality_score": quality,
            "is_attorney_reviewed": quality >= 0.85,
            "favorability": random.choice(["favorable", "neutral", "unfavorable"]),
        }
        corpus.append(entry)

    logger.info(
        "Generated %d synthetic benchmark clauses across %d types",
        len(corpus), len(CLAUSE_TYPES),
    )
    return corpus


def save_corpus(corpus: List[Dict[str, Any]], output_path: str) -> str:
    """Save the corpus to a JSON file.

    Args:
        corpus: List of clause dicts.
        output_path: Directory to save to.

    Returns:
        Path to saved file.
    """
    os.makedirs(output_path, exist_ok=True)
    filepath = os.path.join(output_path, "benchmark_corpus_10k.json")

    with open(filepath, "w") as f:
        json.dump(corpus, f, indent=2)

    logger.info("Corpus saved to %s (%.1f MB)", filepath, os.path.getsize(filepath) / 1024 / 1024)
    return filepath


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate benchmark corpus")
    parser.add_argument("--num", type=int, default=10000, help="Number of clauses")
    parser.add_argument("--output", default="./benchmarking/data", help="Output directory")
    args = parser.parse_args()

    corpus = generate_corpus(args.num)
    path = save_corpus(corpus, os.path.abspath(args.output))
    print(f"\nCorpus generated: {path}")
    print(f"Total clauses: {len(corpus)}")
