"""Redis-backed async ingestion queue with job status tracking.

Provides the IngestionQueue class that manages job lifecycle
(PENDING → PROCESSING → DONE/FAILED) using Redis for state
storage and Celery for distributed task execution.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

from ingestion.models import JobRecord, JobStatus

logger = logging.getLogger(__name__)


class IngestionQueueError(Exception):
    """Base exception for ingestion queue operations."""


class JobNotFoundError(IngestionQueueError):
    """Raised when a job ID is not found in the queue."""


class JobStateError(IngestionQueueError):
    """Raised when a state transition is invalid."""


@dataclass
class QueueStats:
    """Statistics for the ingestion queue."""

    pending: int = 0
    processing: int = 0
    done: int = 0
    failed: int = 0
    total: int = 0


class IngestionQueue:
    """Async Redis-backed queue for managing document ingestion jobs.

    Provides job lifecycle management with atomic state transitions
    and TTL-based expiration for completed jobs.

    Attributes:
        redis_url: Redis connection URL.
        job_ttl: Time-to-live in seconds for completed job records (default 7 days).
        namespace: Redis key prefix for all queue keys.
    """

    JOB_KEY_PREFIX = "ingestion:job:"
    STATUS_KEY = "ingestion:status"
    QUEUE_KEY = "ingestion:queue"

    VALID_TRANSITIONS: Dict[JobStatus, set] = {
        JobStatus.PENDING: {JobStatus.PROCESSING, JobStatus.FAILED},
        JobStatus.PROCESSING: {JobStatus.DONE, JobStatus.FAILED},
        JobStatus.DONE: set(),
        JobStatus.FAILED: {JobStatus.PENDING},  # Allow retry
    }

    def __init__(self, redis_url: str = "redis://localhost:6379/0", job_ttl: int = 604800) -> None:
        self.redis_url = redis_url
        self.job_ttl = job_ttl
        self.namespace = "contractrisk"
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create the async Redis connection.

        Returns:
            An async Redis client instance.
        """
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            logger.info("Connected to Redis at %s", self.redis_url)
        return self._redis

    def _job_key(self, job_id: str) -> str:
        """Build the Redis key for a job record.

        Args:
            job_id: The unique job identifier.

        Returns:
            The full Redis key string.
        """
        return f"{self.namespace}:{self.JOB_KEY_PREFIX}{job_id}"

    async def enqueue(self, job: JobRecord) -> str:
        """Enqueue a new ingestion job.

        Atomically stores the job record and adds it to the processing queue.

        Args:
            job: The JobRecord to enqueue. Must have status PENDING.

        Returns:
            The job ID string.

        Raises:
            JobStateError: If the job status is not PENDING.
        """
        if job.status != JobStatus.PENDING:
            raise JobStateError(
                f"Cannot enqueue job {job.job_id} with status {job.status}; "
                f"must be PENDING"
            )

        redis_client = await self._get_redis()
        job_key = self._job_key(job.job_id)

        pipe = redis_client.pipeline()
        pipe.set(
            job_key,
            job.model_dump_json(),
            ex=self.job_ttl,
        )
        pipe.rpush(self.QUEUE_KEY, job.job_id)
        pipe.hincrby(self.STATUS_KEY, JobStatus.PENDING.value, 1)
        await pipe.execute()

        logger.info(
            "Enqueued job %s for document %s (tenant: %s)",
            job.job_id,
            job.document_id,
            job.tenant_id,
        )
        return job.job_id

    async def dequeue(self, timeout: int = 5) -> Optional[JobRecord]:
        """Dequeue the next pending job for processing.

        Uses Redis BLPOP with a timeout for blocking pop from the queue.

        Args:
            timeout: Maximum seconds to wait for a job (default 5).

        Returns:
            A JobRecord if available, or None if the queue is empty.
        """
        redis_client = await self._get_redis()
        result = await redis_client.blpop(self.QUEUE_KEY, timeout=timeout)

        if result is None:
            return None

        _, job_id = result
        job = await self.get_job(job_id)
        if job is None:
            logger.warning("Dequeued job %s but no record found", job_id)
            return None

        return job

    async def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Retrieve a job record by its ID.

        Args:
            job_id: The unique job identifier.

        Returns:
            The JobRecord if found, or None.
        """
        redis_client = await self._get_redis()
        job_key = self._job_key(job_id)
        data = await redis_client.get(job_key)

        if data is None:
            return None

        try:
            return JobRecord.model_validate_json(data)
        except Exception as exc:
            logger.error("Failed to deserialize job %s: %s", job_id, exc)
            return None

    async def update_status(
        self,
        job_id: str,
        new_status: JobStatus,
        error_message: Optional[str] = None,
        progress: Optional[float] = None,
        **extra_fields: Any,
    ) -> JobRecord:
        """Atomically update a job's status and metadata.

        Validates the state transition before applying. Updates the
        completed_at timestamp when the job reaches a terminal state.

        Args:
            job_id: The job to update.
            new_status: The target status.
            error_message: Optional error message for FAILED status.
            progress: Optional progress percentage (0-100).
            **extra_fields: Additional fields to update on the JobRecord.

        Returns:
            The updated JobRecord.

        Raises:
            JobNotFoundError: If the job ID does not exist.
            JobStateError: If the requested state transition is invalid.
        """
        redis_client = await self._get_redis()
        job_key = self._job_key(job_id)

        # Use a Redis Lua script for atomic read-modify-write
        lua_script = """
        local job_key = KEYS[1]
        local status_key = ARGV[1]
        local new_status = ARGV[2]
        local old_status = ARGV[3]

        local data = redis.call('GET', job_key)
        if not data then
            return nil
        end

        local job = cjson.decode(data)
        if job.status ~= old_status then
            return {error = "Status mismatch: expected " .. old_status .. " but was " .. job.status}
        end

        job.status = new_status
        job.updated_at = ARGV[4]
        if new_status == 'DONE' or new_status == 'FAILED' then
            job.completed_at = ARGV[4]
        end

        redis.call('SET', job_key, cjson.encode(job), 'EX', ARGV[5])
        redis.call('HINCRBY', status_key, old_status, -1)
        redis.call('HINCRBY', status_key, new_status, 1)

        return cjson.encode(job)
        """

        now = datetime.utcnow().isoformat()
        job = await self.get_job(job_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")

        old_status = job.status
        if new_status not in self.VALID_TRANSITIONS.get(old_status, set()):
            raise JobStateError(
                f"Invalid state transition: {old_status} → {new_status} for job {job_id}"
            )

        script = redis_client.register_script(lua_script)
        result = await script(
            keys=[job_key],
            args=[
                self.STATUS_KEY,
                new_status.value,
                old_status.value,
                now,
                str(self.job_ttl),
            ],
        )

        if result is None:
            raise JobNotFoundError(f"Job {job_id} not found during status update")

        if isinstance(result, dict) and "error" in result:
            raise JobStateError(result["error"])

        # Reload the full job record
        updated_job = await self.get_job(job_id)
        if updated_job is None:
            raise JobNotFoundError(f"Job {job_id} disappeared after status update")

        # Apply extra field updates
        if error_message is not None:
            updated_job.error_message = error_message
        if progress is not None:
            updated_job.progress = progress
        for field_name, value in extra_fields.items():
            if hasattr(updated_job, field_name):
                setattr(updated_job, field_name, value)

        # Persist extra field changes
        await redis_client.set(job_key, updated_job.model_dump_json(), ex=self.job_ttl)

        logger.info(
            "Job %s status updated: %s → %s (progress: %.1f%%)",
            job_id,
            old_status,
            new_status,
            updated_job.progress,
        )
        return updated_job

    async def get_queue_stats(self) -> QueueStats:
        """Get current queue statistics.

        Returns:
            A QueueStats dataclass with counts per status.
        """
        redis_client = await self._get_redis()
        counts = await redis_client.hgetall(self.STATUS_KEY)

        return QueueStats(
            pending=int(counts.get(JobStatus.PENDING.value, 0)),
            processing=int(counts.get(JobStatus.PROCESSING.value, 0)),
            done=int(counts.get(JobStatus.DONE.value, 0)),
            failed=int(counts.get(JobStatus.FAILED.value, 0)),
            total=sum(int(v) for v in counts.values()),
        )

    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JobRecord]:
        """List jobs, optionally filtered by status.

        Args:
            status: Optional status filter.
            limit: Maximum number of jobs to return (default 100, max 1000).
            offset: Number of jobs to skip (default 0).

        Returns:
            A list of JobRecord objects.
        """
        if limit > 1000:
            limit = 1000

        redis_client = await self._get_redis()
        cursor = 0
        jobs: list[JobRecord] = []
        pattern = f"{self.namespace}:{self.JOB_KEY_PREFIX}*"

        while len(jobs) < offset + limit:
            cursor, keys = await redis_client.scan(
                cursor=cursor, match=pattern, count=100
            )
            for key in keys:
                data = await redis_client.get(key)
                if data is None:
                    continue
                try:
                    job = JobRecord.model_validate_json(data)
                except Exception:
                    continue
                if status is None or job.status == status:
                    jobs.append(job)
            if cursor == 0:
                break

        return jobs[offset : offset + limit]

    async def remove_job(self, job_id: str) -> bool:
        """Remove a job record from the queue.

        Args:
            job_id: The job to remove.

        Returns:
            True if the job was removed, False if it did not exist.
        """
        redis_client = await self._get_redis()
        job_key = self._job_key(job_id)

        job = await self.get_job(job_id)
        if job is None:
            return False

        pipe = redis_client.pipeline()
        pipe.delete(job_key)
        if job.status != JobStatus.PENDING:
            pipe.lrem(self.QUEUE_KEY, 0, job_id)
        pipe.hincrby(self.STATUS_KEY, job.status.value, -1)
        await pipe.execute()

        logger.info("Removed job %s from queue", job_id)
        return True

    async def close(self) -> None:
        """Close the Redis connection gracefully."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
            logger.info("Redis connection closed")

    async def __aenter__(self) -> IngestionQueue:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
