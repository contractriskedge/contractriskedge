"""Multi-step prompt chain for risk clause analysis.

Defines a 4-step prompt chain: (1) clause classification, (2) risk
assessment, (3) severity scoring, and (4) rationale generation.
Each step builds on the previous, with structured output enforcement.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .taxonomy import RiskTaxonomy


class RiskPromptChain:
    """Multi-step prompt chain for contract risk analysis.

    Builds structured prompts for each step of the risk analysis
    pipeline: classification, assessment, scoring, and rationale.
    Each prompt includes the taxonomy context and few-shot examples.

    Usage:
        taxonomy = RiskTaxonomy()
        prompts = RiskPromptChain(taxonomy)
        classify_prompt = prompts.build_classification_prompt(clause_text)
        assessment_prompt = prompts.build_assessment_prompt(clause_text, category)
    """

    def __init__(self, taxonomy: RiskTaxonomy) -> None:
        """Initialize the prompt chain with taxonomy context.

        Args:
            taxonomy: The risk taxonomy to reference in prompts.
        """
        self._taxonomy = taxonomy

    def build_system_prompt(self) -> str:
        """Build the base system prompt for risk analysis.

        Returns:
            System prompt string with role definition and constraints.
        """
        return (
            "You are an expert contract risk analyst AI. Your role is to analyze "
            "contract clauses and identify potential risks with precision and accuracy.\n\n"
            "CONSTRAINTS:\n"
            "1. Only analyze the clause text provided - do not make assumptions about "
            "information not present.\n"
            "2. Be objective and evidence-based. Base all assessments on the actual "
            "language in the clause.\n"
            "3. If a clause is missing or ambiguous, note this rather than guessing.\n"
            "4. Always output valid JSON as specified.\n"
            "5. Consider both legal and business implications.\n"
            "6. Reference specific language from the clause to support your findings."
        )

    def build_classification_prompt(
        self,
        clause_text: str,
        section_heading: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Build the Step 1 prompt: clause classification.

        Classifies the clause into one or more risk categories.

        Args:
            clause_text: The text of the clause to classify.
            section_heading: Optional section heading for context.

        Returns:
            List of message dicts for the LLM.
        """
        categories = self._taxonomy.get_all_categories()
        category_descriptions = "\n".join(
            f"- {cat.id}: {cat.name} - {cat.description}"
            for cat in categories
        )

        context = ""
        if section_heading:
            context = f"\nSection Heading: {section_heading}\n"

        user_prompt = (
            "STEP 1: CLAUSE CLASSIFICATION\n\n"
            f"Analyze the following contract clause and classify it into the "
            f"appropriate risk categories.\n\n"
            f"CLAUSE TEXT:\n```\n{clause_text}\n```\n"
            f"{context}\n"
            f"AVAILABLE RISK CATEGORIES:\n{category_descriptions}\n\n"
            "TASK:\n"
            "1. Identify which risk categories this clause relates to (may be multiple).\n"
            "2. For each identified category, select the most specific sub-type.\n"
            "3. Rate your confidence in the classification (high/medium/low).\n\n"
            "OUTPUT FORMAT (JSON):\n"
            "{\n"
            '  "classifications": [\n'
            "    {\n"
            '      "category_id": "string",\n'
            '      "sub_type_id": "string",\n'
            '      "confidence": "high|medium|low",\n'
            '      "reasoning": "string - brief justification"\n'
            "    }\n"
            "  ],\n"
            '  "is_ambiguous": boolean,\n'
            '  "needs_human_review": boolean\n'
            "}"
        )

        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]

    def build_assessment_prompt(
        self,
        clause_text: str,
        category_id: str,
        sub_type_id: Optional[str] = None,
        section_heading: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Build the Step 2 prompt: risk assessment.

        Assesses the specific risk level and characteristics.

        Args:
            clause_text: The clause text to assess.
            category_id: The identified risk category.
            sub_type_id: Optional specific sub-type.
            section_heading: Optional section heading.

        Returns:
            List of message dicts for the LLM.
        """
        category = self._taxonomy.get_category(category_id)
        if category is None:
            raise ValueError(f"Unknown category: {category_id}")

        sub_type_info = ""
        if sub_type_id:
            for sub in category.sub_types:
                if sub.id == sub_type_id:
                    sub_type_info = (
                        f"\nSub-Type: {sub.name}\n"
                        f"Description: {sub.description}\n"
                        f"Severity Range: {sub.default_severity_range[0]}-"
                        f"{sub.default_severity_range[1]}\n"
                        f"Example High Risk Language: "
                        f"{' | '.join(sub.example_high_risk_language)}\n"
                        f"Example Market Standard: "
                        f"{' | '.join(sub.example_market_standard_language)}"
                    )
                    break

        context = ""
        if section_heading:
            context = f"\nSection Heading: {section_heading}\n"

        user_prompt = (
            "STEP 2: RISK ASSESSMENT\n\n"
            f"Assess the risk level of the following clause.\n\n"
            f"CLAUSE TEXT:\n```\n{clause_text}\n```\n"
            f"{context}\n"
            f"CATEGORY: {category.name} ({category_id})\n"
            f"{sub_type_info}\n\n"
            "TASK:\n"
            "1. Assess the risk level of this clause in detail.\n"
            "2. Compare the clause language against market standards.\n"
            "3. Identify specific high-risk language or protections.\n"
            "4. Consider the business impact of this clause.\n\n"
            "OUTPUT FORMAT (JSON):\n"
            "{\n"
            '  "risk_level": "critical|high|medium|low|info",\n'
            '  "risk_score": float (0.0-1.0),\n'
            '  "key_concerns": ["string - list of specific concerns"],\n'
            '  "favorable_terms": ["string - list of favorable terms"],\n'
            '  "market_comparison": "string - how this compares to market",\n'
            '  "business_impact": "string - business impact assessment"\n'
            "}"
        )

        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]

    def build_severity_prompt(
        self,
        clause_text: str,
        category_id: str,
        sub_type_id: Optional[str] = None,
        assessment_context: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Build the Step 3 prompt: severity scoring.

        Generates a numerical severity score with chain-of-thought.

        Args:
            clause_text: The clause text.
            category_id: The risk category.
            sub_type_id: Optional specific sub-type.
            assessment_context: Optional context from step 2.

        Returns:
            List of message dicts for the LLM.
        """
        category = self._taxonomy.get_category(category_id)
        sev_range = category.default_severity_range if category else (1, 10)

        context = ""
        if assessment_context:
            context = f"\nPRIOR ASSESSMENT:\n{assessment_context}\n"

        user_prompt = (
            "STEP 3: SEVERITY SCORING\n\n"
            f"Score the severity of this clause on a scale of 1-10.\n\n"
            f"CLAUSE TEXT:\n```\n{clause_text}\n```\n"
            f"{context}\n"
            f"CATEGORY: {category_id}\n"
            f"SEVERITY RANGE FOR THIS CATEGORY: {sev_range[0]}-{sev_range[1]}\n\n"
            "SCORING GUIDELINES:\n"
            "1-3: Minor concern, standard market language, low business impact\n"
            "4-5: Moderate risk, some deviation from market standard\n"
            "6-7: Significant risk, clearly unfavorable terms\n"
            "8-9: Severe risk, highly unusual or aggressive terms\n"
            "10: Critical risk, potentially invalid or unenforceable provision\n\n"
            "TASK:\n"
            "1. Analyze the clause step by step (chain-of-thought).\n"
            "2. Assign a numerical severity score (1-10).\n"
            "3. Classify your confidence in this score.\n"
            "4. Consider multiple dimensions of severity.\n\n"
            "OUTPUT FORMAT (JSON):\n"
            "{\n"
            '  "chain_of_thought": "string - step-by-step reasoning",\n'
            '  "severity_score": integer (1-10),\n'
            '  "confidence": "high|medium|low",\n'
            '  "confidence_reasoning": "string",\n'
            '  "dimension_scores": {\n'
            '    "legal_risk": integer (1-10),\n'
            '    "financial_risk": integer (1-10),\n'
            '    "operational_risk": integer (1-10),\n'
            '    "reputational_risk": integer (1-10)\n'
            '  },\n'
            '  "score_justification": "string - detailed justification"\n'
            "}"
        )

        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]

    def build_rationale_prompt(
        self,
        clause_text: str,
        category_id: str,
        severity_score: int,
        assessment_summary: str,
    ) -> List[Dict[str, str]]:
        """Build the Step 4 prompt: rationale generation with 8-field explainability.

        Generates a comprehensive, human-readable rationale using the
        8-field enterprise explainability model.

        Args:
            clause_text: The clause text.
            category_id: The risk category.
            severity_score: The severity score (1-10).
            assessment_summary: Summary from prior steps.

        Returns:
            List of message dicts for the LLM.
        """
        category = self._taxonomy.get_category(category_id)
        category_name = category.name if category else category_id

        user_prompt = (
            "STEP 4: ENTERPRISE EXPLAINABILITY OUTPUT\n\n"
            f"Generate the final risk analysis output using the 8-field enterprise "
            f"explainability model.\n\n"
            f"CLAUSE TEXT:\n```\n{clause_text}\n```\n\n"
            f"CATEGORY: {category_name}\n"
            f"SEVERITY SCORE: {severity_score}/10\n"
            f"ASSESSMENT SUMMARY:\n{assessment_summary}\n\n"
            "TASK:\n"
            "Produce a comprehensive risk analysis with ALL of the following fields:\n\n"
            "1. why_flagged: Explain WHY this clause was flagged. Reference specific "
            "language from the clause that triggered the alert. Be precise.\n\n"
            "2. potential_business_impact: Assess the potential business impact "
            "including financial, operational, and reputational consequences.\n\n"
            "3. market_benchmark_comparison: Compare this clause against market "
            "standards and industry benchmarks for similar contract types.\n\n"
            "4. confidence_score: Assign a confidence score (0.0-1.0) based on "
            "how clearly the clause text supports the assessment.\n\n"
            "5. suggested_remediation: Provide specific, actionable remediation "
            "recommendations including alternative language and negotiation positions.\n\n"
            "6. linked_evidence: List specific evidence from the clause text that "
            "supports each claim in your assessment.\n\n"
            "7. jurisdictional_considerations: Note any jurisdiction-specific "
            "considerations for US / EU / UK / APAC regulatory frameworks.\n\n"
            "8. rationale: Write a clear, concise overall rationale.\n\n"
            "OUTPUT FORMAT (JSON):\n"
            "{\n"
            '  "why_flagged": "string - specific explanation with clause references",\n'
            '  "potential_business_impact": "string - business impact assessment",\n'
            '  "market_benchmark_comparison": "string - comparison to market standards",\n'
            '  "confidence_score": float (0.0-1.0),\n'
            '  "suggested_remediation": "string - actionable recommendations",\n'
            '  "linked_evidence": [\n'
            "    {\n"
            '      "clause_reference": "string",\n'
            '      "excerpt": "string",\n'
            '      "relevance_score": float (0.0-1.0)\n'
            "    }\n"
            "  ],\n"
            '  "jurisdictional_considerations": [\n'
            "    {\n"
            '      "jurisdiction": "US|EU|UK|APAC",\n'
            '      "rule_reference": "string",\n'
            '      "risk_modifier": float,\n'
            '      "explanation": "string"\n'
            "    }\n"
            "  ],\n"
            '  "rationale": "string - comprehensive explanation",\n'
            '  "executive_summary": "string - one paragraph summary",\n'
            '  "suggested_action": "accept|review|negotiate|reject",\n'
            '  "negotiation_guidance": {\n'
            '    "priority": "high|medium|low",\n'
            '    "fallback_position": "string",\n'
            '    "market_alternative": "string",\n'
            '    "key_arguments": ["string - list of key arguments"]\n'
            '  },\n'
            '  "risk_mitigation": ["string - list of mitigation steps"]\n'
            "}"
        )

        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]

    def build_combined_analysis_prompt(
        self,
        clause_text: str,
        section_heading: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Build a single combined prompt for all steps with 8-field output.

        Useful for simpler analyses where the multi-step chain
        overhead is unnecessary.

        Args:
            clause_text: The clause text to analyze.
            section_heading: Optional section heading.

        Returns:
            List of message dicts for the LLM.
        """
        categories = self._taxonomy.get_all_categories()
        category_descriptions = "\n".join(
            f"- {cat.id}: {cat.name} - {cat.description}\n"
            f"  Sub-types: {', '.join(s.name for s in cat.sub_types)}"
            for cat in categories
        )

        context = ""
        if section_heading:
            context = f"\nSection Heading: {section_heading}\n"

        user_prompt = (
            "COMPREHENSIVE CLAUSE RISK ANALYSIS — 8-FIELD EXPLAINABILITY MODEL\n\n"
            f"Analyze the following contract clause for risk.\n\n"
            f"CLAUSE TEXT:\n```\n{clause_text}\n```\n"
            f"{context}\n\n"
            f"RISK TAXONOMY:\n{category_descriptions}\n\n"
            "TASKS (complete all in order):\n"
            "1. CLASSIFICATION: Identify risk categories and sub-types.\n"
            "2. ASSESSMENT: Assess risk level and key concerns.\n"
            "3. SEVERITY SCORING: Score 1-10 with chain-of-thought.\n"
            "4. EXPLAINABILITY OUTPUT: Generate 8-field enterprise output.\n\n"
            "OUTPUT FORMAT (JSON):\n"
            "{\n"
            '  "classification": {\n'
            '    "categories": [{"category_id": "string", "sub_type_id": "string", '
            '"confidence": "high|medium|low"}],\n'
            '    "is_ambiguous": boolean\n'
            "  },\n"
            '  "assessment": {\n'
            '    "risk_level": "critical|high|medium|low|info",\n'
            '    "risk_score": float,\n'
            '    "key_concerns": ["string"],\n'
            '    "market_comparison": "string"\n'
            "  },\n"
            '  "severity": {\n'
            '    "score": integer,\n'
            '    "confidence": "high|medium|low",\n'
            '    "chain_of_thought": "string",\n'
            '    "dimension_scores": {"legal": int, "financial": int, '
            '"operational": int, "reputational": int}\n'
            "  },\n"
            '  "explainability": {\n'
            '    "why_flagged": "string",\n'
            '    "potential_business_impact": "string",\n'
            '    "market_benchmark_comparison": "string",\n'
            '    "confidence_score": float,\n'
            '    "suggested_remediation": "string",\n'
            '    "linked_evidence": [{"clause_reference": "string", "excerpt": "string", '
            '"relevance_score": float}],\n'
            '    "jurisdictional_considerations": [{"jurisdiction": "string", '
            '"rule_reference": "string", "risk_modifier": float, "explanation": "string"}]\n'
            "  },\n"
            '  "rationale": {\n'
            '    "summary": "string",\n'
            '    "suggested_action": "accept|review|negotiate|reject",\n'
            '    "negotiation_guidance": {"priority": "string", '
            '"fallback_position": "string"},\n'
            '    "risk_mitigation": ["string"]\n'
            "  }\n"
            "}"
        )

        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]
