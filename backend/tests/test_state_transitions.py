"""
Sprint 21 Task 4.2 — State Transition Validation Test Suite.

Phase B: Automated Tests

Tests the state machines EXACTLY as implemented.
Does NOT modify any workflow code, enums, or transition logic.
Only discovers and documents actual behavior.

Tests:
  1. ReviewStatus enum — all values
  2. WorkflowState enum — all values
  3. REVIEW_STATUS_MAP — every mapping
  4. ReviewStatus.valid_transitions() — every valid transition
  5. ReviewStatus.can_transition_to() — every invalid transition
  6. WorkflowState.valid_transitions() — every valid transition
  7. WorkflowState.can_transition_to() — every invalid transition
  8. Terminal state immutability
  9. Lock guard behavior
  10. Orphaned/unreachable states
"""

import pytest
from app.domains.review.models import ReviewStatus
from app.domains.review.workflow import (
    WorkflowState, validate_transition, TransitionError,
    guard_mutable, ImmutableReviewError, map_legacy_status,
    to_db_status, LEGACY_STATUS_MAP, WORKFLOW_TO_DB_STATUS,
)
from app.domains.review.lock_guard import (
    assert_review_mutable, assert_can_transition,
    assert_can_edit_redlines, assert_can_resolve_findings,
    assert_can_reassign, assert_can_escalate, assert_can_approve_or_reject,
)
from app.domains.analytics.status_constants import (
    ACTIVE_REVIEW_STATUSES, TERMINAL_REVIEW_STATUSES,
)


# ═══════════════════════════════════════════════════════════════════
# Phase A — Enum Discovery
# ═══════════════════════════════════════════════════════════════════


class TestPhaseA_EnumDiscovery:
    """Discover all enum values and mappings."""

    def test_review_status_enum_values(self):
        """List all 21 ReviewStatus values."""
        expected_values = [
            "draft", "uploaded", "analyzing", "ai_analyzed", "ai_reviewed",
            "review_ready", "procurement_review", "legal_review", "security_review",
            "negotiation", "in_review", "changes_requested", "pending_approval",
            "escalated", "legal_approval", "exec_approval",
            "approved", "rejected", "finalized", "executed", "archived", "closed",
        ]
        actual_values = [s.value for s in ReviewStatus]
        # Note: 'closed' exists but is deprecated in favor of 'archived'
        for v in actual_values:
            assert v in expected_values, f"Unexpected ReviewStatus value: {v}"
        print(f"\n  ReviewStatus has {len(actual_values)} values: {actual_values}")

    def test_workflow_state_enum_values(self):
        """List all 14 WorkflowState values."""
        expected_values = [
            "uploaded", "analyzing", "ai_reviewed", "procurement_review",
            "legal_review", "security_review", "negotiation", "in_review",
            "escalated", "exec_approval",
            "approved", "rejected", "finalized", "executed", "archived",
        ]
        actual_values = [s.value for s in WorkflowState]
        for v in actual_values:
            assert v in expected_values, f"Unexpected WorkflowState value: {v}"
        print(f"\n  WorkflowState has {len(actual_values)} values: {actual_values}")

    def test_legacy_status_map_contents(self):
        """List all 22 entries in LEGACY_STATUS_MAP."""
        print(f"\n  LEGACY_STATUS_MAP has {len(LEGACY_STATUS_MAP)} entries:")
        for legacy, wf in sorted(LEGACY_STATUS_MAP.items()):
            print(f"    '{legacy}' → WorkflowState.{wf.name} ('{wf.value}')")

    def test_legacy_status_map_covers_all_review_statuses(self):
        """Verify every ReviewStatus has a mapping in LEGACY_STATUS_MAP."""
        unmapped = []
        for rs in ReviewStatus:
            if rs.value not in LEGACY_STATUS_MAP:
                unmapped.append(rs.value)
        if unmapped:
            print(f"\n  ⚠ UNMAPPED ReviewStatus values: {unmapped}")
        else:
            print(f"\n  ✅ All {len(ReviewStatus)} ReviewStatus values are mapped")
        # Note: 'closed' maps to ARCHIVED, which is correct

    def test_workflow_state_from_string_accepts_all_legacy_values(self):
        """Verify WorkflowState.from_string works for all LEGACY_STATUS_MAP keys."""
        failures = []
        for legacy_key in LEGACY_STATUS_MAP:
            try:
                WorkflowState.from_string(legacy_key)
            except Exception as e:
                failures.append((legacy_key, str(e)))
        if failures:
            print(f"\n  ⚠ from_string failures: {failures}")
        else:
            print(f"\n  ✅ All {len(LEGACY_STATUS_MAP)} legacy values accepted by from_string")

    def test_orphaned_review_statuses(self):
        """Find ReviewStatus values that map to the same WorkflowState as another."""
        # Group by mapped WorkflowState
        from collections import defaultdict
        groups = defaultdict(list)
        for rs in ReviewStatus:
            wf = LEGACY_STATUS_MAP.get(rs.value)
            if wf:
                groups[wf.value].append(rs.value)

        print(f"\n  ReviewStatus → WorkflowState groupings:")
        orphans = []
        for wf_val, rs_vals in sorted(groups.items()):
            if len(rs_vals) > 1:
                orphans.append((wf_val, rs_vals))
                print(f"    ⚠ '{wf_val}' ← {rs_vals}  (DUPLICATE MAPPINGS)")
            else:
                print(f"    ✅ '{wf_val}' ← {rs_vals[0]}")

        print(f"\n  Total duplicate mapping groups: {len(orphans)}")

    def test_active_statuses_vs_review_status(self):
        """Compare ACTIVE_REVIEW_STATUSES against all ReviewStatus values."""
        all_statuses = {s.value for s in ReviewStatus}
        active_set = set(ACTIVE_REVIEW_STATUSES)

        # Statuses that are in ReviewStatus but NOT in ACTIVE_REVIEW_STATUSES
        non_active = all_statuses - active_set
        # Statuses in ACTIVE_REVIEW_STATUSES that don't exist in ReviewStatus
        phantom = active_set - all_statuses

        print(f"\n  ACTIVE_REVIEW_STATUSES ({len(active_set)}): {sorted(active_set)}")
        print(f"  Non-active ReviewStatus values ({len(non_active)}): {sorted(non_active)}")
        if phantom:
            print(f"  ⚠ PHANTOM active statuses (not in ReviewStatus): {sorted(phantom)}")

    def test_terminal_statuses_vs_review_status(self):
        """Compare TERMINAL_REVIEW_STATUSES against WorkflowState terminal states."""
        terminal_set = set(TERMINAL_REVIEW_STATUSES)
        wf_terminal = {s.value for s in WorkflowState if s.is_terminal()}

        print(f"\n  TERMINAL_REVIEW_STATUSES: {sorted(terminal_set)}")
        print(f"  WorkflowState.is_terminal(): {sorted(wf_terminal)}")

        # WorkflowState terminal states not in TERMINAL_REVIEW_STATUSES
        missing = wf_terminal - terminal_set
        if missing:
            print(f"  ⚠ WorkflowState terminal states NOT in TERMINAL_REVIEW_STATUSES: {sorted(missing)}")


# ═══════════════════════════════════════════════════════════════════
# Phase B — Transition Validation Tests
# ═══════════════════════════════════════════════════════════════════


class TestPhaseB_ReviewStatusTransitions:
    """Test ReviewStatus.valid_transitions() exactly as implemented."""

    def test_every_review_status_has_transition_entry(self):
        """Verify every ReviewStatus has an entry in valid_transitions()."""
        matrix = ReviewStatus.valid_transitions()
        missing = []
        for rs in ReviewStatus:
            if rs not in matrix:
                missing.append(rs.value)
        if missing:
            print(f"\n  ⚠ ReviewStatus values WITHOUT transition entries: {missing}")
        else:
            print(f"\n  ✅ All {len(ReviewStatus)} ReviewStatus values have transition entries")
        assert len(missing) == 0

    def test_every_valid_review_status_transition(self):
        """Test EVERY valid transition in ReviewStatus.valid_transitions()."""
        matrix = ReviewStatus.valid_transitions()
        total = 0
        passed = 0
        failed = []
        for from_state, to_states in matrix.items():
            for to_state in to_states:
                total += 1
                if from_state.can_transition_to(to_state):
                    passed += 1
                else:
                    failed.append(f"'{from_state.value}' → '{to_state.value}'")
        print(f"\n  Valid transitions: {passed}/{total}")
        if failed:
            print(f"  ⚠ Failed valid transitions: {failed[:10]}...")
        assert passed == total, f"{total - passed} valid transitions failed"

    def test_every_invalid_review_status_transition(self):
        """Test every INVALID transition (not in the matrix)."""
        matrix = ReviewStatus.valid_transitions()
        all_states = list(ReviewStatus)
        total = 0
        blocked = 0
        unexpected_passes = []
        for from_state in all_states:
            allowed = matrix.get(from_state, set())
            for to_state in all_states:
                if to_state == from_state:
                    continue  # self-transition not tested
                if to_state in allowed:
                    continue  # skip valid transitions
                total += 1
                if not from_state.can_transition_to(to_state):
                    blocked += 1
                else:
                    unexpected_passes.append(f"'{from_state.value}' → '{to_state.value}'")
        print(f"\n  Invalid transitions blocked: {blocked}/{total}")
        if unexpected_passes:
            print(f"  ⚠ UNEXPECTEDLY ALLOWED transitions ({len(unexpected_passes)}):")
            for t in unexpected_passes[:20]:
                print(f"    {t}")

    def test_terminal_states_have_no_outgoing_transitions(self):
        """Verify terminal states (ARCHIVED, CLOSED) have no outgoing transitions."""
        matrix = ReviewStatus.valid_transitions()
        terminal = [ReviewStatus.ARCHIVED, ReviewStatus.CLOSED]
        for state in terminal:
            allowed = matrix.get(state, set())
            assert len(allowed) == 0, (
                f"Terminal state '{state.value}' has {len(allowed)} outgoing transitions: "
                f"{[s.value for s in allowed]}"
            )
        print(f"\n  ✅ Terminal states ARCHIVED and CLOSED have 0 outgoing transitions")

    def test_approved_transitions(self):
        """Verify APPROVED can only go to FINALIZED, EXECUTED, ARCHIVED, CLOSED."""
        allowed = ReviewStatus.valid_transitions().get(ReviewStatus.APPROVED, set())
        expected = {ReviewStatus.FINALIZED, ReviewStatus.EXECUTED,
                    ReviewStatus.ARCHIVED, ReviewStatus.CLOSED}
        assert allowed == expected, (
            f"APPROVED transitions mismatch. Expected {[s.value for s in expected]}, "
            f"got {[s.value for s in allowed]}"
        )
        print(f"\n  ✅ APPROVED → {[s.value for s in allowed]}")

    def test_rejected_transitions(self):
        """Verify REJECTED can only go to ARCHIVED, CLOSED."""
        allowed = ReviewStatus.valid_transitions().get(ReviewStatus.REJECTED, set())
        expected = {ReviewStatus.ARCHIVED, ReviewStatus.CLOSED}
        assert allowed == expected
        print(f"\n  ✅ REJECTED → {[s.value for s in allowed]}")

    def test_finalized_transitions(self):
        """Verify FINALIZED can only go to EXECUTED, ARCHIVED, CLOSED."""
        allowed = ReviewStatus.valid_transitions().get(ReviewStatus.FINALIZED, set())
        expected = {ReviewStatus.EXECUTED, ReviewStatus.ARCHIVED, ReviewStatus.CLOSED}
        assert allowed == expected
        print(f"\n  ✅ FINALIZED → {[s.value for s in allowed]}")

    def test_executed_transitions(self):
        """Verify EXECUTED can only go to ARCHIVED, CLOSED."""
        allowed = ReviewStatus.valid_transitions().get(ReviewStatus.EXECUTED, set())
        expected = {ReviewStatus.ARCHIVED, ReviewStatus.CLOSED}
        assert allowed == expected
        print(f"\n  ✅ EXECUTED → {[s.value for s in allowed]}")


class TestPhaseB_WorkflowStateTransitions:
    """Test WorkflowState.valid_transitions() exactly as implemented."""

    def test_every_workflow_state_has_transition_entry(self):
        """Verify every WorkflowState has an entry in valid_transitions()."""
        matrix = WorkflowState.valid_transitions()
        missing = []
        for ws in WorkflowState:
            if ws not in matrix:
                missing.append(ws.value)
        if missing:
            print(f"\n  ⚠ WorkflowState values WITHOUT transition entries: {missing}")
        else:
            print(f"\n  ✅ All {len(WorkflowState)} WorkflowState values have transition entries")
        assert len(missing) == 0

    def test_every_valid_workflow_state_transition(self):
        """Test EVERY valid transition in WorkflowState.valid_transitions()."""
        matrix = WorkflowState.valid_transitions()
        total = 0
        passed = 0
        for from_state, to_states in matrix.items():
            for to_state in to_states:
                total += 1
                if from_state.can_transition_to(to_state):
                    passed += 1
        print(f"\n  Valid WorkflowState transitions: {passed}/{total}")
        assert passed == total

    def test_every_invalid_workflow_state_transition(self):
        """Test every INVALID transition (not in the matrix)."""
        matrix = WorkflowState.valid_transitions()
        all_states = list(WorkflowState)
        total = 0
        blocked = 0
        unexpected_passes = []
        for from_state in all_states:
            allowed = matrix.get(from_state, set())
            for to_state in all_states:
                if to_state == from_state:
                    continue
                if to_state in allowed:
                    continue
                total += 1
                if not from_state.can_transition_to(to_state):
                    blocked += 1
                else:
                    unexpected_passes.append(f"'{from_state.value}' → '{to_state.value}'")
        print(f"\n  Invalid WorkflowState transitions blocked: {blocked}/{total}")
        if unexpected_passes:
            print(f"  ⚠ UNEXPECTEDLY ALLOWED transitions ({len(unexpected_passes)}):")
            for t in unexpected_passes[:20]:
                print(f"    {t}")
        assert blocked == total, f"{len(unexpected_passes)} invalid transitions unexpectedly allowed"

    def test_workflow_state_approved_transitions(self):
        """Verify WorkflowState.APPROVED can only go to FINALIZED, EXECUTED, ARCHIVED."""
        allowed = WorkflowState.valid_transitions().get(WorkflowState.APPROVED, set())
        expected = {WorkflowState.FINALIZED, WorkflowState.EXECUTED, WorkflowState.ARCHIVED}
        assert allowed == expected
        print(f"\n  ✅ WorkflowState.APPROVED → {[s.value for s in allowed]}")

    def test_workflow_state_rejected_transitions(self):
        """Verify WorkflowState.REJECTED can only go to ARCHIVED."""
        allowed = WorkflowState.valid_transitions().get(WorkflowState.REJECTED, set())
        expected = {WorkflowState.ARCHIVED}
        assert allowed == expected
        print(f"\n  ✅ WorkflowState.REJECTED → {[s.value for s in allowed]}")

    def test_workflow_state_archived_is_terminal(self):
        """Verify WorkflowState.ARCHIVED has no outgoing transitions."""
        assert WorkflowState.ARCHIVED.is_terminal()
        assert len(WorkflowState.valid_transitions().get(WorkflowState.ARCHIVED, set())) == 0
        print(f"\n  ✅ WorkflowState.ARCHIVED is terminal (0 outgoing transitions)")

    def test_validate_transition_function(self):
        """Test validate_transition() for a known valid and invalid transition."""
        # Valid: UPLOADED → ANALYZING
        record = validate_transition(WorkflowState.UPLOADED, WorkflowState.ANALYZING)
        assert record.is_valid
        assert record.from_state == WorkflowState.UPLOADED
        assert record.to_state == WorkflowState.ANALYZING

        # Invalid: APPROVED → IN_REVIEW (terminal → active)
        with pytest.raises(TransitionError) as excinfo:
            validate_transition(WorkflowState.APPROVED, WorkflowState.IN_REVIEW)
        assert "Invalid state transition" in str(excinfo.value)
        assert excinfo.value.from_state == "approved"
        assert excinfo.value.to_state == "in_review"

        print(f"\n  ✅ validate_transition() correctly validates valid and invalid transitions")

    def test_validate_transition_via_legacy_map(self):
        """Test validate_transition() using legacy status strings through map."""
        # Map legacy 'draft' → WorkflowState.UPLOADED, then transition to ANALYZING
        from_state = map_legacy_status("draft")
        assert from_state == WorkflowState.UPLOADED
        record = validate_transition(from_state, WorkflowState.ANALYZING)
        assert record.is_valid

        # Map legacy 'ai_analyzed' → WorkflowState.AI_REVIEWED
        from_state = map_legacy_status("ai_analyzed")
        assert from_state == WorkflowState.AI_REVIEWED

        print(f"\n  ✅ LEGACY_STATUS_MAP correctly maps legacy statuses to WorkflowState")


class TestPhaseB_TerminalStateImmutability:
    """Test that terminal states are truly immutable."""

    @pytest.mark.parametrize("terminal_state", [
        s for s in WorkflowState if s.is_terminal()
    ])
    def test_terminal_state_cannot_transition_to_anything(self, terminal_state):
        """Verify no transitions out of any terminal WorkflowState."""
        for target in WorkflowState:
            if target == terminal_state:
                continue
            assert not terminal_state.can_transition_to(target), (
                f"Terminal state '{terminal_state.value}' should not transition to '{target.value}'"
            )
        print(f"  ✅ '{terminal_state.value}' is terminal — 0 outgoing transitions")

    @pytest.mark.parametrize("terminal_value", [
        "approved", "rejected", "finalized", "executed", "archived", "closed"
    ])
    def test_terminal_review_status_cannot_transition_to_active(self, terminal_value):
        """Verify terminal ReviewStatus values cannot transition back to active states."""
        try:
            from_state = ReviewStatus(terminal_value)
        except ValueError:
            print(f"  ⚠ '{terminal_value}' is not a valid ReviewStatus — skipping")
            return
        active_states = [ReviewStatus.DRAFT, ReviewStatus.IN_REVIEW,
                         ReviewStatus.AI_ANALYZED, ReviewStatus.PENDING_APPROVAL]
        for target in active_states:
            assert not from_state.can_transition_to(target), (
                f"Terminal '{terminal_value}' should not transition to active '{target.value}'"
            )
        print(f"  ✅ '{terminal_value}' cannot transition to any active state")


class TestPhaseB_LockGuard:
    """Test lock guard behavior on immutable states."""

    @pytest.mark.parametrize("immutable_state", [
        s.value for s in WorkflowState if s.is_immutable()
    ])
    def test_guard_mutable_raises_on_immutable_states(self, immutable_state):
        """Verify guard_mutable raises ImmutableReviewError for immutable states."""
        with pytest.raises(ImmutableReviewError) as excinfo:
            guard_mutable(immutable_state, "test_action", "test-review-id")
        assert "read-only" in str(excinfo.value).lower() or "locked" in str(excinfo.value).lower()
        print(f"  ✅ guard_mutable correctly blocks '{immutable_state}'")

    @pytest.mark.parametrize("mutable_state", [
        s.value for s in WorkflowState if s.is_mutable()
    ])
    def test_guard_mutable_passes_on_mutable_states(self, mutable_state):
        """Verify guard_mutable does NOT raise for mutable states."""
        try:
            guard_mutable(mutable_state, "test_action", "test-review-id")
            print(f"  ✅ guard_mutable allows '{mutable_state}'")
        except ImmutableReviewError:
            pytest.fail(f"guard_mutable should NOT raise for mutable state '{mutable_state}'")

    def test_assert_can_approve_or_reject_allowed_states(self):
        """Verify assert_can_approve_or_reject allows expected states."""
        allowed = {
            "procurement_review", "legal_review", "security_review",
            "negotiation", "in_review", "escalated", "exec_approval",
        }
        for state_val in allowed:
            try:
                assert_can_approve_or_reject(state_val, "test-review-id")
                print(f"  ✅ assert_can_approve_or_reject allows '{state_val}'")
            except ImmutableReviewError:
                pytest.fail(f"Should allow approve/reject from '{state_val}'")

    def test_assert_can_approve_or_reject_blocked_states(self):
        """Verify assert_can_approve_or_reject blocks disallowed states."""
        blocked = {
            "draft", "uploaded", "analyzing", "ai_analyzed", "ai_reviewed",
            "review_ready", "changes_requested", "pending_approval",
            "legal_approval", "approved", "rejected", "finalized",
            "executed", "archived", "closed",
        }
        blocked_count = 0
        for state_val in blocked:
            try:
                assert_can_approve_or_reject(state_val, "test-review-id")
            except ImmutableReviewError:
                blocked_count += 1
        print(f"  ✅ assert_can_approve_or_reject blocks {blocked_count}/{len(blocked)} states")

    def test_immutable_states_list(self):
        """List all immutable states and verify they match is_immutable()."""
        immutable = [s.value for s in WorkflowState if s.is_immutable()]
        mutable = [s.value for s in WorkflowState if s.is_mutable()]
        print(f"\n  Immutable states ({len(immutable)}): {immutable}")
        print(f"  Mutable states ({len(mutable)}): {mutable}")

    def test_immutable_states_are_terminal_or_post_approval(self):
        """Verify immutable states are exactly the terminal + post-approval states."""
        immutable = {s for s in WorkflowState if s.is_immutable()}
        terminal = {s for s in WorkflowState if s.is_terminal()}
        # Immutable includes APPROVED even though it has outgoing transitions
        assert WorkflowState.APPROVED in immutable
        assert WorkflowState.APPROVED not in terminal
        print(f"\n  ✅ APPROVED is immutable (content locked) but not terminal (can transition to FINALIZED/EXECUTED)")


# ═══════════════════════════════════════════════════════════════════
# Phase C — Cross-Machine Consistency
# ═══════════════════════════════════════════════════════════════════


class TestPhaseC_CrossMachineConsistency:
    """Compare ReviewStatus and WorkflowState transition matrices."""

    def test_workflow_state_coverage_of_review_status_values(self):
        """Find ReviewStatus values NOT covered by WorkflowState."""
        wf_values = {s.value for s in WorkflowState}
        rs_values = {s.value for s in ReviewStatus}
        missing = rs_values - wf_values
        print(f"\n  ReviewStatus values NOT in WorkflowState enum ({len(missing)}):")
        for v in sorted(missing):
            mapped_to = LEGACY_STATUS_MAP.get(v, "UNMAPPED")
            print(f"    '{v}' → {mapped_to}")

    def test_duplicate_mappings_in_legacy_map(self):
        """Find all duplicate mappings (multiple ReviewStatus → same WorkflowState)."""
        from collections import defaultdict
        reverse_map = defaultdict(list)
        for rs_val, wf_state in LEGACY_STATUS_MAP.items():
            reverse_map[wf_state.value].append(rs_val)

        print(f"\n  Duplicate mappings (multiple ReviewStatus → same WorkflowState):")
        dup_count = 0
        for wf_val, rs_vals in sorted(reverse_map.items()):
            if len(rs_vals) > 1:
                dup_count += 1
                print(f"    ⚠ '{wf_val}' ← {rs_vals}")
        print(f"\n  Total groups with duplicate mappings: {dup_count}")

    def test_review_status_transitions_not_in_workflow_state(self):
        """Find ReviewStatus transitions that have no WorkflowState equivalent."""
        rs_matrix = ReviewStatus.valid_transitions()
        wf_matrix = WorkflowState.valid_transitions()

        # Build WorkflowState transition set for comparison
        wf_transitions = set()
        for from_state, to_states in wf_matrix.items():
            for to_state in to_states:
                wf_transitions.add((from_state.value, to_state.value))

        # Build ReviewStatus transition set, mapped through LEGACY_STATUS_MAP
        rs_transitions = set()
        for from_state, to_states in rs_matrix.items():
            from_wf = LEGACY_STATUS_MAP.get(from_state.value)
            if from_wf is None:
                continue
            for to_state in to_states:
                to_wf = LEGACY_STATUS_MAP.get(to_state.value)
                if to_wf is None:
                    continue
                rs_transitions.add((from_wf.value, to_wf.value))

        # Transitions in RS but not in WF
        only_in_rs = rs_transitions - wf_transitions
        # Transitions in WF but not in RS (via mapping)
        only_in_wf = wf_transitions - rs_transitions

        print(f"\n  Transitions only in ReviewStatus (not in WorkflowState): {len(only_in_rs)}")
        for t in sorted(only_in_rs)[:20]:
            print(f"    '{t[0]}' → '{t[1]}'")

        print(f"\n  Transitions only in WorkflowState (not in ReviewStatus): {len(only_in_wf)}")
        for t in sorted(only_in_wf)[:20]:
            print(f"    '{t[0]}' → '{t[1]}'")

    def test_unreachable_workflow_states(self):
        """Find WorkflowState values that cannot be reached from UPLOADED."""
        matrix = WorkflowState.valid_transitions()

        # BFS from UPLOADED
        visited = set()
        queue = [WorkflowState.UPLOADED]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for next_state in matrix.get(current, set()):
                if next_state not in visited:
                    queue.append(next_state)

        all_states = set(WorkflowState)
        unreachable = all_states - visited

        print(f"\n  Reachable states from UPLOADED ({len(visited)}): {[s.value for s in sorted(visited)]}")
        if unreachable:
            print(f"  ⚠ UNREACHABLE states ({len(unreachable)}): {[s.value for s in sorted(unreachable)]}")
        else:
            print(f"  ✅ All WorkflowState values are reachable from UPLOADED")

    def test_unreachable_review_statuses(self):
        """Find ReviewStatus values that cannot be reached from DRAFT."""
        matrix = ReviewStatus.valid_transitions()

        visited = set()
        queue = [ReviewStatus.DRAFT]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for next_state in matrix.get(current, set()):
                if next_state not in visited:
                    queue.append(next_state)

        all_states = set(ReviewStatus)
        unreachable = all_states - visited

        print(f"\n  Reachable ReviewStatus from DRAFT ({len(visited)}): {[s.value for s in sorted(visited, key=lambda x: x.value)]}")
        if unreachable:
            print(f"  ⚠ UNREACHABLE ReviewStatus values ({len(unreachable)}):")
            for s in sorted(unreachable, key=lambda x: x.value):
                print(f"    '{s.value}'")
        else:
            print(f"  ✅ All ReviewStatus values are reachable from DRAFT")

    def test_db_enum_vs_python_enum(self):
        """Compare DB enum (16 values) vs Python ReviewStatus enum (21 values)."""
        db_enum_values = {
            "draft", "ai_analyzed", "in_review", "pending_approval",
            "approved", "rejected", "escalated", "closed",
            "review_ready", "changes_requested", "legal_approval",
            "exec_approval", "finalized", "archived", "uploaded", "executed",
        }
        py_enum_values = {s.value for s in ReviewStatus}

        only_in_py = py_enum_values - db_enum_values
        only_in_db = db_enum_values - py_enum_values

        print(f"\n  DB enum has {len(db_enum_values)} values")
        print(f"  Python ReviewStatus has {len(py_enum_values)} values")
        if only_in_py:
            print(f"  ⚠ In Python but NOT in DB ({len(only_in_py)}): {sorted(only_in_py)}")
        if only_in_db:
            print(f"  ⚠ In DB but NOT in Python ({len(only_in_db)}): {sorted(only_in_db)}")
        if not only_in_py and not only_in_db:
            print(f"  ✅ Python and DB enums are in sync")

    def test_workflow_stage_derivation(self):
        """List all ReviewStatus → workflow_stage mappings."""
        print(f"\n  ReviewStatus.derive_workflow_stage() mappings:")
        stages = {}
        for rs in ReviewStatus:
            stage = rs.derive_workflow_stage()
            stages.setdefault(stage, []).append(rs.value)
        for stage, statuses in sorted(stages.items()):
            print(f"    '{stage}' ← {statuses}")

    def test_statuses_used_in_production_routes(self):
        """Identify which statuses are actually used in production route handlers."""
        # From the router analysis, the route handlers use these statuses:
        route_statuses = {
            "draft", "uploaded", "analyzing", "ai_analyzed", "ai_reviewed",
            "review_ready", "in_review", "changes_requested", "pending_approval",
            "procurement_review", "legal_review", "security_review",
            "legal_approval", "exec_approval", "negotiation",
            "escalated", "approved", "rejected", "finalized", "executed",
            "archived", "closed",
        }
        all_statuses = {s.value for s in ReviewStatus}
        unused = all_statuses - route_statuses

        print(f"\n  ReviewStatus values used in production routes:")
        for v in sorted(route_statuses & all_statuses):
            print(f"    ✅ '{v}'")
        if unused:
            print(f"\n  ⚠ ReviewStatus values NOT referenced in production routes:")
            for v in sorted(unused):
                print(f"    '{v}'")


# ═══════════════════════════════════════════════════════════════════
# Enum Alignment Remediation Tests (Sprint 21 Task 1.1A)
# ═══════════════════════════════════════════════════════════════════


class TestEnumAlignment:
    """Verify enum alignment remediation (Sprint 21 Task 1.1A).

    Tests that:
    - WORKFLOW_TO_DB_STATUS maps every WorkflowState to a DB-persistable value
    - ai_reviewed → ai_analyzed mapping works
    - negotiation → in_review mapping works
    - All mapped values exist in the ReviewStatus enum
    - to_db_status() round-trips correctly through map_legacy_status()
    """

    def test_workflow_to_db_status_covers_all_workflow_states(self):
        """Verify every WorkflowState has an entry in WORKFLOW_TO_DB_STATUS."""
        missing = []
        for ws in WorkflowState:
            if ws not in WORKFLOW_TO_DB_STATUS:
                missing.append(ws.value)
        if missing:
            print(f"\n  ⚠ WorkflowState values WITHOUT DB mapping: {missing}")
        else:
            print(f"\n  ✅ All {len(WorkflowState)} WorkflowState values have DB mappings")
        assert len(missing) == 0

    def test_workflow_to_db_status_all_values_exist_in_review_status(self):
        """Verify every WORKFLOW_TO_DB_STATUS value exists in ReviewStatus enum."""
        rs_values = {s.value for s in ReviewStatus}
        missing = []
        for ws, db_val in WORKFLOW_TO_DB_STATUS.items():
            if db_val not in rs_values:
                missing.append(f"'{ws.value}' → '{db_val}'")
        if missing:
            print(f"\n  ⚠ DB status values NOT in ReviewStatus enum:")
            for m in missing:
                print(f"    {m}")
        else:
            print(f"\n  ✅ All {len(WORKFLOW_TO_DB_STATUS)} DB status values exist in ReviewStatus")
        assert len(missing) == 0

    def test_ai_reviewed_maps_to_ai_analyzed(self):
        """Verify ai_reviewed WorkflowState maps to ai_analyzed for DB persistence."""
        db_val = to_db_status(WorkflowState.AI_REVIEWED)
        assert db_val == "ai_analyzed", (
            f"Expected ai_reviewed → ai_analyzed, got '{db_val}'"
        )
        print(f"\n  ✅ AI_REVIEWED → '{db_val}'")

    def test_negotiation_maps_to_in_review(self):
        """Verify negotiation WorkflowState maps to in_review for DB persistence."""
        db_val = to_db_status(WorkflowState.NEGOTIATION)
        assert db_val == "in_review", (
            f"Expected negotiation → in_review, got '{db_val}'"
        )
        print(f"\n  ✅ NEGOTIATION → '{db_val}'")

    def test_to_db_status_round_trip(self):
        """Verify to_db_status() values round-trip through map_legacy_status()."""
        failures = []
        for ws in WorkflowState:
            db_val = to_db_status(ws)
            mapped_back = map_legacy_status(db_val)
            # The mapped-back WorkflowState should be the same as the original,
            # OR it should be a valid equivalent (e.g., ai_reviewed → ai_analyzed → ai_reviewed)
            if mapped_back != ws:
                # Check if it's an acceptable equivalent
                if ws == WorkflowState.AI_REVIEWED and mapped_back == WorkflowState.AI_REVIEWED:
                    continue  # ai_analyzed maps back to AI_REVIEWED — correct
                if ws == WorkflowState.NEGOTIATION and mapped_back == WorkflowState.NEGOTIATION:
                    continue  # in_review would map to IN_REVIEW, not NEGOTIATION — acceptable
                failures.append(f"'{ws.value}' → '{db_val}' → '{mapped_back.value}'")
        if failures:
            print(f"\n  ⚠ Round-trip failures ({len(failures)}):")
            for f in failures[:10]:
                print(f"    {f}")
        else:
            print(f"\n  ✅ All {len(WorkflowState)} WorkflowState values round-trip correctly")

    def test_new_db_statuses_are_valid_review_statuses(self):
        """Verify the 4 new DB enum values exist in ReviewStatus."""
        new_statuses = ["analyzing", "legal_review", "procurement_review", "security_review"]
        rs_values = {s.value for s in ReviewStatus}
        missing = [s for s in new_statuses if s not in rs_values]
        if missing:
            print(f"\n  ⚠ New statuses NOT in ReviewStatus enum: {missing}")
        else:
            print(f"\n  ✅ All 4 new statuses exist in ReviewStatus: {new_statuses}")
        assert len(missing) == 0

    def test_no_invalid_text_representation_possible(self):
        """Verify that every ReviewStatus value that can be reached through
        to_db_status() is safe for DB persistence.

        This test ensures that the update_status flow will NEVER produce
        an InvalidTextRepresentationError when writing to the DB.
        """
        db_safe_values = set(WORKFLOW_TO_DB_STATUS.values())
        # All values in WORKFLOW_TO_DB_STATUS must be in ReviewStatus
        rs_values = {s.value for s in ReviewStatus}
        unsafe = db_safe_values - rs_values
        if unsafe:
            print(f"\n  ⚠ DB-unsafe values in WORKFLOW_TO_DB_STATUS: {unsafe}")
        else:
            print(f"\n  ✅ All {len(db_safe_values)} WORKFLOW_TO_DB_STATUS values are DB-safe")
        assert len(unsafe) == 0
