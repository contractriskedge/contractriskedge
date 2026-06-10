"""Tests for policy-to-finding linkage helpers."""

from app.domains.review.policy_linkage import (
    pick_best_rule,
    rule_matches_finding,
    build_violation_dto,
)


def test_rule_matches_finding_by_target_category():
    finding = {"clause_type": "liability", "title": "Uncapped liability"}
    rule = {"name": "Liability Cap", "target_category": "liability", "conditions": {}}
    assert rule_matches_finding(finding, rule) is True


def test_rule_matches_finding_by_name_keyword():
    finding = {"clause_type": "data_privacy", "title": "Missing DPA"}
    rule = {"name": "GDPR Compliance — DPA Required", "target_category": None, "conditions": {}}
    assert rule_matches_finding(finding, rule) is True


def test_pick_best_rule_prefers_lower_priority_number():
    finding = {"clause_type": "liability", "title": "Cap issue"}
    rules = [
        {"rule_id": "a", "playbook_id": "p1", "name": "Low", "target_category": "liability", "priority": 50, "conditions": {}},
        {"rule_id": "b", "playbook_id": "p1", "name": "High", "target_category": "liability", "priority": 10, "conditions": {}},
    ]
    best = pick_best_rule(finding, rules)
    assert best is not None
    assert best["rule_id"] == "b"


def test_build_violation_dto_includes_traceability():
    dto = build_violation_dto(
        finding={"finding_id": "f1", "clause_type": "liability", "severity": "high", "title": "Cap", "description": "d"},
        rule={"rule_id": "r1", "playbook_id": "p1", "name": "Liability Cap", "effect": "flag_for_review", "is_mandatory": True},
        playbook={"name": "Commercial Playbook", "created_by": "Legal Ops"},
        version_label="v1.0",
        review_id="rev1",
        redline_count=2,
    )
    assert dto["policy_name"] == "Commercial Playbook"
    assert dto["traceability"]["redline_count"] == 2
    assert dto["rule_id"] == "r1"
