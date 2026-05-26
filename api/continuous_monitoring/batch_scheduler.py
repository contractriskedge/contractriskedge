"""Batch inference scheduler (V2-030).

Schedules LLM inference tasks for off-peak hours to optimize costs.
Manages a queue of batch jobs, prioritizes by urgency, and executes
during configurable low-cost time windows.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class BatchJobStatus(str, Enum):
    """Status of a batch inference job."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(str, Enum):
    """Priority levels for batch jobs."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class BatchJob:
    """A batch inference job."""

    job_id: str
    tenant_id: str
    job_type: str  # risk_analysis, redline, classification, extraction
    priority: JobPriority
    status: BatchJobStatus = BatchJobStatus.PENDING
    items: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    estimated_cost_usd: float = 0.0
    actual_cost_usd: float = 0.0
    scheduled_for: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "job_type": self.job_type,
            "priority": self.priority.value if isinstance(self.priority, JobPriority) else self.priority,
            "status": self.status.value if isinstance(self.status, BatchJobStatus) else self.status,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "failed_items": self.failed_items,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "actual_cost_usd": round(self.actual_cost_usd, 6),
            "scheduled_for": self.scheduled_for,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "progress_percent": round(
                self.completed_items / self.total_items * 100, 1
            ) if self.total_items > 0 else 0.0,
        }


class BatchScheduler:
    """Batch inference scheduler for cost-optimized LLM processing.

    Queues inference jobs and schedules them for off-peak hours.
    Supports priority-based execution and cost optimization.

    Usage:
        scheduler = BatchScheduler()
        job_id = await scheduler.submit_job(job)
        await scheduler.start()
        await scheduler.process_queue()
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        peak_hours_start: int = 8,    # 8 AM
        peak_hours_end: int = 18,      # 6 PM
        max_concurrent_jobs: int = 3,
        cost_multiplier_peak: float = 1.5,
        cost_multiplier_offpeak: float = 0.7,
    ) -> None:
        """Initialize the batch scheduler.

        Args:
            llm_client: LLM client for executing jobs.
            peak_hours_start: Hour when peak pricing starts (0-23).
            peak_hours_end: Hour when peak pricing ends (0-23).
            max_concurrent_jobs: Maximum concurrent job execution.
            cost_multiplier_peak: Cost multiplier during peak hours.
            cost_multiplier_offpeak: Cost multiplier during off-peak hours.
        """
        self._llm_client = llm_client
        self._peak_start = peak_hours_start
        self._peak_end = peak_hours_end
        self._max_concurrent = max_concurrent_jobs
        self._peak_multiplier = cost_multiplier_peak
        self._offpeak_multiplier = cost_multiplier_offpeak

        self._jobs: Dict[str, BatchJob] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._is_running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._processing_semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._job_processors: Dict[str, Callable] = {}

    def register_processor(self, job_type: str, processor: Callable) -> None:
        """Register a processor function for a job type.

        Args:
            job_type: The job type identifier.
            processor: Async function that processes a batch item.
        """
        self._job_processors[job_type] = processor
        logger.info("Registered processor for job type: %s", job_type)

    async def submit_job(
        self,
        tenant_id: str,
        job_type: str,
        items: List[Dict[str, Any]],
        priority: JobPriority = JobPriority.NORMAL,
        created_by: Optional[str] = None,
    ) -> str:
        """Submit a batch inference job.

        Args:
            tenant_id: The tenant identifier.
            job_type: Type of job (must have registered processor).
            items: List of items to process.
            priority: Job priority.
            created_by: User who created the job.

        Returns:
            Job ID.
        """
        job_id = str(uuid.uuid4())

        job = BatchJob(
            job_id=job_id,
            tenant_id=tenant_id,
            job_type=job_type,
            priority=priority,
            items=items,
            total_items=len(items),
            created_by=created_by,
        )

        self._jobs[job_id] = job

        # Determine scheduling
        now = datetime.utcnow()
        if priority in (JobPriority.URGENT, JobPriority.HIGH):
            job.scheduled_for = now.isoformat()
            job.status = BatchJobStatus.QUEUED
        else:
            # Schedule for next off-peak window
            next_offpeak = self._get_next_offpeak_time(now)
            job.scheduled_for = next_offpeak.isoformat()
            job.status = BatchJobStatus.QUEUED

        # Add to priority queue (lower number = higher priority)
        priority_order = {
            JobPriority.URGENT: 0,
            JobPriority.HIGH: 1,
            JobPriority.NORMAL: 2,
            JobPriority.LOW: 3,
        }
        queue_priority = priority_order.get(priority, 2)

        await self._queue.put((queue_priority, job_id))

        logger.info(
            "Submitted batch job %s: type=%s, items=%d, priority=%s, scheduled=%s",
            job_id, job_type, len(items), priority.value if isinstance(priority, JobPriority) else priority,
            job.scheduled_for,
        )

        return job_id

    async def start(self) -> None:
        """Start the background scheduler worker."""
        if self._is_running:
            return
        self._is_running = True
        self._worker_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Batch scheduler started (peak hours: %d:00-%d:00, max concurrent: %d)",
                     self._peak_start, self._peak_end, self._max_concurrent)

    async def stop(self) -> None:
        """Stop the background scheduler worker."""
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Batch scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Background loop that processes the job queue."""
        while self._is_running:
            try:
                # Get next job from queue (with timeout for periodic checks)
                try:
                    priority, job_id = await asyncio.wait_for(
                        self._queue.get(), timeout=5.0
                    )
                except asyncio.TimeoutError:
                    continue

                job = self._jobs.get(job_id)
                if not job:
                    self._queue.task_done()
                    continue

                # Check if it's time to execute
                if job.scheduled_for:
                    scheduled = datetime.fromisoformat(job.scheduled_for)
                    if datetime.utcnow() < scheduled:
                        # Re-queue and wait
                        await self._queue.put((priority, job_id))
                        self._queue.task_done()
                        await asyncio.sleep(30)
                        continue

                # Execute job with concurrency limit
                async with self._processing_semaphore:
                    await self._execute_job(job)

                self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Scheduler loop error: %s", exc)

    async def _execute_job(self, job: BatchJob) -> None:
        """Execute a batch job.

        Args:
            job: The job to execute.
        """
        processor = self._job_processors.get(job.job_type)
        if not processor:
            job.status = BatchJobStatus.FAILED
            job.error = f"No processor registered for job type: {job.job_type}"
            logger.error(job.error)
            return

        job.status = BatchJobStatus.PROCESSING
        job.started_at = datetime.utcnow().isoformat()
        logger.info("Processing batch job %s: %d items", job.job_id, job.total_items)

        # Process items
        for i, item in enumerate(job.items):
            try:
                result = await processor(item)
                job.results.append(result)
                job.completed_items += 1

                # Estimate cost (simplified)
                job.actual_cost_usd += 0.001  # Placeholder

            except Exception as exc:
                logger.error("Batch job %s item %d failed: %s", job.job_id, i, exc)
                job.failed_items += 1
                job.results.append({"error": str(exc), "item": item})

        # Complete job
        job.status = BatchJobStatus.COMPLETED if job.failed_items == 0 else BatchJobStatus.COMPLETED
        job.completed_at = datetime.utcnow().isoformat()

        # Apply cost multiplier based on execution time
        if job.started_at:
            start_hour = datetime.fromisoformat(job.started_at).hour
            if self._is_peak_hour(start_hour):
                job.actual_cost_usd *= self._peak_multiplier
            else:
                job.actual_cost_usd *= self._offpeak_multiplier

        logger.info(
            "Batch job %s completed: %d/%d items, %d failed, cost=$%.6f",
            job.job_id, job.completed_items, job.total_items,
            job.failed_items, job.actual_cost_usd,
        )

    def _is_peak_hour(self, hour: int) -> bool:
        """Check if the given hour is a peak hour.

        Args:
            hour: Hour to check (0-23).

        Returns:
            True if peak hour.
        """
        if self._peak_start <= self._peak_end:
            return self._peak_start <= hour < self._peak_end
        else:  # Overnight peak (e.g., 22:00 - 06:00)
            return hour >= self._peak_start or hour < self._peak_end

    def _get_next_offpeak_time(self, from_time: datetime) -> datetime:
        """Get the next off-peak time slot.

        Args:
            from_time: Starting time.

        Returns:
            Next off-peak datetime.
        """
        # Off-peak is outside peak hours
        # If currently off-peak, schedule 1 hour from now
        # If currently peak, schedule at next off-peak start

        current_hour = from_time.hour

        if self._is_peak_hour(current_hour):
            # Schedule for next off-peak start
            next_hour = self._peak_end
            next_time = from_time.replace(hour=next_hour, minute=0, second=0, microsecond=0)
            if next_time <= from_time:
                next_time += timedelta(days=1)
        else:
            # Schedule 1 hour from now (still off-peak)
            next_time = from_time + timedelta(hours=1)

        return next_time

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job's status and results.

        Args:
            job_id: The job identifier.

        Returns:
            Job dict or None.
        """
        job = self._jobs.get(job_id)
        return job.to_dict() if job else None

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or queued job.

        Args:
            job_id: The job identifier.

        Returns:
            True if cancelled, False if not found or already processing.
        """
        job = self._jobs.get(job_id)
        if not job:
            return False
        if job.status in (BatchJobStatus.PROCESSING, BatchJobStatus.COMPLETED):
            return False

        job.status = BatchJobStatus.CANCELLED
        logger.info("Cancelled batch job %s", job_id)
        return True

    async def get_queue_status(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get the batch queue status.

        Args:
            tenant_id: Optional tenant filter.

        Returns:
            Dict with queue status.
        """
        jobs_list = list(self._jobs.values())
        if tenant_id:
            jobs_list = [j for j in jobs_list if j.tenant_id == tenant_id]

        pending = sum(1 for j in jobs_list if j.status == BatchJobStatus.QUEUED)
        processing = sum(1 for j in jobs_list if j.status == BatchJobStatus.PROCESSING)
        completed = sum(1 for j in jobs_list if j.status == BatchJobStatus.COMPLETED)
        failed = sum(1 for j in jobs_list if j.status == BatchJobStatus.FAILED)

        total_items = sum(j.total_items for j in jobs_list)
        completed_items = sum(j.completed_items for j in jobs_list)

        now = datetime.utcnow()
        is_peak = self._is_peak_hour(now.hour)

        return {
            "is_running": self._is_running,
            "is_peak_hours": is_peak,
            "peak_hours": f"{self._peak_start}:00-{self._peak_end}:00",
            "current_cost_multiplier": self._peak_multiplier if is_peak else self._offpeak_multiplier,
            "queue_depth": self._queue.qsize(),
            "max_concurrent_jobs": self._max_concurrent,
            "jobs_summary": {
                "total": len(jobs_list),
                "queued": pending,
                "processing": processing,
                "completed": completed,
                "failed": failed,
            },
            "items_summary": {
                "total": total_items,
                "completed": completed_items,
                "progress_percent": round(completed_items / total_items * 100, 1) if total_items > 0 else 0.0,
            },
            "total_cost_usd": round(sum(j.actual_cost_usd for j in jobs_list), 4),
        }
