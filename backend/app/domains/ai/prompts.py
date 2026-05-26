"""Prompt template system — versioned prompt registry, rendering, and management."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """A versioned prompt template with metadata."""
    key: str
    version: int
    template: str
    system_prompt: Optional[str] = None
    model: str = "gpt-4o"
    temperature: float = 0.1
    max_tokens: int = 4096
    response_schema: Optional[dict] = None


class PromptRegistry:
    """Registry of versioned prompt templates with rendering support."""

    def __init__(self):
        self._templates: dict[str, list[PromptTemplate]] = {}

    def register(self, template: PromptTemplate):
        if template.key not in self._templates:
            self._templates[template.key] = []
        self._templates[template.key].append(template)
        self._templates[template.key].sort(key=lambda t: t.version, reverse=True)

    def get(self, key: str, version: Optional[int] = None) -> Optional[PromptTemplate]:
        versions = self._templates.get(key, [])
        if not versions:
            return None
        if version is not None:
            for t in versions:
                if t.version == version:
                    return t
            return None
        return versions[0]  # Latest version

    def render(self, key: str, version: Optional[int] = None, **variables) -> str:
        """Render a prompt template with variables."""
        template = self.get(key, version)
        if not template:
            raise ValueError(f"Prompt template '{key}' (version {version}) not found")
        from jinja2 import Template
        jinja = Template(template.template)
        return jinja.render(**variables)


# ── Default prompt templates ───────────────────────────────────────

prompt_registry = PromptRegistry()

prompt_registry.register(PromptTemplate(
    key="risk_analysis",
    version=1,
    template="""
You are a senior contract risk analyst. Analyze the following contract chunks
and identify all high-risk clauses, missing clauses, and obligations.

Contract chunks:
{% for chunk in chunks %}
[Chunk {{ loop.index0 }}] (Pages: {{ chunk.page_numbers }})
{{ chunk.text }}
{% endfor %}

For each finding, provide:
1. clause_type: The type of clause (indemnification, liability, termination, data_privacy, compliance, payment, confidentiality, ip, force_majeure, assignment, governing_law, non_compete, other)
2. severity: critical, high, medium, low, or info
3. title: Short title
4. description: Detailed explanation of the risk
5. recommendation: Specific remediation recommendation
6. confidence: 0.0-1.0
7. risk_score: 0.0-1.0 (overall risk)
8. chunk_indices: List of chunk indices this finding relates to

Also provide:
- risk_score: Overall contract risk score (0.0-1.0)
- summary: One-paragraph executive summary

Respond in JSON format with keys: risk_score, summary, findings (array)
""",
    system_prompt="You are a senior contract risk analyst. Always respond in valid JSON.",
    response_schema={"type": "json_object"},
))

prompt_registry.register(PromptTemplate(
    key="redline_generation",
    version=1,
    template="""
You are a senior contract negotiation specialist. Review the following clause
and suggest improved language that protects our interests while remaining
commercially reasonable.

Clause type: {{ clause_type }}
Original text:
{{ original_text }}

Context from contract:
{{ context }}

Provide:
1. proposed_text: The improved clause language as a single plain-text string (not a JSON object)
2. rationale: Why this change is recommended
3. risk_level: critical, high, medium, or low
4. confidence: 0.0-1.0

Respond in JSON format.
""",
    system_prompt="You are a senior contract negotiation specialist. Always respond in valid JSON.",
    response_schema={"type": "json_object"},
))

prompt_registry.register(PromptTemplate(
    key="redline_generation",
    version=2,
    template="""
You are a senior contract negotiation specialist. Suggest a legally sound change for the issue below.

Clause type: {{ clause_type }}

Contract excerpt (for context only — do NOT use the full excerpt as original_text):
{{ original_text }}

Risk context:
{{ context }}

Choose exactly one operation:
- "insert" — clause is MISSING; add new language without deleting unrelated text
- "modification" — change a specific phrase/sentence inside an existing clause
- "replace" — replace one bounded clause with another (original_text must be the exact clause span only)
- "delete" — remove unsafe language (proposed_text may be empty)

Rules:
1. For "insert": set original_text to "" and provide anchor_text (10–80 chars) — an exact phrase from the excerpt marking WHERE to insert after (e.g. a section heading or closing line of a paragraph). proposed_text is ONLY the new clause.
2. For "modification" or "replace": original_text must be the MINIMAL exact span being changed (under 400 characters), never the whole contract intro or chunk.
3. Never delete title, party names, or recitals when adding a missing clause.
4. proposed_text must be plain text (not JSON).

Respond in JSON with keys:
operation, anchor_text, original_text, proposed_text, rationale, risk_level, confidence
""",
    system_prompt=(
        "You are a senior contract negotiation specialist. "
        "Preserve document integrity: use insert for missing clauses, never replace large sections. "
        "Always respond in valid JSON."
    ),
    response_schema={"type": "json_object"},
))

prompt_registry.register(PromptTemplate(
    key="redline_generation",
    version=3,
    template="""
You are a senior contract negotiation specialist. Suggest a legally sound change for the issue below.

Clause type: {{ clause_type }}

Contract excerpt (for context only — do NOT use the full excerpt as original_text):
{{ original_text }}

Risk context:
{{ context }}

Choose exactly one operation:
- "insert" — clause is MISSING; add new language without deleting unrelated text
- "modification" — change a specific phrase/sentence inside an existing clause
- "replace" — replace one bounded clause with another
- "delete" — remove unsafe language

CRITICAL RULES FOR NUMBERING:
- NEVER add section numbers, article numbers, or subsection numbers to proposed_text (e.g. DO NOT write "10. Indemnification" or "3.2 Feedback Ownership" or "Section 5.1").
- For "insert": Begin proposed_text with the clause title as a plain label only, like "Indemnification." or "Limitation of Liability." — then the substantive clause text.
- Numbering is assigned by the document editor during export. The AI must never assign authoritative numbers.

DRAFTING RULES:
1. For "insert": set original_text to "" and provide anchor_text (10–80 chars) — an exact phrase from the excerpt marking WHERE to insert after. proposed_text is ONLY the new clause body (no section numbers).
2. For "modification" or "replace": original_text must be the MINIMAL exact span being changed (under 400 characters).
3. Never delete title, party names, or recitals when adding a missing clause.
4. proposed_text must be plain text (not JSON).

RISK TRACEABILITY — also return these fields:
- detected_risk: One sentence describing the specific legal risk detected (e.g. "Provider may unilaterally increase fees without cap or notice").
- business_impact: One sentence on the business consequence (e.g. "Exposes customer to uncapped recurring cost escalation and budget unpredictability").
- mitigation_strategy: One sentence on how the proposed clause mitigates it (e.g. "Caps annual fee increases at 5% and requires 60-day written notice").

Respond in JSON with keys:
operation, anchor_text, original_text, proposed_text, rationale, risk_level, confidence,
detected_risk, business_impact, mitigation_strategy
""",
    system_prompt=(
        "You are a senior contract negotiation specialist. "
        "NEVER include section numbers (like '10.' or '3.2') in proposed_text. "
        "Numbering is the document editor's job, not the AI's. "
        "Preserve document integrity: use insert for missing clauses, never replace large sections. "
        "Always respond in valid JSON."
    ),
    response_schema={"type": "json_object"},
))

prompt_registry.register(PromptTemplate(
    key="redline_generation",
    version=4,
    template="""
You are a senior contract negotiation specialist. Suggest a legally sound change for the issue below.

Clause type: {{ clause_type }}

Contract excerpt (for context only — do NOT use the full excerpt as original_text):
{{ original_text }}

Risk context:
{{ context }}

{% if playbook_context %}
{{ playbook_context }}
{% endif %}

Choose exactly one operation:
- "insert" — clause is MISSING; add new language without deleting unrelated text
- "modification" — change a specific phrase/sentence inside an existing clause
- "replace" — replace one bounded clause with another
- "delete" — remove unsafe language

CRITICAL RULES FOR NUMBERING:
- NEVER add section numbers, article numbers, or subsection numbers to proposed_text (e.g. DO NOT write "10. Indemnification" or "3.2 Feedback Ownership" or "Section 5.1").
- For "insert": Begin proposed_text with the clause title as a plain label only, like "Indemnification." or "Limitation of Liability." — then the substantive clause text.
- Numbering is assigned by the document editor during export. The AI must never assign authoritative numbers.

DRAFTING RULES:
1. For "insert": set original_text to "" and provide anchor_text (10–80 chars) — an exact phrase from the excerpt marking WHERE to insert after. proposed_text is ONLY the new clause body (no section numbers).
2. For "modification" or "replace": original_text must be the MINIMAL exact span being changed (under 400 characters).
3. Never delete title, party names, or recitals when adding a missing clause.
4. proposed_text must be plain text (not JSON).

{% if playbook_context %}
PLAYBOOK COMPLIANCE:
- If company-approved language exists for this clause type, your proposed_text MUST align with the approved standard.
- You may adapt the approved language to fit the specific contract context, but preserve the core protections.
- If no approved standard exists, use preferred alternatives or fallback clauses.
- If the contract contains forbidden language, flag it with operation "delete" or "modification".
{% endif %}

RISK TRACEABILITY — also return these fields:
- detected_risk: One sentence describing the specific legal risk detected (e.g. "Provider may unilaterally increase fees without cap or notice").
- business_impact: One sentence on the business consequence (e.g. "Exposes customer to uncapped recurring cost escalation and budget unpredictability").
- mitigation_strategy: One sentence on how the proposed clause mitigates it (e.g. "Caps annual fee increases at 5% and requires 60-day written notice").

Respond in JSON with keys:
operation, anchor_text, original_text, proposed_text, rationale, risk_level, confidence,
detected_risk, business_impact, mitigation_strategy
""",
    system_prompt=(
        "You are a senior contract negotiation specialist. "
        "NEVER include section numbers (like '10.' or '3.2') in proposed_text. "
        "Numbering is the document editor's job, not the AI's. "
        "Preserve document integrity: use insert for missing clauses, never replace large sections. "
        "Always respond in valid JSON."
    ),
    response_schema={"type": "json_object"},
))
