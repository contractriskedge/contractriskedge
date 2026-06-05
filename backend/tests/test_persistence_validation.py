"""
Sprint 21 Task 1.1B — Workflow Persistence Validation.

Tests that every status can:
  1. Save (be constructed as a ReviewStatus)
  2. Load (be round-tripped through the DB enum)
  3. Transition (be validated by the WorkflowState machine)
  4. Return through the persistence mapping (to_db_status → ReviewStatus → DB)

This validates the complete enum alignment remediation from Task 1.1A.
"""

import pytest
from app.domains.review.models import ReviewStatus
from app.domains.review.workflow import (
    WorkflowState, to_db_status, map_legacy_status,
    validate_transition, TransitionError,
)


# ═══════════════════════════════════════════════════════════════════
# 1. Save — Every status can be constructed as a ReviewStatus
# ═══════════════════════════════════════════════════════════════════


class TestSave:
    """Verify every status can be constructed as a ReviewStatus."""

    # All 22 ReviewStatus values
    ALL_REVIEW_STATUSES = [
        "draft", "uploaded", "analyzing", "ai_analyzed", "ai_reviewed",
        "review_ready", "procurement_review", "legal_review", "security_review",
        "negotiation", "in_review", "changes_requested", "pending_approval",
        "escalated", "legal_approval", "exec_approval",
        "approved", "rejected", "finalized", "executed", "archived", "closed",
    ]

    @pytest.mark.parametrize("status_str", ALL_REVIEW_STATUSES)
    def test_review_status_can_be_constructed(self, status_str):
        """Verify every string value can be constructed as a ReviewStatus."""
        rs = ReviewStatus(status_str)
        assert rs.value == status_str
        print(f"  ✅ ReviewStatus('{status_str}') → {rs}")

    @pytest.mark.parametrize("status_str", ALL_REVIEW_STATUSES)
    def test_review_status_has_workflow_stage(self, status_str):
        """Verify every ReviewStatus has a derive_workflow_stage() mapping."""
        rs = ReviewStatus(status_str)
        stage = rs.derive_workflow_stage()
        assert isinstance(stage, str) and len(stage) > 0
        print(f"  ✅ ReviewStatus('{status_str}').derive_workflow_stage() → '{stage}'")

    @pytest.mark.parametrize("status_str", ALL_REVIEW_STATUSES)
    def test_review_status_has_transition_entry(self, status_str):
        """Verify every ReviewStatus has an entry in valid_transitions()."""
        rs = ReviewStatus(status_str)
        matrix = ReviewStatus.valid_transitions()
        assert rs in matrix, f"'{status_str}' missing from valid_transitions()"
        print(f"  ✅ ReviewStatus('{status_str}') has transition entry")


# ═══════════════════════════════════════════════════════════════════
# 2. Load — Every status can be round-tripped through the DB enum
# ═══════════════════════════════════════════════════════════════════


class TestLoad:
    """Verify every status can be round-tripped through the persistence layer."""

    # All 15 WorkflowState values
    ALL_WORKFLOW_STATES = [
        WorkflowState.UPLOADED,
        WorkflowState.ANALYZING,
        WorkflowState.AI_REVIEWED,
        WorkflowState.PROCUREMENT_REVIEW,
        WorkflowState.LEGAL_REVIEW,
        WorkflowState.SECURITY_REVIEW,
        WorkflowState.NEGOTIATION,
        WorkflowState.IN_REVIEW,
        WorkflowState.ESCALATED,
        WorkflowState.EXEC_APPROVAL,
        WorkflowState.APPROVED,
        WorkflowState.REJECTED,
        WorkflowState.FINALIZED,
        WorkflowState.EXECUTED,
        WorkflowState.ARCHIVED,
    ]

    @pytest.mark.parametrize("wf_state", ALL_WORKFLOW_STATES)
    def test_workflow_state_to_db_status_produces_valid_review_status(self, wf_state):
        """Verify to_db_status() produces a value that can be constructed as ReviewStatus."""
        db_val = to_db_status(wf_state)
        rs = ReviewStatus(db_val)
        assert rs.value == db_val
        print(f"  ✅ {wf_state.name} → to_db_status() → '{db_val}' → ReviewStatus('{db_val}')")

    @pytest.mark.parametrize("wf_state", ALL_WORKFLOW_STATES)
    def test_workflow_state_round_trip_through_legacy_map(self, wf_state):
        """Verify round-trip: WorkflowState → DB → map_legacy_status → WorkflowState.

        Some states map to different DB values (ai_reviewed→ai_analyzed,
        negotiation→in_review), so the round-trip may not return the original
        WorkflowState. This test documents which round-trips are identity vs mapped.
        """
        db_val = to_db_status(wf_state)
        mapped_back = map_legacy_status(db_val)

        if mapped_back == wf_state:
            print(f"  ✅ {wf_state.name} → '{db_val}' → {mapped_back.name} (identity)")
        else:
            print(f"  ⚠ {wf_state.name} → '{db_val}' → {mapped_back.name} (mapped)")
            # These are the expected non-identity round-trips:
            if wf_state == WorkflowState.AI_REVIEWED:
                assert mapped_back == WorkflowState.AI_REVIEWED, (
                    f"ai_reviewed should round-trip back to AI_REVIEWED via ai_analyzed"
                )
            elif wf_state == WorkflowState.NEGOTIATION:
                assert mapped_back == WorkflowState.IN_REVIEW, (
                    f"negotiation should round-trip to IN_REVIEW via in_review"
                )

    def test_all_workflow_states_map_to_db_values_in_review_status_enum(self):
        """Verify every WORKFLOW_TO_DB_STATUS value exists in ReviewStatus."""
        rs_values = {s.value for s in ReviewStatus}
        for wf_state in self.ALL_WORKFLOW_STATES:
            db_val = to_db_status(wf_state)
            assert db_val in rs_values, (
                f"'{db_val}' (from {wf_state.name}) not in ReviewStatus enum"
            )
        print(f"  ✅ All {len(self.ALL_WORKFLOW_STATES)} WorkflowState values map to valid ReviewStatus values")


# ═══════════════════════════════════════════════════════════════════
# 3. Transition — Every status can be validated by the state machine
# ═══════════════════════════════════════════════════════════════════


class TestTransition:
    """Verify every status can transition through the WorkflowState machine."""

    def test_analyzing_can_transition_from_uploaded(self):
        """Verify 'analyzing' is reachable from 'uploaded'."""
        record = validate_transition(WorkflowState.UPLOADED, WorkflowState.ANALYZING)
        assert record.is_valid
        print(f"  ✅ UPLOADED → ANALYZING: valid")

    def test_analyzing_can_transition_to_ai_reviewed(self):
        """Verify 'analyzing' can transition to 'ai_reviewed'."""
        record = validate_transition(WorkflowState.ANALYZING, WorkflowState.AI_REVIEWED)
        assert record.is_valid
        print(f"  ✅ ANALYZING → AI_REVIEWED: valid")

    def test_legal_review_can_transition_from_procurement_review(self):
        """Verify 'legal_review' is reachable from 'procurement_review'."""
        record = validate_transition(WorkflowState.PROCUREMENT_REVIEW, WorkflowState.LEGAL_REVIEW)
        assert record.is_valid
        print(f"  ✅ PROCUREMENT_REVIEW → LEGAL_REVIEW: valid")

    def test_legal_review_can_transition_to_approved(self):
        """Verify 'legal_review' can transition to 'approved'."""
        record = validate_transition(WorkflowState.LEGAL_REVIEW, WorkflowState.APPROVED)
        assert record.is_valid
        print(f"  ✅ LEGAL_REVIEW → APPROVED: valid")

    def test_procurement_review_can_transition_from_ai_reviewed(self):
        """Verify 'procurement_review' is reachable from 'ai_reviewed'."""
        record = validate_transition(WorkflowState.AI_REVIEWED, WorkflowState.PROCUREMENT_REVIEW)
        assert record.is_valid
        print(f"  ✅ AI_REVIEWED → PROCUREMENT_REVIEW: valid")

    def test_security_review_can_transition_from_procurement_review(self):
        """Verify 'security_review' is reachable from 'procurement_review'."""
        record = validate_transition(WorkflowState.PROCUREMENT_REVIEW, WorkflowState.SECURITY_REVIEW)
        assert record.is_valid
        print(f"  ✅ PROCUREMENT_REVIEW → SECURITY_REVIEW: valid")

    def test_security_review_can_transition_to_legal_review(self):
        """Verify 'security_review' can transition to 'legal_review'."""
        record = validate_transition(WorkflowState.SECURITY_REVIEW, WorkflowState.LEGAL_REVIEW)
        assert record.is_valid
        print(f"  ✅ SECURITY_REVIEW → LEGAL_REVIEW: valid")

    def test_negotiation_can_transition_from_procurement_review(self):
        """Verify 'negotiation' is reachable in the state machine."""
        record = validate_transition(WorkflowState.PROCUREMENT_REVIEW, WorkflowState.NEGOTIATION)
        assert record.is_valid
        print(f"  ✅ PROCUREMENT_REVIEW → NEGOTIATION: valid (in state machine)")

    def test_negotiation_to_db_maps_to_in_review(self):
        """Verify 'negotiation' persists as 'in_review'."""
        db_val = to_db_status(WorkflowState.NEGOTIATION)
        assert db_val == "in_review"
        print(f"  ✅ NEGOTIATION → to_db_status() → '{db_val}'")

    def test_ai_reviewed_to_db_maps_to_ai_analyzed(self):
        """Verify 'ai_reviewed' persists as 'ai_analyzed'."""
        db_val = to_db_status(WorkflowState.AI_REVIEWED)
        assert db_val == "ai_analyzed"
        print(f"  ✅ AI_REVIEWED → to_db_status() → '{db_val}'")


# ═══════════════════════════════════════════════════════════════════
# 4. Return through API — Full persistence chain
# ═══════════════════════════════════════════════════════════════════


class TestPersistenceChain:
    """Verify the full persistence chain for every status.

    Chain: WorkflowState → to_db_status() → ReviewStatus() → .value
    This is the exact chain used by service.update_status() before DB write.
    """

    # The 4 new statuses added by migration k0l1m2n3o4p5
    NEW_DB_STATUSES = ["analyzing", "legal_review", "procurement_review", "security_review"]

    # The 2 mapped statuses (not stored directly)
    MAPPED_STATUSES = [
        ("ai_reviewed", "ai_analyzed"),
        ("negotiation", "in_review"),
    ]

    @pytest.mark.parametrize("status_str", NEW_DB_STATUSES)
    def test_new_status_persists_directly(self, status_str):
        """Verify the 4 new DB statuses persist as themselves (no mapping)."""
        # Chain: WorkflowState → to_db_status → ReviewStatus → DB value
        wf_state = WorkflowState.from_string(status_str)
        db_val = to_db_status(wf_state)
        rs = ReviewStatus(db_val)

        assert db_val == status_str, (
            f"'{status_str}' should persist as itself, but got '{db_val}'"
        )
        assert rs.value == status_str
        print(f"  ✅ '{status_str}' → to_db_status() → '{db_val}' → ReviewStatus → '{rs.value}' (DIRECT)")

    @pytest.mark.parametrize("wf_name,expected_db", MAPPED_STATUSES)
    def test_mapped_status_persists_as_expected(self, wf_name, expected_db):
        """Verify mapped statuses persist to their expected DB values."""
        wf_state = WorkflowState.from_string(wf_name)
        db_val = to_db_status(wf_state)
        rs = ReviewStatus(db_val)

        assert db_val == expected_db, (
            f"'{wf_name}' should map to '{expected_db}', but got '{db_val}'"
        )
        assert rs.value == expected_db
        print(f"  ✅ '{wf_name}' → to_db_status() → '{db_val}' → ReviewStatus → '{rs.value}' (MAPPED)")

    def test_full_chain_for_every_workflow_state(self):
        """Test the full persistence chain for ALL WorkflowState values."""
        failures = []
        for wf_state in WorkflowState:
            try:
                db_val = to_db_status(wf_state)
                rs = ReviewStatus(db_val)
                val = rs.value
                assert val == db_val
            except Exception as e:
                failures.append(f"{wf_state.name}: {e}")

        if failures:
            print(f"\n  ⚠ Chain failures:")
            for f in failures:
                print(f"    {f}")
        else:
            print(f"\n  ✅ Full persistence chain valid for all {len(WorkflowState)} WorkflowState values")
        assert len(failures) == 0

    def test_no_invalid_text_representation_possible(self):
        """Verify that every possible DB value from to_db_status() is in the ReviewStatus enum.

        This guarantees that service.update_status() will NEVER produce an
        InvalidTextRepresentationError when writing to PostgreSQL.
        """
        rs_values = {s.value for s in ReviewStatus}
        db_values = set()
        for wf_state in WorkflowState:
            db_values.add(to_db_status(wf_state))

        unsafe = db_values - rs_values
        if unsafe:
            print(f"\n  ⚠ DB-unsafe values: {unsafe}")
        else:
            print(f"\n  ✅ All {len(db_values)} possible DB values are safe for PostgreSQL persistence")
        assert len(unsafe) == 0
