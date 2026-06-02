"""Queue reliability framework for async AI workloads.

Provides:
- Idempotency keys for safe retries
- Retry backoff strategies
- Dead-letter queue management
- Poison job quarantine
- Stuck job recovery
- Worker heartbeats
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


# ── Backoff Strategies ─────────────────────────────────────────────

class BackoffStrategy(str, Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    JITTERED = "jittered"


@dataclass
class RetryPolicy:
    """Retry policy for queue jobs."""
    max_retries: int = 3
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt."""
        if self.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.base_delay_seconds
        elif self.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.base_delay_seconds * attempt
        elif self.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.base_delay_seconds * (2 ** (attempt - 1))
        elif self.backoff_strategy == BackoffStrategy.JITTERED:
            import random
            exponential = self.base_delay_seconds * (2 ** (attempt - 1))
            delay = exponential * (0.5 + random.random() * 0.5)
        else:
            delay = self.base_delay_seconds

        import random
        if self.jitter and self.backoff_strategy != BackoffStrategy.JITTERED:
            delay *= 0.5 + random.random() * 0.5

        return min(delay, self.max_delay_seconds)


# ── Job Status ─────────────────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"
    QUARANTINED = "quarantined"
    CANCELLED = "cancelled"
    STUCK = "stuck"


class JobPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QueueJob:
    """A single job in the reliable queue system."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    idempotency_key: str = ""
    queue_name: str = "default"
    job_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    priority: JobPriority = JobPriority.MEDIUM

    status: JobStatus = JobStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3

    # Timing
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    last_retry_at: float | None = None
    next_retry_at: float | None = None

    # Heartbeat
    heartbeat_at: float | None = None
    heartbeat_timeout_seconds: float = 30.0

    # Error tracking
    last_error: str | None = None
    error_history: list[dict[str, Any]] = field(default_factory=list)

    # Result
    result: dict[str, Any] | None = None

    # Metadata
    tenant_id: str = ""
    trace_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if the job has exceeded its heartbeat timeout."""
        if self.heartbeat_at is None:
            return False
        return (time.time() - self.heartbeat_at) > self.heartbeat_timeout_seconds

    @property
    def is_dead(self) -> bool:
        """Check if the job has exceeded max retries."""
        return self.retry_count >= self.max_retries

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "idempotency_key": self.idempotency_key,
            "queue_name": self.queue_name,
            "job_type": self.job_type,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "last_error": self.last_error,
            "tenant_id": self.tenant_id,
            "trace_id": self.trace_id,
        }


# ── Dead-Letter Queue ──────────────────────────────────────────────

@dataclass
class DeadLetterEntry:
    """A job that has been moved to the dead-letter queue."""
    job_id: str
    original_queue: str
    job_type: str
    payload: dict[str, Any]
    failure_reason: str
    retry_count: int
    error_history: list[dict[str, Any]]
    moved_at: float = field(default_factory=time.time)
    reviewed: bool = False
    reviewed_by: str | None = None
    resolution: str | None = None  # "requeue", "discard", "ignore"


# ── Poison Job Quarantine ──────────────────────────────────────────

@dataclass
class QuarantineEntry:
    """A job placed in quarantine for suspicious behavior."""
    job_id: str
    job_type: str
    reason: str
    pattern: str  # e.g., "rapid_failure", "infinite_loop", "resource_exhaustion"
    details: dict[str, Any] = field(default_factory=dict)
    quarantined_at: float = field(default_factory=time.time)
    expires_at: float | None = None


# ── Reliable Queue Manager ─────────────────────────────────────────

JobHandler = Callable[[QueueJob], Awaitable[Any]]


@dataclass
class ReliableQueueManager:
    """Reliable queue manager with idempotency, retry, DLQ, and quarantine.

    This is an in-memory implementation. For production, back with Redis/PG.
    """

    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    _queues: dict[str, list[QueueJob]] = field(default_factory=dict)
    _processing: dict[str, QueueJob] = field(default_factory=dict)
    _dead_letter: list[DeadLetterEntry] = field(default_factory=list)
    _quarantine: list[QuarantineEntry] = field(default_factory=list)
    _idempotency_cache: dict[str, str] = field(default_factory=dict)  # key -> job_id
    _handlers: dict[str, JobHandler] = field(default_factory=dict)
    _stuck_job_scanner_active: bool = False

    # ── Idempotency ────────────────────────────────────────────────

    def make_idempotency_key(
        self, job_type: str, payload: dict[str, Any]
    ) -> str:
        """Create a deterministic idempotency key from job type and payload."""
        content = json.dumps({"type": job_type, "payload": payload}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def is_duplicate(self, idempotency_key: str) -> bool:
        """Check if a job with this idempotency key has already been processed."""
        return idempotency_key in self._idempotency_cache

    # ── Job Submission ─────────────────────────────────────────────

    async def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        queue_name: str = "default",
        priority: JobPriority = JobPriority.MEDIUM,
        idempotency_key: str | None = None,
        tenant_id: str = "",
        trace_id: str = "",
        max_retries: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> QueueJob:
        """Enqueue a job with idempotency support."""
        if idempotency_key is None:
            idempotency_key = self.make_idempotency_key(job_type, payload)

        if self.is_duplicate(idempotency_key):
            existing_id = self._idempotency_cache[idempotency_key]
            logger.info("Duplicate job detected (key=%s), returning existing job %s", idempotency_key[:16], existing_id)
            # Find and return the existing job
            for queue in self._queues.values():
                for job in queue:
                    if job.job_id == existing_id:
                        return job

        job = QueueJob(
            job_type=job_type,
            payload=payload,
            queue_name=queue_name,
            priority=priority,
            idempotency_key=idempotency_key,
            tenant_id=tenant_id,
            trace_id=trace_id,
            max_retries=max_retries or self.retry_policy.max_retries,
            metadata=metadata or {},
        )

        if queue_name not in self._queues:
            self._queues[queue_name] = []
        self._queues[queue_name].append(job)
        self._idempotency_cache[idempotency_key] = job.job_id

        logger.info("Enqueued job %s (%s) to queue '%s'", job.job_id[:8], job_type, queue_name)
        return job

    # ── Job Processing ─────────────────────────────────────────────

    async def process_next(
        self,
        queue_name: str = "default",
        handler: JobHandler | None = None,
    ) -> QueueJob | None:
        """Process the next available job from a queue."""
        queue = self._queues.get(queue_name, [])
        if not queue:
            return None

        # Find the highest priority pending job
        priority_order = {
            JobPriority.CRITICAL: 0,
            JobPriority.HIGH: 1,
            JobPriority.MEDIUM: 2,
            JobPriority.LOW: 3,
        }
        queue.sort(key=lambda j: (priority_order.get(j.priority, 99), j.created_at))

        job = queue.pop(0)
        job.status = JobStatus.PROCESSING
        job.started_at = time.time()
        self._processing[job.job_id] = job

        try:
            h = handler or self._handlers.get(job.job_type)
            if h is None:
                raise ValueError(f"No handler registered for job type '{job.job_type}'")

            # Execute with heartbeat
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(job))
            try:
                result = await h(job)
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()
                job.result = {"success": True, "data": result} if result else {"success": True}
                logger.info("Job %s (%s) completed successfully", job.job_id[:8], job.job_type)
            finally:
                heartbeat_task.cancel()

        except Exception as e:
            job.last_error = str(e)
            job.error_history.append({
                "attempt": job.retry_count + 1,
                "error": str(e),
                "timestamp": time.time(),
            })
            job.retry_count += 1
            job.last_retry_at = time.time()

            if job.is_dead:
                await self._move_to_dead_letter(job, str(e))
            else:
                job.status = JobStatus.RETRYING
                delay = self.retry_policy.get_delay(job.retry_count)
                job.next_retry_at = time.time() + delay
                # Re-enqueue for retry
                queue.append(job)
                logger.warning(
                    "Job %s failed (attempt %d/%d), retrying in %.1fs: %s",
                    job.job_id[:8], job.retry_count, job.max_retries, delay, e,
                )

        finally:
            self._processing.pop(job.job_id, None)

        return job

    async def _heartbeat_loop(self, job: QueueJob) -> None:
        """Send heartbeats for a processing job."""
        try:
            while True:
                job.heartbeat_at = time.time()
                await asyncio.sleep(min(job.heartbeat_timeout_seconds / 3, 10))
        except asyncio.CancelledError:
            pass

    # ── Dead-Letter Queue ──────────────────────────────────────────

    async def _move_to_dead_letter(self, job: QueueJob, reason: str) -> None:
        """Move a failed job to the dead-letter queue."""
        entry = DeadLetterEntry(
            job_id=job.job_id,
            original_queue=job.queue_name,
            job_type=job.job_type,
            payload=job.payload,
            failure_reason=reason,
            retry_count=job.retry_count,
            error_history=list(job.error_history),
        )
        self._dead_letter.append(entry)
        job.status = JobStatus.DEAD_LETTER
        logger.error(
            "Job %s moved to dead-letter queue after %d retries: %s",
            job.job_id[:8], job.retry_count, reason,
        )

    def get_dead_letter_queue(self) -> list[DeadLetterEntry]:
        """Get all dead-letter queue entries."""
        return list(self._dead_letter)

    async def requeue_from_dlq(
        self,
        job_id: str,
        new_max_retries: int = 5,
    ) -> QueueJob | None:
        """Re-queue a job from the dead-letter queue."""
        for i, entry in enumerate(self._dead_letter):
            if entry.job_id == job_id:
                self._dead_letter.pop(i)
                job = await self.enqueue(
                    job_type=entry.job_type,
                    payload=entry.payload,
                    queue_name=entry.original_queue,
                    idempotency_key=f"requeued_{job_id}_{int(time.time())}",
                    max_retries=new_max_retries,
                )
                logger.info("Requeued job %s from DLQ with max_retries=%d", job_id[:8], new_max_retries)
                return job
        return None

    # ── Poison Job Quarantine ──────────────────────────────────────

    async def quarantine_job(
        self,
        job: QueueJob,
        reason: str,
        pattern: str = "suspicious_behavior",
        ttl_minutes: float = 60.0,
    ) -> None:
        """Move a suspicious job to quarantine."""
        entry = QuarantineEntry(
            job_id=job.job_id,
            job_type=job.job_type,
            reason=reason,
            pattern=pattern,
            details={
                "payload": job.payload,
                "error_history": job.error_history,
                "retry_count": job.retry_count,
            },
            expires_at=time.time() + ttl_minutes * 60 if ttl_minutes > 0 else None,
        )
        self._quarantine.append(entry)
        job.status = JobStatus.QUARANTINED
        logger.warning("Job %s quarantined: %s (pattern=%s)", job.job_id[:8], reason, pattern)

    def get_quarantine(self) -> list[QuarantineEntry]:
        """Get all quarantined jobs."""
        return list(self._quarantine)

    # ── Stuck Job Recovery ─────────────────────────────────────────

    async def scan_stuck_jobs(
        self,
        timeout_seconds: float = 60.0,
    ) -> list[QueueJob]:
        """Scan for and recover stuck jobs."""
        stuck: list[QueueJob] = []
        now = time.time()

        for job_id, job in list(self._processing.items()):
            if job.started_at and (now - job.started_at) > timeout_seconds:
                job.status = JobStatus.STUCK
                stuck.append(job)
                self._processing.pop(job_id, None)

                # Re-enqueue with reset retry count
                job.retry_count = max(0, job.retry_count - 1)
                job.status = JobStatus.PENDING
                queue = self._queues.setdefault(job.queue_name, [])
                queue.append(job)
                logger.warning(
                    "Recovered stuck job %s (%s) — re-enqueued after %.0fs timeout",
                    job_id[:8], job.job_type, now - job.started_at,
                )

        return stuck

    async def start_stuck_job_scanner(
        self,
        interval_seconds: float = 30.0,
        timeout_seconds: float = 60.0,
    ) -> None:
        """Start a background task to periodically scan for stuck jobs."""
        if self._stuck_job_scanner_active:
            return
        self._stuck_job_scanner_active = True

        async def _scanner():
            while self._stuck_job_scanner_active:
                await asyncio.sleep(interval_seconds)
                try:
                    stuck = await self.scan_stuck_jobs(timeout_seconds)
                    if stuck:
                        logger.info("Stuck job scanner recovered %d jobs", len(stuck))
                except Exception as e:
                    logger.error("Stuck job scanner failed: %s", e)

        asyncio.create_task(_scanner())
        logger.info("Started stuck job scanner (interval=%ds, timeout=%ds)", interval_seconds, timeout_seconds)

    def stop_stuck_job_scanner(self) -> None:
        """Stop the stuck job scanner."""
        self._stuck_job_scanner_active = False

    # ── Handler Registration ───────────────────────────────────────

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        """Register a handler for a job type."""
        self._handlers[job_type] = handler
        logger.info("Registered handler for job type '%s'", job_type)

    # ── Queue Stats ────────────────────────────────────────────────

    def get_queue_stats(self) -> dict[str, Any]:
        """Get statistics for all queues."""
        stats = {}
        for queue_name, jobs in self._queues.items():
            pending = sum(1 for j in jobs if j.status == JobStatus.PENDING)
            retrying = sum(1 for j in jobs if j.status == JobStatus.RETRYING)
            stats[queue_name] = {
                "total": len(jobs),
                "pending": pending,
                "retrying": retrying,
                "processing": len(self._processing),
            }
        stats["dead_letter"] = len(self._dead_letter)
        stats["quarantine"] = len(self._quarantine)
        stats["idempotency_cache_size"] = len(self._idempotency_cache)
        return stats
