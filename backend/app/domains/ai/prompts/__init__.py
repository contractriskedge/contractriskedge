"""Prompt registry with semantic versioning, tenant overrides, and A/B testing support.

This replaces the flat prompt_registry in prompts.py with an enterprise-grade
registry that supports:
- Semantic versioning (semver)
- Active/inactive prompt sets
- Tenant-specific overrides
- A/B testing hooks
- Prompt metadata and change tracking
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PromptStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    ROLLED_BACK = "rolled_back"


@dataclass
class PromptVariable:
    """Defines a variable used in a prompt template."""
    name: str
    description: str
    required: bool = True
    default_value: str | None = None
    validator: str | None = None  # Optional regex or type validator name


@dataclass
class PromptTemplate:
    """A versioned prompt template with full metadata and governance.

    This class stores a semantic version string in `semver` (e.g. "2.1.0")
    for internal resolution and exposes a backward-compatible `version`
    property that returns the major version as an `int` for older callers.
    """
    key: str
    semver: str  # Semantic version string (e.g., "2.1.0")
    system_prompt: str
    template: str = ""
    description: str = ""
    status: PromptStatus = PromptStatus.DRAFT

    # Model configuration
    default_model: str = "gpt-4o"
    default_temperature: float = 0.1
    default_max_tokens: int = 4096

    # Variable definitions
    variables: list[PromptVariable] = field(default_factory=list)

    # Response schema for structured output validation
    response_schema: dict[str, Any] | None = None

    # Governance
    author: str = ""
    change_notes: str = ""
    review_status: str = "pending"  # pending, approved, rejected

    # A/B testing
    ab_test_group: str | None = None  # "control", "variant_a", "variant_b"
    ab_test_weight: float = 0.0  # 0.0-1.0, traffic percentage

    # Metrics
    created_at: str = ""
    activated_at: str | None = None
    total_executions: int = 0
    avg_confidence: float = 0.0
    avg_latency_ms: int = 0

    def render(self, **variables: Any) -> str:
        """Render the template with provided variables using Jinja2."""
        from jinja2 import Template
        jinja = Template(self.template)
        return jinja.render(**variables)

    @property
    def version(self) -> int:
        """Backward-compatible numeric major version (e.g. '1' for '1.0.0')."""
        try:
            return int(self.semver.split(".")[0])
        except Exception:
            return 0


@dataclass
class TenantPromptOverride:
    """Tenant-specific override for a prompt template."""
    tenant_id: str
    prompt_key: str
    version: str
    overridden_system_prompt: str | None = None
    overridden_template: str | None = None
    overridden_variables: dict[str, Any] | None = None
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""


class PromptRegistry:
    """Enterprise prompt registry with semantic versioning and tenant overrides.

    Capabilities:
    - Register prompt templates with semver
    - Activate/deactivate prompt versions
    - Resolve prompts with tenant-specific overrides
    - A/B test group assignment
    - Prompt execution metrics tracking
    """

    def __init__(self):
        self._templates: dict[str, list[PromptTemplate]] = {}
        self._active_versions: dict[str, str] = {}  # key -> active version string
        self._tenant_overrides: dict[str, list[TenantPromptOverride]] = {}
        self._ab_test_configs: dict[str, dict[str, Any]] = {}  # key -> A/B config

    # ── Registration ───────────────────────────────────────────────

    def register(self, template: PromptTemplate) -> None:
        """Register a prompt template version."""
        if template.key not in self._templates:
            self._templates[template.key] = []
        # Check for duplicate semantic version
        existing = [t for t in self._templates[template.key] if t.semver == template.semver]
        if existing:
            raise ValueError(
                f"Prompt template '{template.key}' version '{template.semver}' already registered"
            )
        self._templates[template.key].append(template)
        # Sort by version descending (newest first)
        self._templates[template.key].sort(
            key=lambda t: [int(x) for x in t.semver.split(".")],
            reverse=True,
        )
        logger.info("Registered prompt '%s' version %s", template.key, template.semver)

    def activate(self, key: str, version: str) -> None:
        """Set a specific version as the active prompt for a key."""
        template = self.get(key, version)
        if not template:
            raise ValueError(f"Prompt '{key}' version '{version}' not found")
        # Deactivate all other versions
        for t in self._templates.get(key, []):
            if t.semver == version:
                t.status = PromptStatus.ACTIVE
            elif t.status == PromptStatus.ACTIVE:
                t.status = PromptStatus.INACTIVE
        self._active_versions[key] = version
        logger.info("Activated prompt '%s' version %s", key, version)

    # ── Retrieval ──────────────────────────────────────────────────

    def get(
        self,
        key: str,
        version: str | int | None = None,
        tenant_id: str | None = None,
    ) -> PromptTemplate | None:
        """Get a prompt template, with optional version and tenant override.

        Resolution order:
        1. Tenant-specific override (if tenant_id provided)
        2. Specific version requested
        3. Active version
        4. Latest version
        """
        versions = self._templates.get(key, [])
        if not versions:
            return None

        # Check tenant override first
        if tenant_id:
            override = self._resolve_tenant_override(key, tenant_id)
            if override:
                base = self.get(key, override.version)
                if base:
                    return self._apply_override(base, override)

        # Specific version requested. Accept either a semver string or an int
        # representing the major version for backward compatibility.
        if version is not None:
            # numeric major version lookup
            if isinstance(version, int):
                for t in versions:
                    if t.version == version:
                        return t
                return None
            # semver string lookup
            ver_str = str(version)
            for t in versions:
                if t.semver == ver_str:
                    return t
            return None

        # Active version
        active_version = self._active_versions.get(key)
        if active_version:
            for t in versions:
                if t.semver == active_version:
                    return t

        # Latest version
        return versions[0] if versions else None

    def render(self, key: str, version: str | None = None,
               tenant_id: str | None = None, **variables: Any) -> str:
        """Render a prompt template with variables.

        Resolves the template via get(), then delegates to
        PromptTemplate.render() for Jinja2 rendering.

        Raises:
            ValueError: If no template is found for the given key/version.
        """
        template = self.get(key, version=version, tenant_id=tenant_id)
        if not template:
            raise ValueError(
                f"Prompt template '{key}' (version={version}) not found"
            )
        return template.render(**variables)

    def get_active(self, key: str) -> PromptTemplate | None:
        """Get the currently active prompt template."""
        return self.get(key)

    def list_versions(self, key: str) -> list[PromptTemplate]:
        """List all versions of a prompt, newest first."""
        return list(self._templates.get(key, []))

    def list_keys(self) -> list[str]:
        """List all registered prompt keys."""
        return list(self._templates.keys())

    # ── Tenant Overrides ───────────────────────────────────────────

    def set_tenant_override(self, override: TenantPromptOverride) -> None:
        """Set or update a tenant-specific prompt override."""
        if override.tenant_id not in self._tenant_overrides:
            self._tenant_overrides[override.tenant_id] = []
        existing = [
            o for o in self._tenant_overrides[override.tenant_id]
            if o.prompt_key == override.prompt_key
        ]
        for e in existing:
            self._tenant_overrides[override.tenant_id].remove(e)
        self._tenant_overrides[override.tenant_id].append(override)
        logger.info(
            "Set tenant override for %s prompt '%s' version %s",
            override.tenant_id, override.prompt_key, override.version,
        )

    def get_tenant_override(
        self, tenant_id: str, prompt_key: str
    ) -> TenantPromptOverride | None:
        """Get the active tenant override for a prompt key."""
        overrides = self._tenant_overrides.get(tenant_id, [])
        for o in overrides:
            if o.prompt_key == prompt_key and o.is_active:
                return o
        return None

    def remove_tenant_override(self, tenant_id: str, prompt_key: str) -> None:
        """Remove a tenant override."""
        overrides = self._tenant_overrides.get(tenant_id, [])
        self._tenant_overrides[tenant_id] = [
            o for o in overrides if o.prompt_key != prompt_key
        ]

    def _resolve_tenant_override(
        self, key: str, tenant_id: str
    ) -> TenantPromptOverride | None:
        """Resolve a tenant override, falling back to None."""
        return self.get_tenant_override(tenant_id, key)

    def _apply_override(
        self, base: PromptTemplate, override: TenantPromptOverride
    ) -> PromptTemplate:
        """Apply a tenant override to a base template, returning a new instance."""
        import copy
        merged = copy.deepcopy(base)
        if override.overridden_system_prompt is not None:
            merged.system_prompt = override.overridden_system_prompt
        if override.overridden_template is not None:
            merged.template = override.overridden_template
        if override.overridden_variables:
            merged.variables = [
                PromptVariable(**v) if isinstance(v, dict) else v
                for v in override.overridden_variables
            ]
        return merged

    # ── A/B Testing ────────────────────────────────────────────────

    def configure_ab_test(
        self,
        key: str,
        control_version: str,
        variant_versions: dict[str, float],
    ) -> None:
        """Configure A/B test for a prompt key.

        Args:
            key: Prompt key to test.
            control_version: Version string for control group.
            variant_versions: Dict mapping variant version -> traffic weight (0.0-1.0).
                             Weights should sum to 1.0.
        """
        total_weight = sum(variant_versions.values())
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Variant weights must sum to ~1.0, got {total_weight}")

        self._ab_test_configs[key] = {
            "control": control_version,
            "variants": variant_versions,
            "enabled": True,
        }
        logger.info("Configured A/B test for '%s': control=%s variants=%s", key, control_version, variant_versions)

    def resolve_ab_test(self, key: str, user_id: str) -> PromptTemplate | None:
        """Resolve which prompt version an A/B test user should receive.

        Uses deterministic hashing of user_id for consistent assignment.
        """
        config = self._ab_test_configs.get(key)
        if not config or not config.get("enabled"):
            return self.get_active(key)

        import hashlib
        hash_val = int(hashlib.sha256(user_id.encode()).hexdigest(), 16) % 1000
        threshold = hash_val / 1000.0

        cumulative = 0.0
        for variant, weight in config["variants"].items():
            cumulative += weight
            if threshold <= cumulative:
                return self.get(key, variant)

        return self.get(key, config["control"])

    # ── Metrics ────────────────────────────────────────────────────

    def record_execution(
        self,
        key: str,
        version: str,
        confidence: float,
        latency_ms: int,
    ) -> None:
        """Record execution metrics for a prompt version."""
        template = self.get(key, version)
        if template:
            template.total_executions += 1
            # Rolling average
            n = template.total_executions
            template.avg_confidence = (
                (template.avg_confidence * (n - 1) + confidence) / n
            )
            template.avg_latency_ms = (
                (template.avg_latency_ms * (n - 1) + latency_ms) / n
            )


# ── Global singleton ───────────────────────────────────────────────

prompt_registry = PromptRegistry()

# ── Register core prompt templates ────────────────────────────────
# These are the essential templates needed for AI analysis.
# They mirror the templates defined in app/domains/ai/prompts.py
# but use the enterprise PromptTemplate format (semver, default_* attrs).

_RISK_ANALYSIS_TEMPLATE = """You are a senior contract risk analyst. Analyze the following contract chunks
and identify all high-risk clauses, missing clauses, and obligations.

{% if policy_context %}
{{ policy_context }}

{% endif %}
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
"""

prompt_registry.register(PromptTemplate(
    key="risk_analysis",
    semver="1.0.0",
    system_prompt="You are a senior contract risk analyst. Always respond in valid JSON.",
    template=_RISK_ANALYSIS_TEMPLATE,
    default_model="gpt-4o",
    default_temperature=0.1,
    default_max_tokens=4096,
    status=PromptStatus.ACTIVE,
))

_REDLINE_V4_TEMPLATE = """You are a senior contract negotiation specialist. Review the following clause
and suggest improved language that protects our interests while remaining
commercially reasonable.

Clause type: {{ clause_type }}
Original text:
{{ original_text }}

Risk context:
{{ context }}

{% if playbook_context %}
Approved fallback language from playbook:
{{ playbook_context }}
{% endif %}

Provide:
1. proposed_text: The improved clause language as a single plain-text string (not a JSON object)
2. rationale: Why this change is recommended
3. risk_level: critical, high, medium, or low
4. confidence: 0.0-1.0

Respond in JSON format.
"""

prompt_registry.register(PromptTemplate(
    key="redline_generation",
    semver="4.0.0",
    system_prompt="You are a senior contract negotiation specialist. Always respond in valid JSON.",
    template=_REDLINE_V4_TEMPLATE,
    default_model="gpt-4o",
    default_temperature=0.2,
    default_max_tokens=4096,
    status=PromptStatus.ACTIVE,
))

logger.info("Registered core prompt templates: risk_analysis (1.0.0), redline_generation (4.0.0)")

# ── Batched redline generation — all findings in a single GPT call ──────

_REDLINE_BATCH_TEMPLATE = """You are a senior contract negotiation specialist. Review ALL of the following risk findings
and suggest legally sound redlines for each one in a single response.

{% for finding in findings %}
--- Finding {{ loop.index }} ---
Clause type: {{ finding.clause_type }}
Contract excerpt:
{{ finding.original_text }}

Risk context:
Risk: {{ finding.title }}
Description: {{ finding.description }}

{% if finding.playbook_context %}
{{ finding.playbook_context }}
{% endif %}

{% endfor %}

For EACH finding above, choose exactly one operation:
- "insert" — clause is MISSING; add new language without deleting unrelated text
- "modification" — change a specific phrase/sentence inside an existing clause
- "replace" — replace one bounded clause with another
- "delete" — remove unsafe language

CRITICAL RULES FOR NUMBERING:
- NEVER add section numbers, article numbers, or subsection numbers to proposed_text.
- For "insert": Begin proposed_text with the clause title as a plain label only.
- Numbering is assigned by the document editor during export. The AI must never assign numbers.

DRAFTING RULES:
1. For "insert": set original_text to "" and provide anchor_text (10–80 chars) marking WHERE to insert after.
2. For "modification" or "replace": original_text must be the MINIMAL exact span being changed (under 400 characters).
3. Never delete title, party names, or recitals when adding a missing clause.
4. proposed_text must be plain text (not JSON).

RISK TRACEABILITY — for each finding also return:
- detected_risk: One sentence describing the specific legal risk detected.
- business_impact: One sentence on the business consequence.
- mitigation_strategy: One sentence on how the proposed clause mitigates it.

Respond in JSON with a single object containing a "redlines" array.
Each element in the array must have keys:
finding_index (integer, 1-based matching the findings above),
operation, anchor_text, original_text, proposed_text, rationale, risk_level, confidence,
detected_risk, business_impact, mitigation_strategy
"""

prompt_registry.register(PromptTemplate(
    key="redline_generation_batch",
    semver="1.0.0",
    system_prompt="You are a senior contract negotiation specialist. Analyze ALL findings and return redlines for each in a single JSON response. NEVER include section numbers in proposed_text. Always respond in valid JSON.",
    template=_REDLINE_BATCH_TEMPLATE,
    default_model="gpt-4o",
    default_temperature=0.2,
    default_max_tokens=8192,
    status=PromptStatus.ACTIVE,
))

logger.info("Registered batched redline prompt: redline_generation_batch (1.0.0)")
