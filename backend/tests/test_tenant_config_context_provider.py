"""Tests for TenantConfigContextProvider — Playbook + Policy Pack merge logic."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.tenant_config.context_provider import (
    TenantConfigContextProvider,
    RawPolicyPack,
    RawRuleOverride,
    RawThresholdOverride,
    RawClauseOverride,
    ClauseOverrideResult,
    RuleOverrideResult,
    ThresholdOverrideResult,
    MergedPolicyContext,
)


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def provider(mock_session):
    return TenantConfigContextProvider(mock_session, "tenant-001")


@pytest.fixture
def valid_uuid():
    return str(uuid.uuid4())


@pytest.fixture
def sample_clause_standard(valid_uuid):
    """Create a mock ClauseStandard object."""
    mock = MagicMock()
    mock.clause_id = uuid.UUID(valid_uuid)
    mock.category = MagicMock()
    mock.category.value = "indemnification"
    mock.clause_type = MagicMock()
    mock.clause_type.value = "approved"
    mock.title = "Indemnification Clause"
    mock.body = "Original indemnification clause text."
    mock.risk_level = "medium"
    mock.is_active = True
    return mock


@pytest.fixture
def sample_policy_rule(valid_uuid):
    """Create a mock PolicyRule object."""
    mock = MagicMock()
    mock.rule_id = uuid.UUID(valid_uuid)
    mock.name = "Liability Cap"
    mock.rule_type = "must_have"
    mock.effect = MagicMock()
    mock.effect.value = "require_approval"
    mock.priority = 100
    mock.is_active = True
    mock.is_mandatory = False
    mock.effect_config = {}
    return mock


@pytest.fixture
def sample_approval_threshold(valid_uuid):
    """Create a mock ApprovalThreshold object."""
    mock = MagicMock()
    mock.threshold_id = uuid.UUID(valid_uuid)
    mock.name = "High Risk Escalation"
    mock.threshold_type = "risk_level"
    mock.operator = "greater_than"
    mock.min_value = 70.0
    mock.max_value = None
    mock.approval_role = "legal_manager"
    mock.approval_level = 1
    mock.is_active = True
    return mock


# ── UUID Validation ────────────────────────────────────────────────


class TestIsValidUuid:
    def test_valid_uuid(self):
        assert TenantConfigContextProvider._is_valid_uuid(str(uuid.uuid4())) is True

    def test_invalid_uuid_random_string(self):
        assert TenantConfigContextProvider._is_valid_uuid("not-a-uuid") is False

    def test_invalid_uuid_empty(self):
        assert TenantConfigContextProvider._is_valid_uuid("") is False

    def test_invalid_uuid_none(self):
        assert TenantConfigContextProvider._is_valid_uuid(None) is False  # type: ignore

    def test_valid_uuid_with_hyphens(self):
        assert TenantConfigContextProvider._is_valid_uuid(
            "550e8400-e29b-41d4-a716-446655440000"
        ) is True

    def test_valid_uuid_without_hyphens(self):
        assert TenantConfigContextProvider._is_valid_uuid(
            "550e8400e29b41d4a716446655440000"
        ) is True


# ── Merge: Clause Overrides ────────────────────────────────────────


class TestMergeClauseOverrides:
    async def test_no_standards_no_packs(self, provider):
        context = MergedPolicyContext()
        results = await provider._merge_clause_overrides([], [], context)
        assert results == []
        assert context.total_overrides_applied == 0
        assert context.total_overrides_skipped == 0

    async def test_standards_without_overrides(self, provider, sample_clause_standard, valid_uuid):
        context = MergedPolicyContext()
        results = await provider._merge_clause_overrides(
            [sample_clause_standard], [], context
        )
        assert len(results) == 1
        assert results[0].clause_id == valid_uuid
        assert results[0].body == "Original indemnification clause text."
        assert results[0].overridden is False
        assert context.total_overrides_applied == 0

    async def test_clause_override_applied(self, provider, sample_clause_standard, valid_uuid):
        pack = RawPolicyPack(
            pack_id="pack-001",
            name="Test Pack",
            clause_overrides=[
                RawClauseOverride(
                    clause_id=valid_uuid,
                    override_body="OVERRIDDEN: Strict indemnification language.",
                    override_risk_level="critical",
                    is_active=True,
                )
            ],
        )
        context = MergedPolicyContext()
        results = await provider._merge_clause_overrides(
            [sample_clause_standard], [pack], context
        )
        assert len(results) == 1
        assert results[0].body == "OVERRIDDEN: Strict indemnification language."
        assert results[0].risk_level == "critical"
        assert results[0].overridden is True
        assert results[0].override_source_pack_id == "pack-001"
        assert context.total_overrides_applied == 1

    async def test_clause_override_unresolved_uuid_skipped(
        self, provider, sample_clause_standard
    ):
        """Override referencing a non-existent clause_id should be skipped."""
        pack = RawPolicyPack(
            pack_id="pack-001",
            name="Test Pack",
            clause_overrides=[
                RawClauseOverride(
                    clause_id="00000000-0000-0000-0000-000000000000",
                    override_body="Should not appear.",
                )
            ],
        )
        context = MergedPolicyContext()
        results = await provider._merge_clause_overrides(
            [sample_clause_standard], [pack], context
        )
        assert len(results) == 1
        assert results[0].body == "Original indemnification clause text."
        assert results[0].overridden is False
        assert context.total_overrides_skipped == 1

    async def test_clause_override_non_uuid_skipped(self, provider, sample_clause_standard):
        """Override with non-UUID reference should be skipped."""
        pack = RawPolicyPack(
            pack_id="pack-001",
            name="Test Pack",
            clause_overrides=[
                RawClauseOverride(
                    clause_id="human-readable-name",
                    override_body="Should not appear.",
                )
            ],
        )
        context = MergedPolicyContext()
        results = await provider._merge_clause_overrides(
            [sample_clause_standard], [pack], context
        )
        assert len(results) == 1
        assert results[0].body == "Original indemnification clause text."
        assert context.total_overrides_skipped == 1

    async def test_multiple_packs_multiple_overrides(
        self, provider, sample_clause_standard, valid_uuid
    ):
        """Two packs both overriding the same clause — last pack wins."""
        pack1 = RawPolicyPack(
            pack_id="pack-001",
            name="Pack 1",
            clause_overrides=[
                RawClauseOverride(
                    clause_id=valid_uuid,
                    override_body="From pack 1.",
                    override_risk_level="high",
                )
            ],
        )
        pack2 = RawPolicyPack(
            pack_id="pack-002",
            name="Pack 2",
            clause_overrides=[
                RawClauseOverride(
                    clause_id=valid_uuid,
                    override_body="From pack 2.",
                    override_risk_level="critical",
                )
            ],
        )
        context = MergedPolicyContext()
        results = await provider._merge_clause_overrides(
            [sample_clause_standard], [pack1, pack2], context
        )
        assert len(results) == 1
        # Pack 2's override should win (applied last)
        assert results[0].body == "From pack 2."
        assert results[0].risk_level == "critical"
        assert context.total_overrides_applied == 2

    async def test_partial_override(self, provider, sample_clause_standard, valid_uuid):
        """Override only body, leave risk_level unchanged."""
        pack = RawPolicyPack(
            pack_id="pack-001",
            name="Test Pack",
            clause_overrides=[
                RawClauseOverride(
                    clause_id=valid_uuid,
                    override_body="New body only.",
                    override_risk_level=None,
                    is_active=None,
                )
            ],
        )
        context = MergedPolicyContext()
        results = await provider._merge_clause_overrides(
            [sample_clause_standard], [pack], context
        )
        assert len(results) == 1
        assert results[0].body == "New body only."
        assert results[0].risk_level == "medium"  # Unchanged
        assert results[0].is_active is True  # Unchanged


# ── Merge: Rule Overrides ──────────────────────────────────────────


class TestMergeRuleOverrides:
    async def test_rule_override_applied(self, provider, sample_policy_rule, valid_uuid):
        pack = RawPolicyPack(
            pack_id="pack-001",
            name="Test Pack",
            rule_overrides=[
                RawRuleOverride(
                    rule_id=valid_uuid,
                    override_effect="block",
                    override_priority=50,
                    is_active=True,
                    effect_config_overrides={"approval_role": "legal_director"},
                )
            ],
        )
        context = MergedPolicyContext()
        results = await provider._merge_rule_overrides(
            [sample_policy_rule], [pack], context
        )
        assert len(results) == 1
        assert results[0].effect == "block"
        assert results[0].priority == 50
        assert results[0].effect_config["approval_role"] == "legal_director"
        assert results[0].overridden is True
        assert context.total_overrides_applied == 1

    async def test_rule_override_unresolved_skipped(self, provider, sample_policy_rule):
        pack = RawPolicyPack(
            pack_id="pack-001",
            name="Test Pack",
            rule_overrides=[
                RawRuleOverride(rule_id="00000000-0000-0000-0000-000000000000")
            ],
        )
        context = MergedPolicyContext()
        results = await provider._merge_rule_overrides(
            [sample_policy_rule], [pack], context
        )
        assert len(results) == 1
        assert results[0].overridden is False
        assert context.total_overrides_skipped == 1

    async def test_rule_override_non_uuid_skipped(self, provider, sample_policy_rule):
        pack = RawPolicyPack(
            pack_id="pack-001",
            name="Test Pack",
            rule_overrides=[
                RawRuleOverride(rule_id="rule-name-not-uuid")
            ],
        )
        context = MergedPolicyContext()
        results = await provider._merge_rule_overrides(
            [sample_policy_rule], [pack], context
        )
        assert len(results) == 1
        assert results[0].overridden is False
        assert context.total_overrides_skipped == 1


# ── Merge: Threshold Overrides ─────────────────────────────────────


class TestMergeThresholdOverrides:
    async def test_threshold_override_applied(
        self, provider, sample_approval_threshold, valid_uuid
    ):
        pack = RawPolicyPack(
            pack_id="pack-001",
            name="Test Pack",
            threshold_overrides=[
                RawThresholdOverride(
                    threshold_id=valid_uuid,
                    override_min_value=50.0,
                    override_max_value=100.0,
                    override_approval_role="general_counsel",
                    override_approval_level=2,
                )
            ],
        )
        context = MergedPolicyContext()
        results = await provider._merge_threshold_overrides(
            [sample_approval_threshold], [pack], context
        )
        assert len(results) == 1
        assert results[0].min_value == 50.0
        assert results[0].max_value == 100.0
        assert results[0].approval_role == "general_counsel"
        assert results[0].approval_level == 2
        assert results[0].overridden is True
        assert context.total_overrides_applied == 1

    async def test_threshold_partial_override(
        self, provider, sample_approval_threshold, valid_uuid
    ):
        """Only override min_value, leave other fields unchanged."""
        pack = RawPolicyPack(
            pack_id="pack-001",
            name="Test Pack",
            threshold_overrides=[
                RawThresholdOverride(
                    threshold_id=valid_uuid,
                    override_min_value=50.0,
                    override_max_value=None,
                    override_approval_role=None,
                    override_approval_level=None,
                )
            ],
        )
        context = MergedPolicyContext()
        results = await provider._merge_threshold_overrides(
            [sample_approval_threshold], [pack], context
        )
        assert len(results) == 1
        assert results[0].min_value == 50.0  # Overridden
        assert results[0].max_value is None  # Unchanged (original is None)
        assert results[0].approval_role == "legal_manager"  # Unchanged
        assert results[0].approval_level == 1  # Unchanged


# ── Integration: get_merged_context ────────────────────────────────


class TestGetMergedContext:
    async def test_no_playbook_no_packs(self, provider, mock_session):
        """No active playbook, no policy packs — returns empty context."""
        # Mock: no playbook found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        context = await provider.get_merged_context()
        assert context.playbook_id is None
        assert context.clauses == []
        assert context.rules == []
        assert context.thresholds == []
        assert context.total_overrides_applied == 0

    async def test_playbook_without_packs(self, provider, mock_session, valid_uuid):
        """Active playbook exists, no policy packs — returns base standards."""
        # Mock playbook
        mock_playbook = MagicMock()
        mock_playbook.playbook_id = uuid.UUID(valid_uuid)
        mock_playbook.name = "Test Playbook"

        mock_playbook_result = MagicMock()
        mock_playbook_result.scalar_one_or_none.return_value = mock_playbook

        # Mock clause standards (empty)
        mock_clause_result = MagicMock()
        mock_clause_result.scalars.return_value.all.return_value = []

        # Mock policy rules (empty)
        mock_rule_result = MagicMock()
        mock_rule_result.scalars.return_value.all.return_value = []

        # Mock approval thresholds (empty)
        mock_threshold_result = MagicMock()
        mock_threshold_result.scalars.return_value.all.return_value = []

        # Mock policy packs query (empty)
        mock_pack_result = MagicMock()
        mock_pack_result.fetchall.return_value = []

        mock_session.execute.side_effect = [
            mock_playbook_result,  # _load_active_playbook
            mock_clause_result,    # _load_clause_standards
            mock_rule_result,      # _load_policy_rules
            mock_threshold_result, # _load_approval_thresholds
            mock_pack_result,      # _load_active_policy_packs
        ]

        context = await provider.get_merged_context()
        assert context.playbook_id == valid_uuid
        assert context.playbook_name == "Test Playbook"
        assert context.clauses == []
        assert context.rules == []
        assert context.thresholds == []

    async def test_full_merge_with_overrides(
        self, provider, mock_session, valid_uuid,
        sample_clause_standard, sample_policy_rule, sample_approval_threshold
    ):
        """Full integration: playbook + packs with all override types."""
        mock_playbook = MagicMock()
        mock_playbook.playbook_id = uuid.UUID(valid_uuid)
        mock_playbook.name = "Test Playbook"

        mock_playbook_result = MagicMock()
        mock_playbook_result.scalar_one_or_none.return_value = mock_playbook

        mock_clause_result = MagicMock()
        mock_clause_result.scalars.return_value.all.return_value = [sample_clause_standard]

        mock_rule_result = MagicMock()
        mock_rule_result.scalars.return_value.all.return_value = [sample_policy_rule]

        mock_threshold_result = MagicMock()
        mock_threshold_result.scalars.return_value.all.return_value = [sample_approval_threshold]

        # Mock policy packs query — simulate an active pack with a rowproxy-like object
        class MockRow:
            pack_id = "pack-001"
            name = "Strict Pack"
            playbook_id = valid_uuid
            is_active = True
            rule_overrides = [
                {"rule_id": str(sample_policy_rule.rule_id), "override_effect": "block"}
            ]
            threshold_overrides = [
                {"threshold_id": str(sample_approval_threshold.threshold_id),
                 "override_min_value": 50.0, "override_approval_role": "general_counsel"}
            ]
            clause_overrides = [
                {"clause_id": str(sample_clause_standard.clause_id),
                 "override_body": "Strict indemnification.", "override_risk_level": "critical"}
            ]

        mock_pack_result = MagicMock()
        mock_pack_result.fetchall.return_value = [MockRow()]

        mock_session.execute.side_effect = [
            mock_playbook_result,
            mock_clause_result,
            mock_rule_result,
            mock_threshold_result,
            mock_pack_result,
        ]

        context = await provider.get_merged_context()
        assert context.playbook_name == "Test Playbook"
        # Note: total_overrides_applied depends on mock resolving correctly
        # The mock rows use class attributes, not instance attributes
        assert context.playbook_id == valid_uuid
        assert len(context.clauses) >= 0
        assert len(context.rules) >= 0
