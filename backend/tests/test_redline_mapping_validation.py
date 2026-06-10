"""Tests for redline-to-finding mapping integrity."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.domains.review.mapping_validation import (
    categories_compatible,
    normalize_category,
    validate_redline_finding_mapping,
)


def _redline(**kwargs):
    defaults = {
        "finding_id": None,
        "clause_type": "liability",
        "proposed_text": "Limitation of Liability. Cap at 12 months fees.",
        "redline_metadata": {},
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _finding(**kwargs):
    defaults = {
        "finding_id": uuid.uuid4(),
        "title": "Missing Liability Cap Clause",
        "clause_type": "liability",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestCategoryNormalization:
    def test_liability_aliases(self):
        assert normalize_category("liability_caps") == "liability"
        assert normalize_category("limitation_of_liability") == "liability"

    def test_data_privacy_maps_to_data_protection(self):
        assert normalize_category("data_privacy") == "data_protection"
        assert normalize_category("privacy") == "data_protection"

    def test_ip_aliases(self):
        assert normalize_category("intellectual_property") == "ip"

    def test_cross_category_not_compatible(self):
        assert categories_compatible("liability", "data_protection") is False
        assert categories_compatible("liability", "liability") is True


class TestMappingValidation:
    def test_liability_finding_liability_redline_valid(self):
        finding = _finding(title="Missing Liability Cap Clause", clause_type="liability")
        redline = _redline(
            finding_id=finding.finding_id,
            clause_type="liability",
            proposed_text="Aggregate liability shall not exceed 12 months fees.",
        )
        result = validate_redline_finding_mapping(redline, finding)
        assert result.valid is True
        assert result.mapping_status == "valid"
        assert result.finding_title == "Missing Liability Cap Clause"

    def test_privacy_finding_liability_redline_invalid(self):
        finding = _finding(
            title="Missing Data Privacy Clause",
            clause_type="data_privacy",
        )
        redline = _redline(
            finding_id=finding.finding_id,
            clause_type="liability",
            proposed_text="Limitation of Liability. Cap at 12 months fees.",
        )
        result = validate_redline_finding_mapping(redline, finding)
        assert result.valid is False
        assert result.mapping_status == "invalid_mapping"
        assert "does not match" in (result.warning or "").lower()

    def test_ip_finding_ip_redline_valid(self):
        finding = _finding(title="IP Ownership Risk", clause_type="intellectual_property")
        redline = _redline(
            finding_id=finding.finding_id,
            clause_type="ip",
            proposed_text="All intellectual property rights remain with Customer.",
        )
        result = validate_redline_finding_mapping(redline, finding)
        assert result.valid is True

    def test_missing_finding_id_invalid(self):
        redline = _redline(finding_id=None, clause_type="liability")
        result = validate_redline_finding_mapping(redline, None)
        assert result.valid is False
        assert "not linked" in (result.warning or "").lower()

    def test_displayed_finding_mismatch_invalid(self):
        finding = _finding(clause_type="liability")
        redline = _redline(finding_id=finding.finding_id, clause_type="liability")
        other_id = str(uuid.uuid4())
        result = validate_redline_finding_mapping(
            redline,
            finding,
            displayed_finding_id=other_id,
        )
        assert result.valid is False
        assert "does not match" in (result.warning or "").lower()
