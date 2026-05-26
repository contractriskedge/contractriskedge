"""Industry-specific benchmark segmentation Phase 2 (V2-032).

Extends benchmark segmentation to 10+ industry verticals with
enhanced classification accuracy and segment-specific scoring.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Industry vertical definitions with sub-verticals
INDUSTRY_VERTICALS = {
    "saas": {
        "name": "SaaS / Cloud Services",
        "sub_verticals": ["b2b_saas", "b2c_saas", "paas", "iaas", "cloud_infrastructure"],
        "typical_contracts": ["msa", "sla", "sow", "license", "dpa"],
        "key_clause_focus": ["uptime", "data_security", "autorenewal", "liability_cap"],
    },
    "manufacturing": {
        "name": "Manufacturing",
        "sub_verticals": ["automotive", "aerospace", "electronics", "industrial", "consumer_goods"],
        "typical_contracts": ["supply_agreement", "purchase_order", "distribution", "quality"],
        "key_clause_focus": ["warranty", "defect_liability", "force_majeure", "quality_standards"],
    },
    "healthcare": {
        "name": "Healthcare & Life Sciences",
        "sub_verticals": ["healthcare_provider", "pharma", "biotech", "medical_devices", "health_insurance"],
        "typical_contracts": ["baa", "clinical_trial", "vendor_agreement", "license"],
        "key_clause_focus": ["hipaa", "phi_protection", "compliance", "indemnification"],
    },
    "financial_services": {
        "name": "Financial Services",
        "sub_verticals": ["banking", "insurance", "fintech", "investment", "payments"],
        "typical_contracts": ["vendor_agreement", "service_agreement", "nda", "partnership"],
        "key_clause_focus": ["regulatory_compliance", "data_privacy", "audit_rights", "confidentiality"],
    },
    "professional_services": {
        "name": "Professional Services",
        "sub_verticals": ["consulting", "legal", "accounting", "marketing", "it_services"],
        "typical_contracts": ["sow", "consulting_agreement", "msa", "nda"],
        "key_clause_focus": ["scope_of_work", "deliverables", "payment_terms", "ip_ownership"],
    },
    "retail": {
        "name": "Retail & E-commerce",
        "sub_verticals": ["ecommerce", "brick_mortar", "wholesale", "supply_chain", "logistics"],
        "typical_contracts": ["supplier_agreement", "vendor_agreement", "logistics", "marketing"],
        "key_clause_focus": ["pricing", "returns", "termination", "exclusivity"],
    },
    "energy": {
        "name": "Energy & Utilities",
        "sub_verticals": ["oil_gas", "renewable", "utilities", "mining", "nuclear"],
        "typical_contracts": ["supply_agreement", "service_contract", "joint_venture", "lease"],
        "key_clause_focus": ["environmental", "regulatory", "force_majeure", "indemnification"],
    },
    "technology": {
        "name": "Technology / Hardware",
        "sub_verticals": ["hardware", "semiconductor", "telecom", "networking", "iot"],
        "typical_contracts": ["license", "distribution", "manufacturing", "patent"],
        "key_clause_focus": ["ip_rights", "patent", "royalty", "non_compete"],
    },
    "real_estate": {
        "name": "Real Estate & Construction",
        "sub_verticals": ["commercial", "residential", "construction", "property_management", "infrastructure"],
        "typical_contracts": ["lease", "construction", "management", "purchase"],
        "key_clause_focus": ["rent_escalation", "maintenance", "termination", "insurance"],
    },
    "education": {
        "name": "Education & Research",
        "sub_verticals": ["higher_education", "k12", "edtech", "research", "training"],
        "typical_contracts": ["grant", "research", "vendor", "license", "employment"],
        "key_clause_focus": ["ip_ownership", "grant_compliance", "data_privacy", "non_profit"],
    },
    "government": {
        "name": "Government & Public Sector",
        "sub_verticals": ["federal", "state", "local", "defense", "public_health"],
        "typical_contracts": ["procurement", "grant", "service", "classified"],
        "key_clause_focus": ["compliance", "audit", "termination_for_convenience", "security"],
    },
    "media": {
        "name": "Media & Entertainment",
        "sub_verticals": ["publishing", "streaming", "gaming", "advertising", "content"],
        "typical_contracts": ["license", "distribution", "talent", "production", "sponsorship"],
        "key_clause_focus": ["ip_rights", "royalty", "exclusivity", "territory"],
    },
}


@dataclass
class IndustrySegment:
    """An industry segment with benchmark data."""

    industry_id: str
    industry_name: str
    sub_vertical: Optional[str] = None
    contract_count: int = 0
    clause_count: int = 0
    avg_risk_score: float = 0.0
    benchmark_percentiles: Dict[str, Dict[str, float]] = field(default_factory=dict)
    data_freshness_days: Optional[int] = None
    data_quality_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "industry_id": self.industry_id,
            "industry_name": self.industry_name,
            "sub_vertical": self.sub_vertical,
            "contract_count": self.contract_count,
            "clause_count": self.clause_count,
            "avg_risk_score": round(self.avg_risk_score, 2),
            "benchmark_percentiles": self.benchmark_percentiles,
            "data_freshness_days": self.data_freshness_days,
            "data_quality_score": round(self.data_quality_score, 2),
        }


class IndustrySegmentationPhase2:
    """Industry-specific benchmark segmentation Phase 2.

    Extends the existing segmentation to 10+ industry verticals with
    sub-vertical classification and segment-specific benchmark scoring.

    Usage:
        seg = IndustrySegmentationPhase2()
        segment = await seg.classify_industry(contract_text)
        benchmarks = await seg.get_segment_benchmarks("saas", "b2b_saas")
    """

    def __init__(self, db_pool: Optional[Any] = None) -> None:
        """Initialize industry segmentation.

        Args:
            db_pool: Optional database pool.
        """
        self._db_pool = db_pool
        self._verticals = INDUSTRY_VERTICALS
        self._segments: Dict[str, IndustrySegment] = {}

        # Industry-specific keyword signatures for classification
        self._industry_signatures: Dict[str, List[str]] = {
            "saas": ["subscription", "saas", "cloud", "software as a service", "hosted",
                     "service level", "uptime", "monthly fee", "annual fee", "user license"],
            "manufacturing": ["manufacturing", "supply chain", "production", "inventory",
                              "bill of materials", "quality spec", "delivery schedule"],
            "healthcare": ["hipaa", "phi", "protected health", "medical", "clinical",
                           "patient", "healthcare", "baa", "business associate"],
            "financial_services": ["sec", "finra", "fdic", "banking", "investment",
                                   "financial", "regulated", "compliance", "anti-money"],
            "professional_services": ["consulting", "advisory", "statement of work",
                                      "deliverable", "professional service", "time and materials"],
            "retail": ["retail", "e-commerce", "ecommerce", "merchant", "consumer",
                       "point of sale", "inventory", "supplier"],
            "energy": ["energy", "utility", "oil", "gas", "renewable", "power",
                       "environmental", "emission"],
            "technology": ["patent", "intellectual property", "hardware", "firmware",
                           "semiconductor", "telecom", "network"],
            "real_estate": ["lease", "rent", "property", "real estate", "tenant",
                            "landlord", "square foot", "occupancy"],
            "education": ["education", "student", "academic", "research", "grant",
                          "university", "school", "curriculum"],
            "government": ["government", "federal", "state agency", "public sector",
                           "procurement", "regulatory", "compliance"],
            "media": ["content", "publish", "royalty", "license fee", "creative",
                      "distribution right", "territory", "broadcast"],
        }

    async def classify_industry(
        self,
        contract_text: str,
        contract_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Classify a contract into an industry vertical.

        Args:
            contract_text: The contract text to classify.
            contract_type: Optional contract type hint.

        Returns:
            Dict with industry classification results.
        """
        text_lower = contract_text.lower()

        # Score each industry
        scores: Dict[str, float] = {}
        for industry, keywords in self._industry_signatures.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[industry] = score / len(keywords)  # Normalize

        if not scores:
            return {
                "primary_industry": "general_commercial",
                "industry_name": "General Commercial",
                "confidence": 0.0,
                "all_scores": {},
                "sub_vertical": None,
            }

        # Get top industry
        sorted_industries = sorted(scores.items(), key=lambda x: -x[1])
        primary = sorted_industries[0][0]
        confidence = min(1.0, sorted_industries[0][1] * 3)  # Scale confidence

        # Detect sub-vertical
        sub_vertical = self._detect_sub_vertical(text_lower, primary)

        industry_info = self._verticals.get(primary, {})
        return {
            "primary_industry": primary,
            "industry_name": industry_info.get("name", primary),
            "confidence": round(confidence, 3),
            "all_scores": {k: round(v, 3) for k, v in sorted_industries[:5]},
            "sub_vertical": sub_vertical,
            "typical_contracts": industry_info.get("typical_contracts", []),
            "key_clause_focus": industry_info.get("key_clause_focus", []),
        }

    def _detect_sub_vertical(
        self,
        text: str,
        industry: str,
    ) -> Optional[str]:
        """Detect sub-vertical within an industry.

        Args:
            text: Contract text.
            industry: Primary industry.

        Returns:
            Sub-vertical identifier or None.
        """
        sub_keywords: Dict[str, List[str]] = {
            "b2b_saas": ["enterprise", "b2b", "business", "corporate"],
            "b2c_saas": ["consumer", "personal", "individual", "b2c"],
            "automotive": ["automotive", "car", "vehicle", "auto"],
            "aerospace": ["aerospace", "aviation", "aircraft", "defense"],
            "healthcare_provider": ["hospital", "clinic", "provider", "physician"],
            "pharma": ["pharmaceutical", "drug", "pharma", "clinical trial"],
            "banking": ["bank", "lending", "deposit", "loan"],
            "insurance": ["insurance", "underwriting", "policy", "claim"],
            "ecommerce": ["ecommerce", "online store", "web shop", "marketplace"],
            "construction": ["construction", "building", "contractor", "subcontractor"],
        }

        for sub_id, keywords in sub_keywords.items():
            if any(kw in text for kw in keywords):
                return sub_id

        return None

    async def get_segment_benchmarks(
        self,
        industry: str,
        sub_vertical: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get benchmark data for an industry segment.

        Args:
            industry: Industry identifier.
            sub_vertical: Optional sub-vertical filter.

        Returns:
            Dict with segment benchmark data.
        """
        industry_info = self._verticals.get(industry)
        if not industry_info:
            return {"error": f"Unknown industry: {industry}"}

        segment_key = f"{industry}_{sub_vertical}" if sub_vertical else industry
        segment = self._segments.get(segment_key)

        if not segment:
            # Return empty segment with metadata
            return {
                "industry": industry,
                "industry_name": industry_info["name"],
                "sub_vertical": sub_vertical,
                "sub_vertical_name": self._get_sub_vertical_name(industry, sub_vertical) if sub_vertical else None,
                "available": False,
                "contract_count": 0,
                "clause_count": 0,
                "typical_contracts": industry_info["typical_contracts"],
                "key_clause_focus": industry_info["key_clause_focus"],
                "message": "No benchmark data available for this segment yet",
            }

        return {
            "industry": industry,
            "industry_name": industry_info["name"],
            "sub_vertical": sub_vertical,
            "available": True,
            "data": segment.to_dict(),
        }

    def _get_sub_vertical_name(self, industry: str, sub_vertical: str) -> Optional[str]:
        """Get human-readable sub-vertical name.

        Args:
            industry: Industry identifier.
            sub_vertical: Sub-vertical identifier.

        Returns:
            Human-readable name or None.
        """
        names = {
            "saas": {"b2b_saas": "B2B SaaS", "b2c_saas": "B2C SaaS", "paas": "PaaS",
                     "iaas": "IaaS", "cloud_infrastructure": "Cloud Infrastructure"},
            "manufacturing": {"automotive": "Automotive", "aerospace": "Aerospace",
                              "electronics": "Electronics", "industrial": "Industrial"},
            "healthcare": {"healthcare_provider": "Healthcare Provider", "pharma": "Pharmaceuticals",
                           "biotech": "Biotechnology", "medical_devices": "Medical Devices"},
        }
        return names.get(industry, {}).get(sub_vertical)

    async def get_all_verticals(self) -> Dict[str, Any]:
        """Get all available industry verticals.

        Returns:
            Dict with vertical definitions.
        """
        return {
            industry_id: {
                "name": info["name"],
                "sub_verticals": info["sub_verticals"],
                "typical_contracts": info["typical_contracts"],
                "key_clause_focus": info["key_clause_focus"],
            }
            for industry_id, info in self._verticals.items()
        }

    async def get_segmentation_summary(self) -> Dict[str, Any]:
        """Get a summary of all industry segments.

        Returns:
            Dict with segmentation summary.
        """
        populated_segments = [
            s.to_dict() for s in self._segments.values()
            if s.contract_count > 0
        ]

        return {
            "total_verticals": len(self._verticals),
            "populated_segments": len(populated_segments),
            "total_contracts_in_corpus": sum(s.contract_count for s in self._segments.values()),
            "total_clauses_in_corpus": sum(s.clause_count for s in self._segments.values()),
            "segments": populated_segments,
        }
