"""Tests for redline coverage audit and NDA clause mapping."""

from app.domains.ai.schemas import _canonicalize_clause_type
from app.domains.review.clause_category import resolve_mitigation_plan
from app.domains.review.redline_coverage import audit_finding_redline_coverage


def test_nda_clause_types_canonicalize():
    assert _canonicalize_clause_type("return_of_information") == "confidentiality"
    assert _canonicalize_clause_type("remedies") == "confidentiality"
    assert _canonicalize_clause_type("no_license") == "intellectual_property"
    assert _canonicalize_clause_type("exclusions") == "confidentiality"


def test_resolve_mitigation_plan_nda_return():
    plan = resolve_mitigation_plan(
        "return_of_information",
        title="Missing Return of Information Clause",
    )
    assert plan.clause_category == "confidentiality"
    assert plan.mitigation_type == "adding_return_of_information"


def test_resolve_mitigation_plan_from_title_hint():
    plan = resolve_mitigation_plan(
        "other",
        title="Missing remedies for breach of confidentiality",
    )
    assert plan.mitigation_type == "adding_remedies_clause"


def test_coverage_audit_gaps():
    findings = [
        {"finding_id": "f1", "clause_type": "confidentiality", "title": "Weak NDA", "severity": "high"},
        {"finding_id": "f2", "clause_type": "return_of_information", "title": "No return clause", "severity": "medium"},
        {"finding_id": "f3", "clause_type": "remedies", "title": "No remedies", "severity": "medium"},
    ]
    redlines = [
        {"redline_id": "r1", "finding_id": "f1", "clause_type": "confidentiality"},
    ]
    report = audit_finding_redline_coverage(findings, redlines)
    assert report["findings"] == 3
    assert report["redlines"] == 1
    assert report["findings_without_redline"] == 2
    assert report["coverage_pct"] == 33.3
    assert len(report["missing_redline_templates"]) >= 0
