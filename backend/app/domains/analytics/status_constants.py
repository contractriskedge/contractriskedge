"""
Shared review status constants for analytics services.

Single source of truth for what constitutes active vs terminal reviews.
All analytics services MUST import from here instead of hardcoding status lists.

── Database Enum ───────────────────────────────────────────────────
PostgreSQL enum review_status contains exactly 16 values (verified live):

    draft              Active     — Initial creation, awaiting AI analysis
    uploaded           Other      — File uploaded, pre-processing
    ai_analyzed        Active     — AI analysis complete, awaiting reviewer
    in_review          Active     — Assigned to reviewer, actively being reviewed
    pending_approval   Active     — Review complete, awaiting approval decision
    approved           Terminal   — Review approved
    rejected           Terminal   — Review rejected
    escalated          Other      — Review escalated (still in progress elsewhere)
    closed             Terminal   — Review closed
    review_ready       Other      — AI review ready for human reviewer
    changes_requested  Other      — Changes requested by reviewer
    legal_approval     Other      — Pending legal team approval
    exec_approval      Other      — Pending executive approval
    finalized          Other      — Contract finalized after approval
    archived           Other      — Review archived
    executed           Other      — Contract executed/signed

── Active Statuses ─────────────────────────────────────────────────
Reviews in progress, not yet at a terminal decision.
These are the statuses that count toward "active reviews", "backlog",
"queue depth", and "reviewer load" across all analytics endpoints.

    draft, ai_analyzed, in_review, pending_approval

── Terminal Statuses ───────────────────────────────────────────────
Reviews that have reached a final decision state.
Used for throughput calculation via review_status_history.

    approved, rejected

── Non-Active, Non-Terminal Statuses ───────────────────────────────
These statuses represent reviews that are NOT actively being worked
by a reviewer but are NOT yet at a terminal decision either.
They are excluded from both active counts and throughput calculations.

    uploaded, review_ready, changes_requested, escalated,
    legal_approval, exec_approval, finalized, archived, executed

── Why negotiation Is NOT in ACTIVE_REVIEW_STATUSES ─────────────────
The Python ReviewStatus enum defines NEGOTIATION = "negotiation", but
this value was NEVER added to the PostgreSQL review_status enum.
Attempting to use it in a query causes InvalidTextRepresentationError.
Negotiation is tracked via the separate negotiation_sessions table
(which has its own stage column: drafting, review, approved, executed).
"""

from __future__ import annotations

from typing import Final

# ── Active Review Statuses ─────────────────────────────────────────
# Reviews in progress, not yet at a terminal decision.
# These are the ONLY statuses that count as "active" across all services.

ACTIVE_REVIEW_STATUSES: Final[list[str]] = [
    "draft",
    "ai_analyzed",
    "in_review",
    "pending_approval",
]

# ── Terminal Review Statuses ───────────────────────────────────────
# Reviews that have reached a final decision state.
# Used for throughput calculation (reviews reaching terminal state).

TERMINAL_REVIEW_STATUSES: Final[list[str]] = [
    "approved",
    "rejected",
]

# ── SQL Helper Snippets ────────────────────────────────────────────
# Ready-to-use SQL fragments for consistent filtering.

ACTIVE_STATUSES_SQL: Final[str] = "status = ANY(:active_statuses)"

TERMINAL_STATUSES_SQL: Final[str] = "to_status IN ('approved', 'rejected')"
