"""Few-shot examples for risk analysis prompt chain.

Provides curated few-shot examples (one per severity tier) for each
step of the risk analysis pipeline: classification, assessment,
severity scoring, and rationale generation.
"""

from __future__ import annotations

from typing import Any, Dict, List


class FewShotExamples:
    """Few-shot examples for the risk analysis prompt chain.

    Contains curated examples at each severity tier (low, medium,
    high, critical) for each step of the analysis pipeline. These
    are injected into prompts to guide LLM output quality.

    Usage:
        examples = FewShotExamples()
        classify_examples = examples.get_classification_examples()
        severity_examples = examples.get_severity_examples("high")
    """

    @staticmethod
    def get_classification_examples() -> List[Dict[str, Any]]:
        """Get few-shot examples for clause classification.

        Returns:
            List of example classification inputs and outputs.
        """
        return [
            {
                "clause": (
                    "The Company shall indemnify, defend, and hold harmless "
                    "the Client from and against any and all claims, damages, "
                    "losses, and expenses arising out of or related to any "
                    "third-party claim alleging that the Services infringe "
                    "upon any patent, copyright, trade secret, or other "
                    "intellectual property right."
                ),
                "output": {
                    "classifications": [
                        {
                            "category_id": "indemnification",
                            "sub_type_id": "indemnification_scope",
                            "confidence": "high",
                            "reasoning": "Explicit indemnification clause covering "
                            "third-party IP claims with broad scope",
                        },
                        {
                            "category_id": "intellectual_property",
                            "sub_type_id": "ip_warranties",
                            "confidence": "high",
                            "reasoning": "IP infringement indemnification is a "
                            "standard IP warranty provision",
                        },
                    ],
                    "is_ambiguous": False,
                    "needs_human_review": False,
                },
            },
            {
                "clause": (
                    "Either party may terminate this Agreement upon 30 days "
                    "written notice if the other party materially breaches "
                    "any provision of this Agreement and fails to cure such "
                    "breach within the 30-day cure period."
                ),
                "output": {
                    "classifications": [
                        {
                            "category_id": "termination",
                            "sub_type_id": "termination_for_cause",
                            "confidence": "high",
                            "reasoning": "Standard termination for cause clause "
                            "with cure period",
                        }
                    ],
                    "is_ambiguous": False,
                    "needs_human_review": False,
                },
            },
            {
                "clause": (
                    "The parties agree that all pricing shall be subject to "
                    "adjustment annually based on the Consumer Price Index."
                ),
                "output": {
                    "classifications": [
                        {
                            "category_id": "payment_terms",
                            "sub_type_id": "price_adjustment",
                            "confidence": "high",
                            "reasoning": "Price adjustment mechanism tied to CPI",
                        }
                    ],
                    "is_ambiguous": False,
                    "needs_human_review": False,
                },
            },
        ]

    @staticmethod
    def get_assessment_examples() -> List[Dict[str, Any]]:
        """Get few-shot examples for risk assessment.

        Returns:
            List of example assessment inputs and outputs.
        """
        return [
            {
                "clause": (
                    "Provider's total aggregate liability for any claims "
                    "arising under this Agreement shall not exceed $100."
                ),
                "category": "liability_limitation",
                "output": {
                    "risk_level": "critical",
                    "risk_score": 0.95,
                    "key_concerns": [
                        "Liability cap of $100 is unrealistically low for any "
                        "commercial engagement",
                        "Cap may be unenforceable as it effectively eliminates "
                        "all meaningful remedy",
                        "No exceptions for gross negligence, IP infringement, "
                        "or confidentiality breaches",
                    ],
                    "favorable_terms": [],
                    "market_comparison": "Market standard is liability cap "
                    "equal to 12 months of fees, typically with exceptions. "
                    "A $100 cap is extremely aggressive and below market.",
                    "business_impact": "Essentially eliminates all meaningful "
                    "recourse for the non-drafting party, making the contract "
                    "effectively one-sided.",
                },
            },
            {
                "clause": (
                    "Neither party shall be liable for any failure or delay "
                    "in performance caused by acts of God, war, natural "
                    "disasters, or government restrictions."
                ),
                "category": "force_majeure",
                "output": {
                    "risk_level": "low",
                    "risk_score": 0.15,
                    "key_concerns": [
                        "Does not explicitly include pandemics or cyberattacks",
                    ],
                    "favorable_terms": [
                        "Mutual application to both parties",
                        "Reasonable list of covered events",
                    ],
                    "market_comparison": "Generally market standard but could "
                    "be improved by adding modern risks like pandemics and "
                    "cyber incidents.",
                    "business_impact": "Low risk - standard force majeure "
                    "provision with typical coverage.",
                },
            },
            {
                "clause": (
                    "All intellectual property rights in any work product "
                    "created under this Agreement shall be owned exclusively "
                    "by Provider, and Client receives a non-exclusive, "
                    "non-transferable license to use such work product solely "
                    "for its internal business purposes."
                ),
                "category": "intellectual_property",
                "output": {
                    "risk_level": "high",
                    "risk_score": 0.75,
                    "key_concerns": [
                        "Provider owns all IP even though client is paying "
                        "for development",
                        "Client receives only a non-exclusive, non-transferable "
                        "license",
                        "No right to modify or enhance the work product",
                        "License may terminate if agreement terminates",
                    ],
                    "favorable_terms": [],
                    "market_comparison": "Market standard is for the customer "
                    "to own custom-developed IP with a license grant to the "
                    "provider for pre-existing tools.",
                    "business_impact": "Client pays for development but gets "
                    "no ownership, creating vendor lock-in and preventing "
                    "use of deliverables with other providers.",
                },
            },
        ]

    @staticmethod
    def get_severity_examples() -> List[Dict[str, Any]]:
        """Get few-shot examples for severity scoring.

        Returns:
            List of example severity scoring inputs and outputs.
        """
        return [
            {
                "clause": (
                    "Provider may unilaterally modify any terms of this "
                    "Agreement upon 5 days electronic notice."
                ),
                "category": "payment_terms",
                "output": {
                    "chain_of_thought": (
                        "1. This clause allows unilateral modification with "
                        "minimal notice.\n"
                        "2. 5 days is insufficient time to review and respond "
                        "to changes.\n"
                        "3. No requirement for mutual consent or reasonable "
                        "limitations.\n"
                        "4. This creates significant uncertainty and risk.\n"
                        "5. Such clauses are often challenged as unconscionable."
                    ),
                    "severity_score": 9,
                    "confidence": "high",
                    "confidence_reasoning": "Clear language with unambiguous "
                    "unilateral modification right",
                    "dimension_scores": {
                        "legal_risk": 9,
                        "financial_risk": 8,
                        "operational_risk": 9,
                        "reputational_risk": 6,
                    },
                    "score_justification": (
                        "Unilateral modification with only 5 days notice "
                        "is extremely aggressive and potentially unenforceable. "
                        "Score of 9 reflects severe risk."
                    ),
                },
            },
            {
                "clause": (
                    "This Agreement shall be governed by and construed in "
                    "accordance with the laws of the State of New York."
                ),
                "category": "governing_law",
                "output": {
                    "chain_of_thought": (
                        "1. Choice of New York law is standard for commercial "
                        "contracts.\n"
                        "2. New York has well-established commercial law.\n"
                        "3. No indication of unfairness or inconvenience.\n"
                        "4. This is a neutral, standard provision."
                    ),
                    "severity_score": 2,
                    "confidence": "high",
                    "confidence_reasoning": "Standard governing law provision",
                    "dimension_scores": {
                        "legal_risk": 2,
                        "financial_risk": 1,
                        "operational_risk": 2,
                        "reputational_risk": 1,
                    },
                    "score_justification": (
                        "Standard New York governing law clause presents "
                        "minimal risk. Score of 2 reflects minor concern only "
                        "if parties have no connection to New York."
                    ),
                },
            },
            {
                "clause": (
                    "Provider shall use reasonable security measures to "
                    "protect Client data."
                ),
                "category": "data_privacy",
                "output": {
                    "chain_of_thought": (
                        "1. 'Reasonable security measures' is vague and "
                        "ambiguous.\n"
                        "2. No specific standards referenced (SOC 2, ISO 27001).\n"
                        "3. No breach notification timeline specified.\n"
                        "4. No audit rights for the client.\n"
                        "5. No specific technical controls enumerated."
                    ),
                    "severity_score": 6,
                    "confidence": "medium",
                    "confidence_reasoning": "Risk depends on the type of data "
                    "being processed",
                    "dimension_scores": {
                        "legal_risk": 7,
                        "financial_risk": 6,
                        "operational_risk": 5,
                        "reputational_risk": 7,
                    },
                    "score_justification": (
                        "Vague security language creates significant risk, "
                        "especially for regulated data. Score of 6 reflects "
                        "the ambiguity and lack of specificity."
                    ),
                },
            },
        ]

    @staticmethod
    def get_rationale_examples() -> List[Dict[str, Any]]:
        """Get few-shot examples for rationale generation.

        Returns:
            List of example rationale inputs and outputs.
        """
        return [
            {
                "clause": (
                    "Provider shall have no obligation to return or destroy "
                    "Client's confidential information upon termination of "
                    "this Agreement."
                ),
                "category": "confidentiality",
                "severity": 8,
                "output": {
                    "rationale": (
                        "This clause presents a severe confidentiality risk "
                        "by eliminating the standard obligation to return or "
                        "destroy confidential information upon termination. "
                        "Without this obligation, Client's confidential "
                        "information remains indefinitely with the Provider "
                        "with no contractual mechanism to require its removal. "
                        "This creates ongoing data privacy and security risks, "
                        "particularly problematic under regulations like GDPR "
                        "which require data minimization and deletion. The "
                        "clause is significantly below market standard and "
                        "should be a priority for negotiation."
                    ),
                    "executive_summary": (
                        "The clause fails to require return or destruction of "
                        "confidential information post-termination, leaving "
                        "sensitive data indefinitely exposed."
                    ),
                    "suggested_action": "negotiate",
                    "negotiation_guidance": {
                        "priority": "high",
                        "fallback_position": (
                            "At minimum, require destruction within 30 days "
                            "with written certification"
                        ),
                        "market_alternative": (
                            "Standard clause: 'Within 30 days of termination, "
                            "each party shall return or destroy the other's "
                            "confidential information and provide written "
                            "certification of compliance.'"
                        ),
                        "key_arguments": [
                            "Standard industry practice requires return or "
                            "destruction of confidential information",
                            "GDPR and other privacy regulations require data "
                            "minimization and deletion when no longer needed",
                            "Retaining data creates unnecessary security risk "
                            "and potential liability",
                        ],
                    },
                    "risk_mitigation": [
                        "Negotiate for standard return/destruction obligation "
                        "within 30 days",
                        "Require written certification of destruction",
                        "If retention is necessary, limit to what is required "
                        "by law with defined retention period",
                        "Include audit right to verify destruction",
                    ],
                },
            },
            {
                "clause": (
                    "Either party may terminate this Agreement for convenience "
                    "upon 90 days written notice to the other party."
                ),
                "category": "termination",
                "severity": 2,
                "output": {
                    "rationale": (
                        "This is a standard mutual termination for convenience "
                        "clause with a reasonable 90-day notice period. The "
                        "mutual nature ensures balance between the parties, "
                        "and 90 days provides adequate time to transition "
                        "services or find alternatives. This clause presents "
                        "minimal risk and is consistent with market standards "
                        "for commercial contracts."
                    ),
                    "executive_summary": (
                        "Standard mutual termination for convenience clause "
                        "with reasonable notice period."
                    ),
                    "suggested_action": "accept",
                    "negotiation_guidance": {
                        "priority": "low",
                        "fallback_position": "",
                        "market_alternative": "",
                        "key_arguments": [],
                    },
                    "risk_mitigation": [
                        "Ensure transition assistance obligations are in place",
                        "Document exit procedures in advance",
                    ],
                },
            },
        ]

    @staticmethod
    def get_all_examples() -> Dict[str, List[Dict[str, Any]]]:
        """Get all few-shot examples organized by step.

        Returns:
            Dict with keys for each step containing example lists.
        """
        return {
            "classification": FewShotExamples.get_classification_examples(),
            "assessment": FewShotExamples.get_assessment_examples(),
            "severity": FewShotExamples.get_severity_examples(),
            "rationale": FewShotExamples.get_rationale_examples(),
        }
