"""Compliance drift detection (V2-020).

Monitors contracts for compliance drift against regulatory frameworks
(GDPR, CCPA, CSRD, etc.). Detects when regulatory requirements change
and flags contracts that may no longer be compliant. Integrates with
the obligation event bus.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .event_bus import ObligationEventBus, ObligationEvent, EventType, EventPriority

logger = logging.getLogger(__name__)


# Regulatory frameworks with key requirements
REGULATORY_FRAMEWORKS = {
    "gdpr": {
        "name": "GDPR",
        "full_name": "General Data Protection Regulation",
        "jurisdiction": "EU/EEA",
        "effective_date": "2018-05-25",
        "key_requirements": [
            "data_processing_agreement",
            "data_breach_notification_72h",
            "data_subject_access_rights",
            "right_to_erasure",
            "data_portability",
            "consent_requirement",
            "data_protection_officer_appointment",
            "cross_border_data_transfer_safeguards",
            "data_protection_impact_assessment",
            "records_of_processing_activities",
        ],
    },
    "ccpa": {
        "name": "CCPA",
        "full_name": "California Consumer Privacy Act",
        "jurisdiction": "California, USA",
        "effective_date": "2020-01-01",
        "key_requirements": [
            "right_to_know",
            "right_to_delete",
            "right_to_opt_out",
            "non_discrimination",
            "data_collection_disclosure",
            "category_of_sources_disclosure",
            "business_purpose_disclosure",
            "third_party_sharing_disclosure",
        ],
    },
    "csrd": {
        "name": "CSRD",
        "full_name": "Corporate Sustainability Reporting Directive",
        "jurisdiction": "EU",
        "effective_date": "2024-01-01",
        "key_requirements": [
            "double_materiality_assessment",
            "esg_reporting",
            "greenhouse_gas_emissions_reporting",
            "social_impact_reporting",
            "value_chain_sustainability",
            "audit_assurance_requirement",
            "digital_tagging_of_reports",
        ],
    },
    "uk_modern_slavery": {
        "name": "UK Modern Slavery Act",
        "full_name": "UK Modern Slavery Act 2015",
        "jurisdiction": "United Kingdom",
        "effective_date": "2015-10-29",
        "key_requirements": [
            "slavery_statement",
            "supply_due_diligence",
            "board_approval_statement",
            "training_provision",
            "risk_assessment",
        ],
    },
    "hipaa": {
        "name": "HIPAA",
        "full_name": "Health Insurance Portability and Accountability Act",
        "jurisdiction": "USA",
        "effective_date": "1996-08-21",
        "key_requirements": [
            "baa_agreement",
            "privacy_rule_compliance",
            "security_rule_compliance",
            "breach_notification",
            "minimum_necessary_standard",
            "administrative_safeguards",
            "physical_safeguards",
            "technical_safeguards",
        ],
    },
}


@dataclass
class ComplianceCheck:
    """Result of a compliance drift check for a contract."""

    check_id: str
    contract_id: str
    tenant_id: str
    framework: str
    framework_version: str
    checked_at: str
    overall_compliance_score: float  # 0.0 - 1.0
    requirement_results: Dict[str, bool]  # requirement -> compliant (True/False)
    missing_requirements: List[str]
    drift_detected: bool
    drift_severity: str  # none, low, medium, high, critical
    previous_score: Optional[float] = None
    score_change: Optional[float] = None
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "check_id": self.check_id,
            "contract_id": self.contract_id,
            "tenant_id": self.tenant_id,
            "framework": self.framework,
            "framework_version": self.framework_version,
            "checked_at": self.checked_at,
            "overall_compliance_score": round(self.overall_compliance_score, 3),
            "requirement_results": self.requirement_results,
            "missing_requirements": self.missing_requirements,
            "drift_detected": self.drift_detected,
            "drift_severity": self.drift_severity,
            "previous_score": round(self.previous_score, 3) if self.previous_score is not None else None,
            "score_change": round(self.score_change, 3) if self.score_change is not None else None,
            "recommendations": self.recommendations,
        }


class ComplianceMonitor:
    """Monitors contracts for regulatory compliance drift.

    Checks contract clauses against regulatory framework requirements,
    tracks changes in compliance scores over time, and emits events
    when drift is detected.

    Usage:
        monitor = ComplianceMonitor(event_bus)
        result = await monitor.check_compliance(contract_id, clauses, "gdpr")
        report = await monitor.get_drift_report("tenant-123")
    """

    def __init__(
        self,
        event_bus: ObligationEventBus,
        llm_client: Optional[Any] = None,
        db_pool: Optional[Any] = None,
    ) -> None:
        """Initialize the compliance monitor.

        Args:
            event_bus: The obligation event bus.
            llm_client: Optional LLM client for AI-powered analysis.
            db_pool: Optional database pool for persistence.
        """
        self._event_bus = event_bus
        self._llm_client = llm_client
        self._db_pool = db_pool
        self._check_history: Dict[str, List[ComplianceCheck]] = {}  # contract_id -> checks
        self._frameworks = REGULATORY_FRAMEWORKS

    def get_available_frameworks(self) -> Dict[str, Any]:
        """Get all available regulatory frameworks.

        Returns:
            Dict of framework configurations.
        """
        return {
            key: {
                "name": config["name"],
                "full_name": config["full_name"],
                "jurisdiction": config["jurisdiction"],
                "effective_date": config["effective_date"],
                "key_requirements": config["key_requirements"],
            }
            for key, config in self._frameworks.items()
        }

    async def check_compliance(
        self,
        contract_id: str,
        tenant_id: str,
        clauses: List[Dict[str, Any]],
        framework: str,
    ) -> ComplianceCheck:
        """Check a contract's compliance against a regulatory framework.

        Analyzes contract clauses against framework requirements and
        computes a compliance score. Detects drift from previous checks.

        Args:
            contract_id: The contract identifier.
            tenant_id: The tenant identifier.
            clauses: List of clause dicts with text and metadata.
            framework: The regulatory framework key (gdpr, ccpa, csrd, etc.).

        Returns:
            ComplianceCheck with results.
        """
        framework_config = self._frameworks.get(framework)
        if not framework_config:
            raise ValueError(f"Unknown framework: {framework}. Available: {list(self._frameworks.keys())}")

        requirements = framework_config["key_requirements"]
        clause_texts = [c.get("text", "") or c.get("clause_text", "") for c in clauses]
        combined_text = " ".join(clause_texts).lower()

        # Check each requirement against contract clauses
        requirement_results: Dict[str, bool] = {}
        missing_requirements: List[str] = []

        if self._llm_client:
            # Use LLM for intelligent compliance analysis
            requirement_results = await self._llm_analyze_compliance(
                combined_text, requirements, framework
            )
        else:
            # Use keyword-based heuristic analysis
            requirement_results = self._keyword_analyze_compliance(
                combined_text, requirements, framework
            )

        missing_requirements = [
            req for req, compliant in requirement_results.items() if not compliant
        ]

        # Compute overall score
        total_reqs = len(requirements)
        met_reqs = sum(1 for v in requirement_results.values() if v)
        overall_score = met_reqs / total_reqs if total_reqs > 0 else 0.0

        # Check for drift from previous check
        previous_checks = self._check_history.get(contract_id, [])
        previous_score = previous_checks[-1].overall_compliance_score if previous_checks else None
        score_change = overall_score - previous_score if previous_score is not None else None

        # Determine drift severity
        drift_detected = False
        drift_severity = "none"
        if previous_score is not None and score_change is not None:
            if abs(score_change) > 0.2:
                drift_detected = True
                drift_severity = "high" if score_change < 0 else "medium"
            elif abs(score_change) > 0.1:
                drift_detected = True
                drift_severity = "medium" if score_change < 0 else "low"
            elif abs(score_change) > 0.05:
                drift_detected = True
                drift_severity = "low"

        # Generate recommendations
        recommendations = self._generate_recommendations(
            missing_requirements, framework, framework_config
        )

        check = ComplianceCheck(
            check_id=str(uuid.uuid4()),
            contract_id=contract_id,
            tenant_id=tenant_id,
            framework=framework,
            framework_version="1.0",
            checked_at=datetime.utcnow().isoformat(),
            overall_compliance_score=overall_score,
            requirement_results=requirement_results,
            missing_requirements=missing_requirements,
            drift_detected=drift_detected,
            drift_severity=drift_severity,
            previous_score=previous_score,
            score_change=score_change,
            recommendations=recommendations,
        )

        # Store in history
        if contract_id not in self._check_history:
            self._check_history[contract_id] = []
        self._check_history[contract_id].append(check)

        # Emit event if drift detected
        if drift_detected and drift_severity in ("medium", "high", "critical"):
            priority_map = {
                "critical": EventPriority.CRITICAL,
                "high": EventPriority.HIGH,
                "medium": EventPriority.MEDIUM,
                "low": EventPriority.LOW,
            }
            event = ObligationEventBus.create_event(
                event_type=EventType.COMPLIANCE_DRIFT_DETECTED,
                contract_id=contract_id,
                tenant_id=tenant_id,
                title=f"Compliance drift detected: {framework_config['name']}",
                description=(
                    f"Contract {contract_id} shows compliance drift against {framework_config['name']}. "
                    f"Score changed from {previous_score:.1% if previous_score else 'N/A'} "
                    f"to {overall_score:.1%}. Missing requirements: {', '.join(missing_requirements[:5])}"
                ),
                priority=priority_map.get(drift_severity, EventPriority.MEDIUM),
                risk_score=round((1.0 - overall_score) * 10.0, 2),
                metadata={
                    "framework": framework,
                    "framework_name": framework_config["name"],
                    "overall_score": overall_score,
                    "previous_score": previous_score,
                    "score_change": score_change,
                    "drift_severity": drift_severity,
                    "missing_requirements": missing_requirements,
                    "total_requirements": total_reqs,
                    "met_requirements": met_reqs,
                },
            )
            await self._event_bus.emit(event)

        logger.info(
            "Compliance check for contract %s against %s: score=%.2f, drift=%s",
            contract_id, framework, overall_score, drift_severity,
        )

        return check

    def _keyword_analyze_compliance(
        self,
        text: str,
        requirements: List[str],
        framework: str,
    ) -> Dict[str, bool]:
        """Keyword-based compliance analysis (fallback when no LLM).

        Args:
            text: Combined clause text.
            requirements: List of requirement keys.
            framework: Framework key.

        Returns:
            Dict of requirement -> compliant.
        """
        # Keyword mappings for each requirement
        keyword_map: Dict[str, List[str]] = {
            # GDPR
            "data_processing_agreement": ["data processing", "processing agreement", "dpa"],
            "data_breach_notification_72h": ["breach notification", "data breach", "72 hour", "72-hour"],
            "data_subject_access_rights": ["access request", "subject access", "data subject"],
            "right_to_erasure": ["erasure", "right to be forgotten", "delete", "removal"],
            "data_portability": ["portability", "data portable"],
            "consent_requirement": ["consent", "opt-in", "opt in"],
            "cross_border_data_transfer_safeguards": ["cross-border", "cross border", "transfer", "adequacy decision", "scc", "standard contractual"],
            "data_protection_officer_appointment": ["data protection officer", "dpo"],
            "data_protection_impact_assessment": ["impact assessment", "dpia", "data protection impact"],
            "records_of_processing_activities": ["processing activities", "records of processing", "ropa"],
            # CCPA
            "right_to_know": ["right to know", "access", "information request"],
            "right_to_delete": ["right to delete", "deletion", "remove personal"],
            "right_to_opt_out": ["opt-out", "opt out", "do not sell", "right to opt"],
            "non_discrimination": ["non-discrimination", "non discrimination", "no discrimination"],
            "data_collection_disclosure": ["collection", "disclose collection"],
            # CSRD
            "double_materiality_assessment": ["double materiality", "materiality assessment"],
            "esg_reporting": ["esg", "sustainability", "environmental", "social", "governance"],
            "greenhouse_gas_emissions_reporting": ["greenhouse gas", "ghg", "carbon emission", "scope 1", "scope 2", "scope 3"],
            "social_impact_reporting": ["social impact", "human rights", "labor", "community"],
            # UK Modern Slavery
            "slavery_statement": ["slavery statement", "modern slavery", "slavery and trafficking"],
            "supply_due_diligence": ["due diligence", "supply chain", "supplier"],
            # HIPAA
            "baa_agreement": ["baa", "business associate", "business associate agreement"],
            "privacy_rule_compliance": ["privacy rule", "protected health", "phi", "privacy practice"],
            "security_rule_compliance": ["security rule", "administrative safeguard", "physical safeguard", "technical safeguard"],
            "breach_notification": ["breach notification", "breach notice", "notification of breach"],
        }

        results: Dict[str, bool] = {}
        for req in requirements:
            keywords = keyword_map.get(req, [req.replace("_", " ")])
            found = any(kw in text for kw in keywords)
            results[req] = found

        return results

    async def _llm_analyze_compliance(
        self,
        text: str,
        requirements: List[str],
        framework: str,
    ) -> Dict[str, bool]:
        """LLM-powered compliance analysis.

        Uses the LLM client for intelligent compliance checking.

        Args:
            text: Combined clause text.
            requirements: List of requirement keys.
            framework: Framework key.

        Returns:
            Dict of requirement -> compliant.
        """
        if not self._llm_client:
            return self._keyword_analyze_compliance(text, requirements, framework)

        try:
            prompt = (
                f"Analyze the following contract text for compliance with {framework} requirements. "
                f"For each requirement, determine if the contract adequately addresses it. "
                f"Return a JSON object with requirement names as keys and boolean compliance values.\n\n"
                f"Requirements: {json.dumps(requirements)}\n\n"
                f"Contract text:\n{text[:8000]}"
            )

            response = await self._llm_client.complete(prompt)
            result = json.loads(response)

            # Ensure all requirements are present
            for req in requirements:
                if req not in result:
                    result[req] = False

            return result

        except Exception as exc:
            logger.warning("LLM compliance analysis failed, falling back to keyword: %s", exc)
            return self._keyword_analyze_compliance(text, requirements, framework)

    def _generate_recommendations(
        self,
        missing_requirements: List[str],
        framework: str,
        framework_config: Dict[str, Any],
    ) -> List[str]:
        """Generate remediation recommendations for missing requirements.

        Args:
            missing_requirements: List of missing requirement keys.
            framework: Framework key.
            framework_config: Framework configuration.

        Returns:
            List of recommendation strings.
        """
        recommendation_map: Dict[str, str] = {
            "data_processing_agreement": "Add a Data Processing Agreement (DPA) as a schedule or exhibit.",
            "data_breach_notification_72h": "Include a data breach notification clause requiring notification within 72 hours.",
            "data_subject_access_rights": "Add provisions for data subject access requests with defined response timelines.",
            "right_to_erasure": "Include a 'right to erasure' clause allowing data subjects to request deletion.",
            "data_portability": "Add data portability provisions enabling data subjects to receive their data in a structured format.",
            "consent_requirement": "Include consent mechanisms for data processing activities where required.",
            "cross_border_data_transfer_safeguards": "Add Standard Contractual Clauses (SCCs) or adequacy decision references for cross-border transfers.",
            "data_protection_officer_appointment": "Include provision for appointment of a Data Protection Officer (DPO).",
            "data_protection_impact_assessment": "Add requirement for Data Protection Impact Assessments (DPIAs) for high-risk processing.",
            "records_of_processing_activities": "Include obligation to maintain Records of Processing Activities (ROPA).",
            "right_to_know": "Add a 'right to know' clause specifying what personal information is collected.",
            "right_to_delete": "Include a deletion right clause per CCPA requirements.",
            "right_to_opt_out": "Add a 'Do Not Sell My Personal Information' opt-out mechanism.",
            "non_discrimination": "Include a non-discrimination clause for consumers exercising CCPA rights.",
            "data_collection_disclosure": "Add disclosure of categories of personal information collected.",
            "double_materiality_assessment": "Include a double materiality assessment process per CSRD requirements.",
            "esg_reporting": "Add ESG reporting obligations aligned with CSRD standards.",
            "greenhouse_gas_emissions_reporting": "Include GHG emissions reporting requirements (Scope 1, 2, and 3).",
            "social_impact_reporting": "Add social impact reporting covering human rights and labor practices.",
            "slavery_statement": "Include a modern slavery statement per UK Modern Slavery Act requirements.",
            "supply_due_diligence": "Add supply chain due diligence provisions for modern slavery risks.",
            "baa_agreement": "Include a Business Associate Agreement (BAA) as required by HIPAA.",
            "privacy_rule_compliance": "Add HIPAA Privacy Rule compliance provisions for protected health information.",
            "security_rule_compliance": "Include HIPAA Security Rule safeguards (administrative, physical, technical).",
            "breach_notification": "Add breach notification provisions per HIPAA requirements.",
        }

        return [
            recommendation_map.get(req, f"Review and address missing requirement: {req}")
            for req in missing_requirements
        ]

    async def get_drift_report(self, tenant_id: str) -> Dict[str, Any]:
        """Generate a compliance drift report for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with drift summary and details.
        """
        all_checks: List[ComplianceCheck] = []
        for checks in self._check_history.values():
            all_checks.extend(checks)

        tenant_checks = [c for c in all_checks if c.tenant_id == tenant_id]

        # Latest check per contract
        latest_per_contract: Dict[str, ComplianceCheck] = {}
        for check in tenant_checks:
            if check.contract_id not in latest_per_contract or \
               check.checked_at > latest_per_contract[check.contract_id].checked_at:
                latest_per_contract[check.contract_id] = check

        contracts_with_drift = sum(1 for c in latest_per_contract.values() if c.drift_detected)
        avg_score = sum(c.overall_compliance_score for c in latest_per_contract.values()) / \
                    max(len(latest_per_contract), 1)

        by_framework: Dict[str, Dict[str, Any]] = {}
        for check in latest_per_contract.values():
            if check.framework not in by_framework:
                by_framework[check.framework] = {
                    "contracts_checked": 0,
                    "avg_score": 0.0,
                    "drift_count": 0,
                }
            by_framework[check.framework]["contracts_checked"] += 1
            by_framework[check.framework]["avg_score"] += check.overall_compliance_score
            if check.drift_detected:
                by_framework[check.framework]["drift_count"] += 1

        for fw in by_framework.values():
            fw["avg_score"] = round(fw["avg_score"] / fw["contracts_checked"], 3)

        return {
            "tenant_id": tenant_id,
            "contracts_checked": len(latest_per_contract),
            "contracts_with_drift": contracts_with_drift,
            "average_compliance_score": round(avg_score, 3),
            "by_framework": by_framework,
            "latest_checks": [c.to_dict() for c in latest_per_contract.values()],
        }

    async def check_regulatory_update(
        self,
        framework: str,
        new_requirements: List[str],
    ) -> List[Dict[str, Any]]:
        """Handle a regulatory framework update (new requirements).

        When regulations change, re-check all contracts monitored
        under that framework and emit regulatory change events.

        Args:
            framework: The framework key.
            new_requirements: Updated list of requirements.

        Returns:
            List of affected contract check results.
        """
        if framework not in self._frameworks:
            raise ValueError(f"Unknown framework: {framework}")

        old_requirements = set(self._frameworks[framework]["key_requirements"])
        new_req_set = set(new_requirements)
        added = new_req_set - old_requirements

        if not added:
            logger.info("No new requirements detected for %s", framework)
            return []

        # Update framework config
        self._frameworks[framework]["key_requirements"] = new_requirements

        logger.info(
            "Regulatory update for %s: %d new requirement(s): %s",
            framework, len(added), added,
        )

        # Find all contracts checked under this framework
        affected: List[Dict[str, Any]] = []
        for contract_id, checks in self._check_history.items():
            latest = checks[-1] if checks else None
            if latest and latest.framework == framework:
                # Emit regulatory change event
                event = ObligationEventBus.create_event(
                    event_type=EventType.REGULATORY_CHANGE,
                    contract_id=contract_id,
                    tenant_id=latest.tenant_id,
                    title=f"Regulatory update: {self._frameworks[framework]['name']}",
                    description=(
                        f"New requirements added to {self._frameworks[framework]['name']}: "
                        f"{', '.join(added)}. Re-check compliance."
                    ),
                    priority=EventPriority.HIGH,
                    risk_score=7.0,
                    metadata={
                        "framework": framework,
                        "new_requirements": list(added),
                        "previous_score": latest.overall_compliance_score,
                    },
                )
                await self._event_bus.emit(event)
                affected.append({
                    "contract_id": contract_id,
                    "tenant_id": latest.tenant_id,
                    "new_requirements": list(added),
                })

        return affected
