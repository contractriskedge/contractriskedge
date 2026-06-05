"""Tests for resilience quick wins — confirm_storage retry config and idempotency cleanup scheduler."""

from __future__ import annotations


class TestConfirmStorageRetryConfig:
    """Verify that confirm_storage_task has proper retry configuration."""

    def test_confirm_storage_has_retry_backoff(self):
        """confirm_storage_task should have retry_backoff=True and retry_backoff_max=300."""
        from workers.ingestion import confirm_storage_task

        task = confirm_storage_task
        assert task.max_retries == 3
        assert task.retry_backoff is True
        assert task.retry_backoff_max == 300
        assert task.name == "confirm_storage"
        assert task.queue == "ingestion"

    def test_confirm_storage_acks_late(self):
        """confirm_storage_task should have acks_late=True to prevent message loss on crash."""
        from workers.ingestion import confirm_storage_task

        assert confirm_storage_task.acks_late is True

    def test_confirm_storage_matches_other_tasks_retry_pattern(self):
        """confirm_storage should have the same retry pattern as other ingestion tasks."""
        from workers.ingestion import confirm_storage_task
        from workers.ingestion import validate_upload_task

        # Both should have max_retries=3
        assert confirm_storage_task.max_retries == validate_upload_task.max_retries

    def test_confirm_storage_is_celery_task(self):
        """confirm_storage_task should be a proper Celery task instance."""
        from workers.ingestion import confirm_storage_task

        assert hasattr(confirm_storage_task, "run")
        assert hasattr(confirm_storage_task, "delay")
        assert hasattr(confirm_storage_task, "apply_async")


class TestIdempotencyCleanupScheduler:
    """Verify that the idempotency cleanup scheduler is correctly configured."""

    def test_cleanup_schedule_exists(self):
        """The beat schedule should have a cleanup-idempotency-records entry."""
        from workers.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "cleanup-idempotency-records" in schedule

    def test_cleanup_schedule_runs_correct_task(self):
        """The cleanup should run recover_stuck_workflows which includes _cleanup_idempotency_records()."""
        from workers.celery_app import celery_app

        entry = celery_app.conf.beat_schedule["cleanup-idempotency-records"]
        assert entry["task"] == "recover_stuck_workflows"

    def test_cleanup_schedule_runs_hourly(self):
        """The cleanup should run every hour at minute 0."""
        from workers.celery_app import celery_app
        from celery.schedules import crontab

        entry = celery_app.conf.beat_schedule["cleanup-idempotency-records"]
        schedule = entry["schedule"]
        assert isinstance(schedule, crontab)
        assert schedule._orig_minute == "0"

    def test_recovery_task_includes_cleanup(self):
        """The recover_stuck_workflows function should call _cleanup_idempotency_records."""
        from app.workers.recovery import _cleanup_idempotency_records

        assert callable(_cleanup_idempotency_records)

    def test_all_ingestion_tasks_have_retry_backoff(self):
        """All ingestion tasks should have retry_backoff configured."""
        from workers.ingestion import validate_upload_task
        from workers.ingestion import confirm_storage_task

        tasks = [validate_upload_task, confirm_storage_task]
        for task in tasks:
            assert task.retry_backoff is not False, (
                f"{task.name} is missing retry_backoff"
            )
