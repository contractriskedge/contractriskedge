"""Workflow Recovery Daemon — periodic tasks for detecting and recovering stuck workflows.

This module provides Celery tasks that:
1. Detect uploads stuck in non-terminal states for >30 minutes
2. Detect AI runs stuck in processing/pending for >30 minutes
3. Detect reviews abandoned in draft/ai_analyzed with proper aging thresholds
4. Enforce recovery cooldown windows to prevent re-flagging
5. Enforce maximum escalation counts per entity
6. Record all recovery actions in an audit trail
7. Clean up expired idempotency records

Run via Celery Beat:
    celery -A app.workers.celery_scheduler beat --loglevel=info

Or triggered manually:
    from app.workers.recovery import recover_stuck_workflows
    recover_stuck_workflows.delay()
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from sqlalchemy import text as sa_text

from app.kernel.datetime_utils import age_minutes, utc_now

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Recovery Thresholds
# ═══════════════════════════════════════════════════════════════════
#
# These thresholds define when a workflow is considered "stuck" or
# "abandoned". Each threshold is intentionally conservative to avoid
# false positives and alert fatigue.
#
# IMPORTANT: Thresholds are state-aware. A review in "draft" gets
# more time than one in "ai_analyzed" because draft reviews may be
# legitimately paused during initial triage.
#
# IMPORTANT: Cooldown windows prevent the same entity from being
# re-recovered within the cooldown period, eliminating the 20-actions-
# every-5-minutes problem observed in the initial implementation.
# ═══════════════════════════════════════════════════════════════════

# ── Upload Recovery Thresholds ────────────────────────────────────

STUCK_UPLOAD_MINUTES = 10                # Uploads in non-terminal state for >10 min
STUCK_INGESTION_REDISPATCH_MINUTES = 3   # Re-queue pipeline tasks sooner for OCR/extraction stalls

# ── AI Run Recovery Thresholds ────────────────────────────────────

STUCK_AI_RUN_MINUTES = 30                # AI runs in processing for >30 min

# ── Abandoned Review Thresholds (State-Aware) ─────────────────────
#
# Different states have different abandonment thresholds because
# they represent different stages of the review lifecycle.
#
#   draft:       72h — Reviews in draft may be legitimately paused
#                      during initial triage or data gathering.
#   ai_analyzed: 48h — AI analysis is complete but no reviewer has
#                      been assigned. After 48h, flag for attention.
#   assigned:    24h — A reviewer is assigned but has taken no action
#                      for 24 hours. Flag as stalled.
#   pending_approval: SLA-based — Uses the review's SLA deadline if set,
#                      otherwise falls back to 48h.
# ═══════════════════════════════════════════════════════════════════

ABANDONED_DRAFT_HOURS = 72               # Reviews in draft for >72 hours
ABANDONED_AI_ANALYZED_HOURS = 48         # Reviews in ai_analyzed unassigned for >48 hours
ABANDONED_ASSIGNED_HOURS = 24            # Reviews assigned but no activity for >24 hours
ABANDONED_PENDING_APPROVAL_HOURS = 48    # Reviews in pending approval for >48 hours

# ── Cooldown Windows ──────────────────────────────────────────────
#
# After a recovery action is taken on an entity, no further recovery
# actions will be taken on that same entity within the cooldown window.
# This prevents the "20 actions every 5 minutes" problem.
#
# Cooldowns are per (entity_type, entity_id) pair.
# ═══════════════════════════════════════════════════════════════════

RECOVERY_COOLDOWN_MINUTES = 120          # 2 hours — don't re-recover the same entity
ESCALATION_COOLDOWN_MINUTES = 60         # 1 hour — don't re-escalate the same review

# ── Escalation Governance ─────────────────────────────────────────
#
# Maximum number of times a single entity can be recovered before
# it requires human intervention. Prevents infinite recovery loops.
# ═══════════════════════════════════════════════════════════════════

MAX_RECOVERY_ATTEMPTS = 3                # Max automated recovery attempts per entity
MAX_ESCALATION_COUNT = 5                 # Max escalations before requiring human intervention

# ── Recovery Priority Weighting ────────────────────────────────────
#
# Recovery actions are weighted by multiple signals to determine
# operational priority. Higher weight = more urgent recovery.
#
# These weights are used to compute a composite priority score
# that determines which reviews get recovered first and how
# aggressively they are escalated.
# ═══════════════════════════════════════════════════════════════════

# Risk severity weights
RISK_WEIGHT_CRITICAL = 100
RISK_WEIGHT_HIGH = 60
RISK_WEIGHT_MEDIUM = 30
RISK_WEIGHT_LOW = 10

# SLA deadline weights (hours remaining → weight)
# Closer to deadline = higher weight
SLA_WEIGHT_OVERDUE = 80
SLA_WEIGHT_WITHIN_4H = 60
SLA_WEIGHT_WITHIN_24H = 40
SLA_WEIGHT_WITHIN_72H = 20

# Contract value tier weights
VALUE_WEIGHT_ENTERPRISE = 80
VALUE_WEIGHT_MID_MARKET = 40
VALUE_WEIGHT_SMB = 10

# Escalation history weight (per previous escalation)
ESCALATION_HISTORY_WEIGHT_PER_COUNT = 15

# Priority thresholds for recovery action tier
PRIORITY_THRESHOLD_CRITICAL = 150   # Immediate notification + assignment
PRIORITY_THRESHOLD_HIGH = 80        # Priority bump + routing rules
PRIORITY_THRESHOLD_NORMAL = 30      # Standard flagging only

# ── Ownership Resolution ──────────────────────────────────────────
#
# When a review is flagged as abandoned, the recovery system can
# attempt to resolve ownership by:
#
# 1. Checking if the assigned reviewer is available (not OOO, not overloaded)
# 2. Applying routing rules to find the best available reviewer
# 3. Escalating through team chains if no reviewer is available
# 4. Auto-assigning to a fallback reviewer pool
# ═══════════════════════════════════════════════════════════════════

# Maximum active reviews per reviewer before they're considered overloaded
MAX_REVIEWS_PER_REVIEWER = 10

# Fallback assignment roles (tried in order)
FALLBACK_ASSIGNMENT_CHAIN = [
    "reviewer",
    "legal_ops",
    "compliance",
    "executive",
]

# ── Idempotency Cleanup ───────────────────────────────────────────

IDEMPOTENCY_CLEANUP_HOURS = 72           # Clean up idempotency keys older than 72h


# ═══════════════════════════════════════════════════════════════════
# Recovery Task
# ═══════════════════════════════════════════════════════════════════

@shared_task(
    name="recover_stuck_workflows",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    acks_late=True,
)
def recover_stuck_workflows():
    """Main recovery task — detects and handles stuck workflows across the system.

    Operates on ALL tenants. Each query is tenant-scoped to ensure
    cross-tenant isolation. Recovery actions respect tenant boundaries.

    Governance features:
    - Cooldown enforcement: Same entity not re-recovered within cooldown window
    - Escalation limits: Max automated recovery attempts per entity
    - Audit trail: Every recovery action recorded in recovery_actions table
    - State-aware thresholds: Different thresholds per review state

    This task should be scheduled via Celery Beat every 5 minutes.
    """
    from app.kernel.database.sync_session import get_sync_factory

    logger.info("[Recovery] Starting workflow recovery scan...")
    factory = get_sync_factory()
    session = factory.create_session(tenant_id="system", user_id="system", user_role="admin")
    recovery_actions = []
    tenant_count = 0

    try:
        # Get all active tenants
        tenants_sql = sa_text("SELECT tenant_id FROM tenants WHERE is_active = TRUE")
        tenants = session.execute(tenants_sql).fetchall()

        for (tenant_id,) in tenants:
            tenant_count += 1
            tenant_id_str = str(tenant_id)

            # 1. Recover stuck uploads (tenant-scoped)
            stuck_uploads = _find_stuck_uploads(session, tenant_id_str)
            for upload in stuck_uploads:
                action = _handle_stuck_upload(session, upload, tenant_id_str)
                if action:
                    recovery_actions.append(f"[{tenant_id_str[:8]}] {action}")

            # 2. Recover stuck AI runs (tenant-scoped)
            stuck_ai_runs = _find_stuck_ai_runs(session, tenant_id_str)
            for run in stuck_ai_runs:
                action = _handle_stuck_ai_run(session, run, tenant_id_str)
                if action:
                    recovery_actions.append(f"[{tenant_id_str[:8]}] {action}")

            # 3. Flag abandoned reviews (tenant-scoped) — state-aware thresholds
            abandoned_reviews = _find_abandoned_reviews(session, tenant_id_str)
            for review in abandoned_reviews:
                action = _flag_abandoned_review(session, review, tenant_id_str)
                if action:
                    recovery_actions.append(f"[{tenant_id_str[:8]}] {action}")

        # 4. Clean up expired idempotency records (global — no tenant context)
        cleanup_count = _cleanup_idempotency_records(session)
        if cleanup_count:
            recovery_actions.append(f"Cleaned up {cleanup_count} expired idempotency records")

        session.commit()

        if recovery_actions:
            logger.info(
                "[Recovery] Completed: %d actions across %d tenants",
                len(recovery_actions), tenant_count,
                extra={"actions": recovery_actions, "tenant_count": tenant_count},
            )
        else:
            logger.info("[Recovery] No stuck workflows detected across %d tenants.", tenant_count)

    except Exception as exc:
        session.rollback()
        logger.error("[Recovery] Recovery scan failed: %s", exc)
        raise
    finally:
        session.close()

    return {"actions_taken": len(recovery_actions), "actions": recovery_actions, "tenants_scanned": tenant_count}


# ═══════════════════════════════════════════════════════════════════
# Detection Functions
# ═══════════════════════════════════════════════════════════════════

def _find_stuck_uploads(session, tenant_id: str):
    """Find uploads stuck in non-terminal states beyond threshold (tenant-scoped)."""
    sql = sa_text("""
        SELECT upload_id, tenant_id, user_id, ingestion_state, retry_count,
               ingestion_error, updated_at
        FROM upload_sessions
        WHERE tenant_id = :tenant_id
          AND ingestion_state NOT IN ('review_ready', 'failed', 'cancelled', 'quarantined')
          AND updated_at < NOW() - INTERVAL :threshold
        ORDER BY updated_at ASC
        LIMIT 20
    """)
    result = session.execute(sql, {
        "tenant_id": tenant_id,
        "threshold": f"{STUCK_UPLOAD_MINUTES} minutes",
    })
    return result.fetchall()


def _find_stuck_ai_runs(session, tenant_id: str):
    """Find AI runs stuck in processing/pending beyond threshold (tenant-scoped)."""
    sql = sa_text("""
        SELECT run_id, upload_id, tenant_id, status, retry_count,
               error_message, started_at, created_at
        FROM ai_execution_runs
        WHERE tenant_id = :tenant_id
          AND status IN ('processing', 'pending')
          AND started_at IS NOT NULL
          AND started_at < NOW() - INTERVAL :threshold
        ORDER BY started_at ASC
        LIMIT 20
    """)
    result = session.execute(sql, {
        "tenant_id": tenant_id,
        "threshold": f"{STUCK_AI_RUN_MINUTES} minutes",
    })
    return result.fetchall()


def _find_abandoned_reviews(session, tenant_id: str):
    """Find reviews abandoned with state-aware thresholds (tenant-scoped).

    Uses different thresholds per review state to prevent false positives:
    - draft: 72h — may be legitimately paused during initial triage
    - ai_analyzed unassigned: 48h — AI done but no reviewer assigned
    - assigned no activity: 24h — reviewer assigned but stalled
    - pending approval: 48h or SLA-based if deadline set

    Also excludes reviews that are currently in a cooldown window
    (recently recovered) to prevent re-flagging.
    """
    now = utc_now()

    # Find reviews in draft for >72h
    draft_sql = sa_text("""
        SELECT cr.review_id, cr.tenant_id, cr.status, cr.assigned_to,
               cr.created_at, cr.updated_at, cr.priority, cr.sla_deadline,
               cr.escalation_count
        FROM contract_reviews cr
        WHERE cr.tenant_id = :tenant_id
          AND cr.is_deleted = FALSE
          AND cr.status = 'draft'
          AND cr.created_at < NOW() - INTERVAL :draft_threshold
          AND NOT EXISTS (
              SELECT 1 FROM recovery_actions ra
              WHERE ra.entity_type = 'review'
                AND ra.entity_id = CAST(cr.review_id AS TEXT)
                AND ra.tenant_id = cr.tenant_id
                AND ra.cooldown_until > :now
          )
        ORDER BY cr.updated_at ASC
        LIMIT 20
    """)

    # Find reviews in ai_analyzed with no assignment for >48h
    ai_analyzed_sql = sa_text("""
        SELECT cr.review_id, cr.tenant_id, cr.status, cr.assigned_to,
               cr.created_at, cr.updated_at, cr.priority, cr.sla_deadline,
               cr.escalation_count
        FROM contract_reviews cr
        WHERE cr.tenant_id = :tenant_id
          AND cr.is_deleted = FALSE
          AND cr.status = 'ai_analyzed'
          AND cr.assigned_to IS NULL
          AND cr.updated_at < NOW() - INTERVAL :ai_threshold
          AND NOT EXISTS (
              SELECT 1 FROM recovery_actions ra
              WHERE ra.entity_type = 'review'
                AND ra.entity_id = CAST(cr.review_id AS TEXT)
                AND ra.tenant_id = cr.tenant_id
                AND ra.cooldown_until > :now
          )
        ORDER BY cr.updated_at ASC
        LIMIT 20
    """)

    # Find reviews that are assigned but have no activity for >24h
    assigned_sql = sa_text("""
        SELECT cr.review_id, cr.tenant_id, cr.status, cr.assigned_to,
               cr.created_at, cr.updated_at, cr.priority, cr.sla_deadline,
               cr.escalation_count
        FROM contract_reviews cr
        WHERE cr.tenant_id = :tenant_id
          AND cr.is_deleted = FALSE
          AND cr.assigned_to IS NOT NULL
          AND cr.status::text NOT IN ('approved', 'rejected', 'closed', 'archived', 'finalized', 'executed')
          AND cr.updated_at < NOW() - INTERVAL :assigned_threshold
          AND NOT EXISTS (
              SELECT 1 FROM recovery_actions ra
              WHERE ra.entity_type = 'review'
                AND ra.entity_id = CAST(cr.review_id AS TEXT)
                AND ra.tenant_id = cr.tenant_id
                AND ra.cooldown_until > :now
          )
        ORDER BY cr.updated_at ASC
        LIMIT 20
    """)

    results = []
    now_iso = now.isoformat()

    # Draft reviews
    for row in session.execute(draft_sql, {
        "tenant_id": tenant_id,
        "draft_threshold": f"{ABANDONED_DRAFT_HOURS} hours",
        "now": now_iso,
    }).fetchall():
        results.append(row)

    # ai_analyzed unassigned reviews
    for row in session.execute(ai_analyzed_sql, {
        "tenant_id": tenant_id,
        "ai_threshold": f"{ABANDONED_AI_ANALYZED_HOURS} hours",
        "now": now_iso,
    }).fetchall():
        results.append(row)

    # Assigned but stalled reviews
    for row in session.execute(assigned_sql, {
        "tenant_id": tenant_id,
        "assigned_threshold": f"{ABANDONED_ASSIGNED_HOURS} hours",
        "now": now_iso,
    }).fetchall():
        results.append(row)

    return results


# ═══════════════════════════════════════════════════════════════════
# Recovery Priority Weighting
# ═══════════════════════════════════════════════════════════════════

def _compute_recovery_priority(review) -> int:
    """Compute a composite priority score for a review recovery action.

    Combines multiple signals into a single priority weight:
    - Risk severity (from document_metadata)
    - SLA deadline proximity
    - Escalation history
    - Current priority level

    Returns a score 0-200 used to determine recovery action tier.
    """
    score = 0

    # ── Risk severity weight ──────────────────────────────────────
    metadata = getattr(review, "document_metadata", None) or {}
    if isinstance(metadata, dict):
        risk_score = metadata.get("risk_score", 0) or 0
        if risk_score >= 0.8:
            score += RISK_WEIGHT_CRITICAL
        elif risk_score >= 0.6:
            score += RISK_WEIGHT_HIGH
        elif risk_score >= 0.3:
            score += RISK_WEIGHT_MEDIUM
        else:
            score += RISK_WEIGHT_LOW

    # ── SLA deadline weight ───────────────────────────────────────
    sla_deadline = getattr(review, "sla_deadline", None)
    if sla_deadline:
        from app.kernel.datetime_utils import utc_now
        now = utc_now()
        hours_remaining = (sla_deadline - now).total_seconds() / 3600
        if hours_remaining < 0:
            score += SLA_WEIGHT_OVERDUE
        elif hours_remaining <= 4:
            score += SLA_WEIGHT_WITHIN_4H
        elif hours_remaining <= 24:
            score += SLA_WEIGHT_WITHIN_24H
        elif hours_remaining <= 72:
            score += SLA_WEIGHT_WITHIN_72H

    # ── Escalation history weight ─────────────────────────────────
    escalation_count = getattr(review, "escalation_count", 0) or 0
    score += escalation_count * ESCALATION_HISTORY_WEIGHT_PER_COUNT

    # ── Current priority weight ───────────────────────────────────
    priority = getattr(review, "priority", "normal") or "normal"
    priority_map = {"critical": 40, "urgent": 30, "high": 20, "normal": 0, "low": -10}
    score += priority_map.get(priority, 0)

    return max(0, min(200, score))


def _get_recovery_tier(priority_score: int) -> str:
    """Determine recovery action tier based on composite priority score.

    Returns one of:
    - 'critical': Immediate notification + auto-assignment
    - 'high': Priority bump + routing rules evaluation
    - 'normal': Standard flagging only
    """
    if priority_score >= PRIORITY_THRESHOLD_CRITICAL:
        return "critical"
    elif priority_score >= PRIORITY_THRESHOLD_HIGH:
        return "high"
    else:
        return "normal"


# ═══════════════════════════════════════════════════════════════════
# Ownership Resolution
# ═══════════════════════════════════════════════════════════════════

_USERS_TABLE_AVAILABLE: bool | None = None


def _users_table_available(session) -> bool:
    """Return True when the reviewer directory table exists (optional in dev)."""
    global _USERS_TABLE_AVAILABLE
    if _USERS_TABLE_AVAILABLE is not None:
        return _USERS_TABLE_AVAILABLE
    try:
        exists = session.execute(sa_text("SELECT to_regclass('public.users')")).scalar()
        _USERS_TABLE_AVAILABLE = exists is not None
    except Exception:
        _USERS_TABLE_AVAILABLE = False
    if not _USERS_TABLE_AVAILABLE:
        logger.debug(
            "[Recovery] users table not present — reviewer availability uses workload only"
        )
    return _USERS_TABLE_AVAILABLE


def _check_reviewer_availability(session, tenant_id: str, reviewer_id: str) -> tuple[bool, str]:
    """Check if a reviewer is available for new assignments.

    Returns:
        Tuple of (is_available: bool, reason: str)
    """
    if _users_table_available(session):
        user_sql = sa_text("""
            SELECT user_id, is_active, is_ooo
            FROM users
            WHERE user_id = :user_id AND tenant_id = :tenant_id
        """)
        user = session.execute(user_sql, {
            "user_id": reviewer_id,
            "tenant_id": tenant_id,
        }).fetchone()

        if not user:
            return False, "Reviewer not found"
        if not user.is_active:
            return False, "Reviewer is inactive"
        if getattr(user, "is_ooo", False):
            return False, "Reviewer is out of office"

    # Check current workload
    workload_sql = sa_text("""
        SELECT COUNT(*)::int AS active_count
        FROM contract_reviews
        WHERE assigned_to = :assigned_to
          AND tenant_id = :tenant_id
          AND is_deleted = FALSE
          AND status::text NOT IN ('approved', 'rejected', 'closed', 'archived', 'finalized', 'executed')
    """)
    workload = session.execute(workload_sql, {
        "assigned_to": reviewer_id,
        "tenant_id": tenant_id,
    }).fetchone()

    if workload and workload.active_count >= MAX_REVIEWS_PER_REVIEWER:
        return False, f"Reviewer at max capacity ({workload.active_count}/{MAX_REVIEWS_PER_REVIEWER})"

    if not _users_table_available(session):
        return True, "Available (users directory not configured)"

    return True, "Available"


def _find_available_reviewer(session, tenant_id: str, preferred_role: str = "reviewer") -> str | None:
    """Find an available reviewer using routing rules and workload balancing.

    Tries in order:
    1. Look for active routing rules that specify an assignee
    2. Find reviewers with the preferred role who are under capacity
    3. Fall back through the assignment chain

    Returns:
        Reviewer ID string, or None if no reviewer is available.
    """
    if not _users_table_available(session):
        return None

    # Try to find a reviewer with the preferred role who is under capacity
    role_sql = sa_text("""
        SELECT u.user_id, COUNT(cr.review_id)::int AS active_count
        FROM users u
        LEFT JOIN contract_reviews cr
            ON cr.assigned_to = u.user_id
            AND cr.tenant_id = :tenant_id
            AND cr.is_deleted = FALSE
            AND cr.status::text NOT IN ('approved', 'rejected', 'closed', 'archived', 'finalized', 'executed')
        WHERE u.tenant_id = :tenant_id
          AND u.is_active = TRUE
          AND (u.is_ooo IS NULL OR u.is_ooo = FALSE)
          AND u.role = :preferred_role
        GROUP BY u.user_id
        HAVING COUNT(cr.review_id) < :max_workload
        ORDER BY COUNT(cr.review_id) ASC
        LIMIT 1
    """)
    result = session.execute(role_sql, {
        "tenant_id": tenant_id,
        "preferred_role": preferred_role,
        "max_workload": MAX_REVIEWS_PER_REVIEWER,
    }).fetchone()

    if result:
        return str(result.user_id)

    # Fall back through the assignment chain
    for fallback_role in FALLBACK_ASSIGNMENT_CHAIN:
        if fallback_role == preferred_role:
            continue
        result = session.execute(role_sql, {
            "tenant_id": tenant_id,
            "preferred_role": fallback_role,
            "max_workload": MAX_REVIEWS_PER_REVIEWER,
        }).fetchone()
        if result:
            return str(result.user_id)

    return None


def _resolve_review_ownership(
    session,
    review,
    tenant_id: str,
    priority_score: int,
    recovery_tier: str,
) -> dict:
    """Attempt to resolve ownership for an abandoned review.

    For critical-tier recoveries, this will:
    1. Check if current assignee is available
    2. If not, find an available reviewer
    3. Auto-assign if a reviewer is found

    For high-tier recoveries, this will:
    1. Check current assignee availability
    2. Flag for reassignment if unavailable

    For normal-tier recoveries:
    1. Just flag for attention

    Returns:
        Dict with resolution action and details.
    """
    review_id = str(review.review_id)
    current_assignee = getattr(review, "assigned_to", None)
    result = {
        "action": "flag_only",
        "current_assignee": current_assignee,
        "new_assignee": None,
        "resolution": "flagged_for_attention",
        "details": "Review flagged for attention",
    }

    # ── Governance: Check for existing assignment lock ────────────
    lock_sql = sa_text("""
        SELECT lock_state, assignee_id, acquired_by
        FROM assignment_locks
        WHERE review_id = :review_id
          AND tenant_id = :tenant_id
          AND lock_state IN ('active', 'locked')
          AND expires_at > NOW()
        LIMIT 1
    """)
    existing_lock = session.execute(lock_sql, {
        "review_id": review_id,
        "tenant_id": tenant_id,
    }).fetchone()

    if existing_lock:
        logger.info(
            "[Recovery] Review %s has active lock (state=%s, assignee=%s) — skipping auto-assignment",
            review_id[:8], existing_lock.lock_state, existing_lock.assignee_id,
        )
        result["action"] = "locked"
        result["details"] = f"Review has active assignment lock ({existing_lock.lock_state})"
        return result

    if recovery_tier == "critical" or recovery_tier == "high":
        # Check current assignee availability
        if current_assignee:
            is_available, reason = _check_reviewer_availability(session, tenant_id, current_assignee)
            if not is_available:
                logger.info(
                    "[Recovery] Assignee %s unavailable for review %s: %s",
                    current_assignee, review_id[:8], reason,
                )
                result["details"] = f"Assignee unavailable: {reason}"

                # Try to find a replacement for critical reviews
                if recovery_tier == "critical":
                    new_assignee = _find_available_reviewer(session, tenant_id)
                    if new_assignee:
                        result["action"] = "auto_reassign"
                        result["new_assignee"] = new_assignee
                        result["resolution"] = f"Auto-reassigned from {current_assignee} to {new_assignee}"
                        result["details"] = f"Reassigned: {current_assignee} unavailable ({reason})"

                        # ── Create assignment lock ────────────────
                        _acquire_assignment_lock(
                            session, review_id, tenant_id, new_assignee,
                            "recovery_engine", recovery_tier,
                        )

                        # ── Record assignment audit trail ─────────
                        _record_assignment_audit(
                            session, review_id, tenant_id,
                            previous_assignee=current_assignee,
                            new_assignee=new_assignee,
                            assigned_by="recovery_engine",
                            assignment_source="recovery_reassign",
                            reason=f"Auto-reassigned: {current_assignee} unavailable ({reason})",
                            explainability={
                                "recovery_tier": recovery_tier,
                                "priority_score": priority_score,
                                "review_status": review.status,
                                "age_hours": round(age_minutes(utc_now(), review.updated_at) / 60.0, 1),
                            },
                        )
                    else:
                        result["action"] = "escalate_unassigned"
                        result["resolution"] = "No available reviewer — requires human intervention"
                        result["details"] = "No available reviewer found in any role"
            else:
                result["details"] = f"Assignee {current_assignee} is available"
        else:
            # No assignee — try to find one
            if recovery_tier == "critical":
                new_assignee = _find_available_reviewer(session, tenant_id)
                if new_assignee:
                    result["action"] = "auto_assign"
                    result["new_assignee"] = new_assignee
                    result["resolution"] = f"Auto-assigned to {new_assignee}"
                    result["details"] = "Unassigned review — auto-assigned to available reviewer"

                    # ── Create assignment lock ────────────────────
                    _acquire_assignment_lock(
                        session, review_id, tenant_id, new_assignee,
                        "recovery_engine", recovery_tier,
                    )

                    # ── Record assignment audit trail ─────────────
                    _record_assignment_audit(
                        session, review_id, tenant_id,
                        previous_assignee=None,
                        new_assignee=new_assignee,
                        assigned_by="recovery_engine",
                        assignment_source="recovery_auto",
                        reason="Unassigned review — auto-assigned to available reviewer",
                        explainability={
                            "recovery_tier": recovery_tier,
                            "priority_score": priority_score,
                            "review_status": review.status,
                            "age_hours": round(age_minutes(utc_now(), review.updated_at) / 60.0, 1),
                        },
                    )

    return result


def _acquire_assignment_lock(
    session,
    review_id: str,
    tenant_id: str,
    assignee_id: str,
    acquired_by: str,
    recovery_tier: str,
) -> None:
    """Acquire an assignment lock to prevent conflicting auto-assignments.

    Uses INSERT ... ON CONFLICT to handle race conditions safely.
    Lock TTL is based on recovery tier (critical = longer lock).
    """
    from datetime import timedelta
    now = utc_now()
    ttl_minutes = 120 if recovery_tier == "critical" else 60
    expires_at = now + timedelta(minutes=ttl_minutes)

    session.execute(sa_text("""
        INSERT INTO assignment_locks
            (lock_id, review_id, tenant_id, lock_state, assignee_id,
             acquired_by, acquired_at, expires_at)
        VALUES
            (gen_random_uuid(), :review_id, :tenant_id, 'active', :assignee_id,
             :acquired_by, :acquired_at, :expires_at)
        ON CONFLICT (review_id)
        DO UPDATE SET
            lock_state = 'active',
            assignee_id = :assignee_id,
            acquired_by = :acquired_by,
            acquired_at = :acquired_at,
            expires_at = :expires_at,
            released_at = NULL
        WHERE assignment_locks.lock_state IN ('released', 'expired')
    """), {
        "review_id": review_id,
        "tenant_id": tenant_id,
        "assignee_id": assignee_id,
        "acquired_by": acquired_by,
        "acquired_at": now,
        "expires_at": expires_at,
    })


def _record_assignment_audit(
    session,
    review_id: str,
    tenant_id: str,
    previous_assignee: str | None,
    new_assignee: str,
    assigned_by: str,
    assignment_source: str,
    reason: str | None,
    explainability: dict | None = None,
) -> None:
    """Record an immutable assignment audit trail entry.

    Includes workload context at time of assignment for explainability.
    """
    # Get workload context
    workload_sql = sa_text("""
        SELECT COUNT(*)::int AS active_count
        FROM contract_reviews
        WHERE assigned_to = :assignee
          AND tenant_id = :tenant_id
          AND is_deleted = FALSE
          AND status::text NOT IN ('approved', 'rejected', 'closed', 'archived', 'finalized', 'executed')
    """)
    workload = session.execute(workload_sql, {
        "assignee": new_assignee,
        "tenant_id": tenant_id,
    }).fetchone()
    active_count = workload.active_count if workload else 0

    session.execute(sa_text("""
        INSERT INTO assignment_audit
            (audit_id, review_id, tenant_id, previous_assignee, new_assignee,
             assigned_by, assignment_source, reason,
             reviewer_active_count, reviewer_max_capacity,
             explainability, created_at)
        VALUES
            (gen_random_uuid(), :review_id, :tenant_id, :previous_assignee, :new_assignee,
             :assigned_by, :assignment_source, :reason,
             :active_count, :max_capacity,
             :explainability, :created_at)
    """), {
        "review_id": review_id,
        "tenant_id": tenant_id,
        "previous_assignee": previous_assignee,
        "new_assignee": new_assignee,
        "assigned_by": assigned_by,
        "assignment_source": assignment_source,
        "reason": reason,
        "active_count": active_count,
        "max_capacity": MAX_REVIEWS_PER_REVIEWER,
        "explainability": explainability or {},
        "created_at": utc_now(),
    })


# ═══════════════════════════════════════════════════════════════════
# Recovery Handlers
# ═══════════════════════════════════════════════════════════════════

def _check_cooldown_and_escalation(session, entity_type: str, entity_id: str, tenant_id: str) -> tuple[bool, str | None]:
    """Check if an entity is in cooldown or has exceeded max recovery attempts.

    Args:
        entity_type: 'upload', 'ai_run', or 'review'
        entity_id: UUID string of the entity
        tenant_id: Tenant UUID string

    Returns:
        Tuple of (should_skip: bool, reason: str | None)
    """
    # Check cooldown — has this entity been recently recovered?
    cooldown_sql = sa_text("""
        SELECT cooldown_until, escalation_count FROM recovery_actions
        WHERE entity_type = :entity_type
          AND entity_id = :entity_id
          AND tenant_id = :tenant_id
        ORDER BY created_at DESC
        LIMIT 1
    """)
    last_action = session.execute(cooldown_sql, {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "tenant_id": tenant_id,
    }).fetchone()

    if last_action:
        # Check cooldown
        if last_action.cooldown_until and last_action.cooldown_until > utc_now():
            return True, f"Entity in cooldown until {last_action.cooldown_until.isoformat()}"

        # Check max escalation count
        if last_action.escalation_count >= MAX_RECOVERY_ATTEMPTS:
            return True, f"Entity reached max recovery attempts ({last_action.escalation_count}/{MAX_RECOVERY_ATTEMPTS})"

    return False, None


def _record_recovery_action(
    session,
    entity_type: str,
    entity_id: str,
    tenant_id: str,
    action_type: str,
    previous_state: str | None,
    new_state: str | None,
    success: bool,
    message: str | None,
    cooldown_minutes: int = RECOVERY_COOLDOWN_MINUTES,
) -> int:
    """Record a recovery action in the audit trail and return the escalation count.

    Args:
        session: Database session
        entity_type: 'upload', 'ai_run', or 'review'
        entity_id: UUID string of the entity
        tenant_id: Tenant UUID string
        action_type: Type of recovery action
        previous_state: State before recovery
        new_state: State after recovery
        success: Whether the action succeeded
        message: Human-readable description
        cooldown_minutes: Cooldown window in minutes

    Returns:
        The new escalation count for this entity
    """
    now = utc_now()

    # Get the current escalation count for this entity
    count_sql = sa_text("""
        SELECT COUNT(*) FROM recovery_actions
        WHERE entity_type = :entity_type
          AND entity_id = :entity_id
          AND tenant_id = :tenant_id
    """)
    escalation_count = session.execute(count_sql, {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "tenant_id": tenant_id,
    }).scalar() or 0

    new_escalation_count = escalation_count + 1
    cooldown_until = now + timedelta(minutes=cooldown_minutes)

    # Insert recovery action record
    session.execute(sa_text("""
        INSERT INTO recovery_actions
            (action_id, tenant_id, entity_type, entity_id, action_type,
             previous_state, new_state, escalation_count, cooldown_until,
             success, message, created_at)
        VALUES
            (gen_random_uuid(), :tenant_id, :entity_type, :entity_id, :action_type,
             :previous_state, :new_state, :escalation_count, :cooldown_until,
             :success, :message, :created_at)
    """), {
        "tenant_id": tenant_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action_type": action_type,
        "previous_state": previous_state,
        "new_state": new_state,
        "escalation_count": new_escalation_count,
        "cooldown_until": cooldown_until,
        "success": success,
        "message": message,
        "created_at": now,
    })

    return new_escalation_count


def _handle_stuck_upload(session, upload, tenant_id: str) -> str | None:
    """Handle a stuck upload by re-queuing pipeline work or marking failed (tenant-scoped).

    Governance:
    - Cooldown enforcement: Skip if recently recovered
    - Max recovery attempts: Skip if exceeded
    - Audit trail: Record all actions
    """
    upload_id = str(upload.upload_id)
    state = upload.ingestion_state
    age = age_minutes(utc_now(), upload.updated_at)

    # ── Governance: Check cooldown and escalation limits ──────────
    should_skip, reason = _check_cooldown_and_escalation(session, "upload", upload_id, tenant_id)
    if should_skip:
        logger.debug("[Recovery] Skipping upload %s: %s", upload_id[:8], reason)
        return None

    logger.warning(
        "[Recovery] Stuck upload detected: %s (tenant=%s, state=%s, age=%dmin, retries=%d)",
        upload_id, tenant_id[:8], state, int(age), upload.retry_count or 0,
    )

    # Re-queue ingestion tasks when stuck in active pipeline states (e.g. OCR processing)
    if (
        int(age) >= STUCK_INGESTION_REDISPATCH_MINUTES
        and state in (
            "uploaded",
            "ocr_pending",
            "ocr_processing",
            "storage_confirmed",
            "ocr_complete",
            "chunking_pending",
            "embedding_pending",
            "analysis_pending",
            "validating",
            "validated",
        )
        and (upload.retry_count or 0) < 3
    ):
        from app.domains.ingestion.models import coerce_ingestion_state
        from workers.ingestion_dispatch import redispatch_ingestion

        ing_state = coerce_ingestion_state(state)
        user_id = str(upload.user_id or "system")
        action = redispatch_ingestion(upload_id, tenant_id, user_id, ing_state)
        if action:
            session.execute(
                sa_text("""
                    UPDATE upload_sessions
                    SET retry_count = retry_count + 1,
                        ingestion_error = :error,
                        updated_at = NOW()
                    WHERE upload_id = :upload_id AND tenant_id = :tenant_id
                """).bindparams(
                    upload_id=upload_id,
                    tenant_id=tenant_id,
                    error=f"Auto-retry: re-queued {action} after {int(age)}min in {state}",
                )
            )

            _record_recovery_action(
                session=session,
                entity_type="upload",
                entity_id=upload_id,
                tenant_id=tenant_id,
                action_type="re-queued",
                previous_state=state,
                new_state=action,
                success=True,
                message=f"Re-queued {action} after {int(age)}min in {state}",
            )

            return (
                f"Re-queued {action} for stuck upload {upload_id[:8]} "
                f"(state={state}, age={int(age)}min)"
            )

    # If retries exceeded, mark as failed
    if (upload.retry_count or 0) >= 3:
        session.execute(
            sa_text("""
                UPDATE upload_sessions
                SET ingestion_state = 'failed',
                    ingestion_error = :error,
                    updated_at = NOW()
                WHERE upload_id = :upload_id AND tenant_id = :tenant_id
            """).bindparams(
                upload_id=upload_id, tenant_id=tenant_id,
                error=f"Auto-recovered: stuck in {state} for {int(age)}min after {upload.retry_count} retries",
            )
        )

        _record_recovery_action(
            session=session,
            entity_type="upload",
            entity_id=upload_id,
            tenant_id=tenant_id,
            action_type="marked_failed",
            previous_state=state,
            new_state="failed",
            success=True,
            message=f"Marked as failed after {upload.retry_count} retries, stuck for {int(age)}min",
        )

        return f"Marked stuck upload {upload_id[:8]} as failed (state={state}, age={int(age)}min)"

    # Otherwise increment retry count
    session.execute(
        sa_text("""
            UPDATE upload_sessions
            SET retry_count = retry_count + 1,
                ingestion_error = :error,
                updated_at = NOW()
            WHERE upload_id = :upload_id AND tenant_id = :tenant_id
        """).bindparams(
            upload_id=upload_id, tenant_id=tenant_id,
            error=f"Auto-retry: stuck in {state} for {int(age)}min",
        )
    )

    _record_recovery_action(
        session=session,
        entity_type="upload",
        entity_id=upload_id,
        tenant_id=tenant_id,
        action_type="retry_incremented",
        previous_state=state,
        new_state=state,
        success=True,
        message=f"Incremented retry count (now {upload.retry_count + 1}) after {int(age)}min in {state}",
    )

    return f"Flagged stuck upload {upload_id[:8]} for retry (state={state}, age={int(age)}min)"


def _handle_stuck_ai_run(session, run, tenant_id: str) -> str | None:
    """Handle a stuck AI run by marking it as failed (tenant-scoped).

    Governance:
    - Cooldown enforcement: Skip if recently recovered
    - Max recovery attempts: Skip if exceeded
    - Audit trail: Record all actions
    """
    run_id = str(run.run_id)
    status = run.status
    ref_time = run.started_at or run.created_at
    age = age_minutes(utc_now(), ref_time)

    # ── Governance: Check cooldown and escalation limits ──────────
    should_skip, reason = _check_cooldown_and_escalation(session, "ai_run", run_id, tenant_id)
    if should_skip:
        logger.debug("[Recovery] Skipping AI run %s: %s", run_id[:8], reason)
        return None

    logger.warning(
        "[Recovery] Stuck AI run detected: %s (tenant=%s, status=%s, age=%dmin, retries=%d)",
        run_id, tenant_id[:8], status, int(age), run.retry_count or 0,
    )

    # Mark as failed (tenant-scoped)
    session.execute(
        sa_text("""
            UPDATE ai_execution_runs
            SET status = 'failed',
                error_message = :error,
                completed_at = NOW()
            WHERE run_id = :run_id AND tenant_id = :tenant_id
        """).bindparams(
            run_id=run_id, tenant_id=tenant_id,
            error=f"Auto-recovered: stuck in {status} for {int(age)}min",
        )
    )

    # Also record the failure (tenant-scoped)
    session.execute(sa_text("""
        INSERT INTO ai_failures (run_id, tenant_id, failure_type, error_message, retry_count, created_at)
        VALUES (:run_id, :tenant_id, 'timeout', :error_message, :retry_count, :created_at)
    """), {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "error_message": f"Auto-recovered: stuck in {status} for {int(age)}min",
        "retry_count": run.retry_count or 0,
        "created_at": utc_now(),
    })

    _record_recovery_action(
        session=session,
        entity_type="ai_run",
        entity_id=run_id,
        tenant_id=tenant_id,
        action_type="marked_failed",
        previous_state=status,
        new_state="failed",
        success=True,
        message=f"Stuck in {status} for {int(age)}min",
    )

    return f"Recovered stuck AI run {run_id[:8]} (status={status}, age={int(age)}min)"


def _flag_abandoned_review(session, review, tenant_id: str) -> str | None:
    """Flag an abandoned review for attention (tenant-scoped).

    Governance:
    - Cooldown enforcement: Skip if recently recovered
    - Max recovery attempts: Skip if exceeded
    - Escalation-aware: Only bumps priority if escalation count is below max
    - Audit trail: Record all actions with full context
    - State-aware messaging: Different messages per review state
    - Priority weighting: Recovery actions weighted by risk, SLA, escalation history
    - Ownership resolution: Auto-assign or reassign based on reviewer availability
    """
    review_id = str(review.review_id)
    age_hours = age_minutes(utc_now(), review.updated_at) / 60.0

    # ── Governance: Check cooldown and escalation limits ──────────
    should_skip, reason = _check_cooldown_and_escalation(session, "review", review_id, tenant_id)
    if should_skip:
        logger.debug("[Recovery] Skipping review %s: %s", review_id[:8], reason)
        return None

    # ── Governance: Check max escalation count on the review itself ──
    current_escalation_count = review.escalation_count or 0
    if current_escalation_count >= MAX_ESCALATION_COUNT:
        logger.warning(
            "[Recovery] Review %s has reached max escalation count (%d/%d) — requiring human intervention",
            review_id[:8], current_escalation_count, MAX_ESCALATION_COUNT,
        )
        _record_recovery_action(
            session=session,
            entity_type="review",
            entity_id=review_id,
            tenant_id=tenant_id,
            action_type="max_escalation_reached",
            previous_state=review.status,
            new_state=review.status,
            success=False,
            message=f"Review has reached max escalation count ({current_escalation_count}/{MAX_ESCALATION_COUNT}) — requires human intervention",
            cooldown_minutes=ESCALATION_COOLDOWN_MINUTES,
        )
        return None

    # ── Recovery Priority Weighting ───────────────────────────────
    priority_score = _compute_recovery_priority(review)
    recovery_tier = _get_recovery_tier(priority_score)

    # ── Ownership Resolution ──────────────────────────────────────
    ownership = _resolve_review_ownership(session, review, tenant_id, priority_score, recovery_tier)

    logger.info(
        "[Recovery] Abandoned review detected: %s (tenant=%s, status=%s, age=%dh, "
        "assigned=%s, escalations=%d, priority_score=%d, tier=%s, ownership=%s)",
        review_id, tenant_id[:8], review.status, int(age_hours),
        review.assigned_to, current_escalation_count,
        priority_score, recovery_tier, ownership["action"],
    )

    # Build the priority bump expression based on recovery tier
    priority_bump_expr = """
        priority = CASE
            WHEN priority = 'normal' THEN 'high'
            WHEN priority = 'high' THEN 'urgent'
            ELSE priority
        END
    """
    if recovery_tier == "critical":
        priority_bump_expr = """
            priority = CASE
                WHEN priority = 'normal' THEN 'urgent'
                WHEN priority = 'high' THEN 'critical'
                WHEN priority = 'urgent' THEN 'critical'
                ELSE priority
            END
        """

    # Build the assignment update if ownership resolution found a new assignee
    assignment_update = ""
    if ownership.get("new_assignee"):
        assignment_update = f"""
            assigned_to = '{ownership["new_assignee"]}',
            assigned_by = 'recovery_engine',
            assigned_at = NOW(),
            started_at = NOW(),
        """

    # Execute the update
    session.execute(
        sa_text(f"""
            UPDATE contract_reviews
            SET {priority_bump_expr},
                escalation_count = escalation_count + 1,
                {assignment_update}
                updated_at = NOW()
            WHERE review_id = :review_id AND tenant_id = :tenant_id
        """).bindparams(review_id=review_id, tenant_id=tenant_id)
    )

    # Determine action type for audit trail
    action_type = "priority_bump"
    if ownership["action"] == "auto_reassign":
        action_type = "auto_reassigned"
    elif ownership["action"] == "auto_assign":
        action_type = "auto_assigned"
    elif ownership["action"] == "escalate_unassigned":
        action_type = "escalate_unassigned"

    # Build audit message with full context
    assigned_info = f"assigned_to={review.assigned_to}" if review.assigned_to else "unassigned"
    audit_message = (
        f"Review stalled in {review.status} for {int(age_hours)}h "
        f"({assigned_info}, priority_score={priority_score}, tier={recovery_tier})"
    )
    if ownership["resolution"]:
        audit_message += f" — {ownership['resolution']}"

    _record_recovery_action(
        session=session,
        entity_type="review",
        entity_id=review_id,
        tenant_id=tenant_id,
        action_type=action_type,
        previous_state=review.status,
        new_state=review.status,
        success=True,
        message=audit_message,
        cooldown_minutes=ESCALATION_COOLDOWN_MINUTES,
    )

    # ── Real-time Event Emission ────────────────────────────────
    # Fire-and-forget: emit events via the real-time event bus
    # to notify frontend clients without blocking recovery.
    _emit_recovery_event(tenant_id, action_type, {
        "review_id": review_id,
        "status": review.status,
        "age_hours": round(age_hours, 1),
        "priority_score": priority_score,
        "recovery_tier": recovery_tier,
        "escalation_count": current_escalation_count + 1,
        "assigned_to": ownership.get("new_assignee") or review.assigned_to,
        "resolution": ownership["resolution"],
        "action": ownership["action"],
    })

    # ── Send Notification for Auto-Assignment ───────────────────
    # If the review was auto-assigned or reassigned, notify the
    # new reviewer so they can acknowledge the assignment.
    if ownership.get("new_assignee") and ownership["action"] in ("auto_assign", "auto_reassign"):
        _send_assignment_notification(
            session, tenant_id,
            review_id=review_id,
            assignee_id=ownership["new_assignee"],
            assigned_by="recovery_engine",
            reason=ownership["details"],
            priority_score=priority_score,
            recovery_tier=recovery_tier,
        )

    # Build return message
    result_parts = [
        f"Flagged {review.status} review {review_id[:8]}",
        f"age={int(age_hours)}h",
        f"priority_score={priority_score}",
        f"tier={recovery_tier}",
        f"escalation={current_escalation_count + 1}",
    ]
    if ownership.get("new_assignee"):
        result_parts.append(f"assigned_to={ownership['new_assignee']}")
    elif review.assigned_to:
        result_parts.append(f"assigned_to={review.assigned_to}")
    if ownership["action"] == "escalate_unassigned":
        result_parts.append("requires_human_intervention")

    return " (" + ", ".join(result_parts) + ")"


def _cleanup_idempotency_records(session) -> int:
    """Clean up expired idempotency records."""
    result = session.execute(
        sa_text("""
            DELETE FROM idempotency_records
            WHERE expires_at < NOW()
            RETURNING record_id
        """)
    )
    count = len(result.fetchall())
    if count:
        logger.info("[Recovery] Cleaned up %d expired idempotency records", count)
    return count


# ── Metrics Aggregation Task ───────────────────────────────────────

@shared_task(
    name="aggregate_system_metrics",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
    acks_late=True,
)
def aggregate_system_metrics():
    """Aggregate and log system metrics for observability.

    Includes recovery action metrics (cooldown state, escalation counts)
    for operational visibility.

    Should be scheduled via Celery Beat every 15 minutes.
    Logs structured metric events that can be ingested by log aggregation tools.
    """
    from app.kernel.database.sync_session import get_sync_factory

    factory = get_sync_factory()
    session = factory.create_session(tenant_id="system", user_id="system", user_role="admin")

    try:
        # Get all active tenants for per-tenant metrics
        tenants_sql = sa_text("SELECT tenant_id FROM tenants WHERE is_active = TRUE")
        tenants = session.execute(tenants_sql).fetchall()

        total_active_uploads: dict[str, int] = {}
        total_active_ai: dict[str, int] = {}
        total_recent_failures = 0
        total_queue: dict[str, int] = {"ocr": 0, "embedding": 0, "analysis": 0}
        total_recovery_actions = 0
        total_active_cooldowns = 0
        total_max_escalations = 0
        tenant_metrics: list[dict] = []

        for (tenant_id,) in tenants:
            tid = str(tenant_id)

            # Active uploads by state (tenant-scoped)
            uploads_sql = sa_text("""
                SELECT ingestion_state, COUNT(*)::int AS count
                FROM upload_sessions
                WHERE tenant_id = :tenant_id
                  AND ingestion_state NOT IN ('review_ready', 'failed', 'cancelled', 'quarantined')
                GROUP BY ingestion_state
            """)
            for row in session.execute(uploads_sql, {"tenant_id": tid}).fetchall():
                total_active_uploads[row.ingestion_state] = total_active_uploads.get(row.ingestion_state, 0) + row.count

            # Active AI runs (tenant-scoped)
            ai_sql = sa_text("""
                SELECT status, COUNT(*)::int AS count
                FROM ai_execution_runs
                WHERE tenant_id = :tenant_id
                  AND status IN ('processing', 'pending')
                GROUP BY status
            """)
            for row in session.execute(ai_sql, {"tenant_id": tid}).fetchall():
                total_active_ai[row.status] = total_active_ai.get(row.status, 0) + row.count

            # Recent failures (tenant-scoped)
            failures_sql = sa_text("""
                SELECT COUNT(*)::int FROM ai_failures
                WHERE tenant_id = :tenant_id
                  AND created_at > NOW() - INTERVAL '1 hour'
            """)
            total_recent_failures += session.execute(failures_sql, {"tenant_id": tid}).scalar() or 0

            # Queue depth (tenant-scoped)
            queue_sql = sa_text("""
                SELECT
                    COUNT(*) FILTER (WHERE ingestion_state = 'ocr_pending')::int AS ocr_queue,
                    COUNT(*) FILTER (WHERE ingestion_state = 'embedding_pending')::int AS embedding_queue,
                    COUNT(*) FILTER (WHERE ingestion_state = 'analysis_pending')::int AS analysis_queue
                FROM upload_sessions
                WHERE tenant_id = :tenant_id
                  AND ingestion_state IN ('ocr_pending', 'embedding_pending', 'analysis_pending')
            """)
            qrow = session.execute(queue_sql, {"tenant_id": tid}).fetchone()
            if qrow:
                total_queue["ocr"] += qrow.ocr_queue or 0
                total_queue["embedding"] += qrow.embedding_queue or 0
                total_queue["analysis"] += qrow.analysis_queue or 0

            # ── Recovery governance metrics (tenant-scoped) ────────
            recovery_sql = sa_text("""
                SELECT COUNT(*)::int FROM recovery_actions
                WHERE tenant_id = :tenant_id
                  AND created_at > NOW() - INTERVAL '24 hours'
            """)
            total_recovery_actions += session.execute(recovery_sql, {"tenant_id": tid}).scalar() or 0

            cooldown_sql = sa_text("""
                SELECT COUNT(*)::int FROM recovery_actions
                WHERE tenant_id = :tenant_id
                  AND cooldown_until > NOW()
            """)
            total_active_cooldowns += session.execute(cooldown_sql, {"tenant_id": tid}).scalar() or 0

            max_esc_sql = sa_text("""
                SELECT COUNT(*)::int FROM recovery_actions
                WHERE tenant_id = :tenant_id
                  AND action_type = 'max_escalation_reached'
                  AND created_at > NOW() - INTERVAL '24 hours'
            """)
            total_max_escalations += session.execute(max_esc_sql, {"tenant_id": tid}).scalar() or 0

        logger.info(
            "[Metrics] System metrics snapshot",
            extra={
                "event": "system_metrics_snapshot",
                "active_uploads": total_active_uploads,
                "active_ai_runs": total_active_ai,
                "recent_failures_1h": total_recent_failures,
                "queue_depth": total_queue,
                "recovery_actions_24h": total_recovery_actions,
                "active_cooldowns": total_active_cooldowns,
                "max_escalations_24h": total_max_escalations,
                "tenants_count": len(tenants),
                "timestamp": utc_now().isoformat(),
            },
        )

        session.commit()

    except Exception as exc:
        session.rollback()
        logger.error("[Metrics] Metrics aggregation failed: %s", exc)
    finally:
        session.close()


# ── Real-time Event Emission ──────────────────────────────────────

def _emit_recovery_event(tenant_id: str, action_type: str, data: dict) -> None:
    """Emit a real-time event for a recovery action (fire-and-forget).

    Uses the existing real-time event system to push updates to
    frontend clients, eliminating the need for aggressive polling.

    This is fire-and-forget: failures are logged but not propagated
    to avoid disrupting the recovery workflow.
    """
    try:
        from app.kernel.events.realtime import EventTypes, emit_event
        import asyncio

        # Map action types to event types
        event_type_map = {
            "priority_bump": EventTypes.RECOVERY_REVIEW_FLAGGED,
            "auto_assigned": EventTypes.RECOVERY_REVIEW_ASSIGNED,
            "auto_reassigned": EventTypes.RECOVERY_REVIEW_ASSIGNED,
            "escalate_unassigned": EventTypes.RECOVERY_MAX_ESCALATION,
            "max_escalation_reached": EventTypes.RECOVERY_MAX_ESCALATION,
        }
        event_type = event_type_map.get(action_type, EventTypes.RECOVERY_ACTION_TAKEN)

        # Create and run the async emit in a new event loop
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(emit_event(tenant_id, event_type, data))
        finally:
            loop.close()

    except Exception as exc:
        logger.debug("[Recovery] Failed to emit real-time event: %s", exc)


def _send_assignment_notification(
    session,
    tenant_id: str,
    review_id: str,
    assignee_id: str,
    assigned_by: str,
    reason: str,
    priority_score: int,
    recovery_tier: str,
) -> None:
    """Send a notification to a reviewer about an auto-assignment.

    Creates an in-app notification and attempts real-time push.
    Fire-and-forget: failures are logged but not propagated.
    """
    try:
        # Insert notification record
        session.execute(sa_text("""
            INSERT INTO notifications
                (notification_id, tenant_id, user_id, type, title, body,
                 severity, entity_type, entity_id, action_url,
                 channel, delivery_status, dedup_key, created_at)
            VALUES
                (gen_random_uuid(), :tenant_id, :user_id, :type, :title, :body,
                 :severity, :entity_type, :entity_id, :action_url,
                 'in_app', 'pending', :dedup_key, :created_at)
        """), {
            "tenant_id": tenant_id,
            "user_id": assignee_id,
            "type": "review.auto_assigned",
            "title": "Review Auto-Assigned",
            "body": reason,
            "severity": "high" if recovery_tier == "critical" else "medium",
            "entity_type": "review",
            "entity_id": review_id,
            "action_url": f"/reviews/{review_id}",
            "dedup_key": f"auto_assign:{review_id}:{assignee_id}",
            "created_at": utc_now(),
        })

        # Also emit a real-time notification event
        _emit_recovery_event(tenant_id, "auto_assigned", {
            "review_id": review_id,
            "assignee_id": assignee_id,
            "assigned_by": assigned_by,
            "reason": reason,
            "priority_score": priority_score,
            "recovery_tier": recovery_tier,
            "notification_type": "review.auto_assigned",
        })

    except Exception as exc:
        logger.debug("[Recovery] Failed to send assignment notification: %s", exc)


# ── Helpers ────────────────────────────────────────────────────────

def update_sql(table: str, id_column: str, id_value: str, values: dict) -> sa_text:
    """Build a parameterized UPDATE statement."""
    set_clause = ", ".join(f"{k} = :{k}" for k in values)
    bind = {**values, "id_value": id_value}
    return sa_text(
        f"UPDATE {table} SET {set_clause} WHERE {id_column} = :id_value"
    ).bindparams(**bind)
