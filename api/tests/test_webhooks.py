"""Tests for the webhook notification module."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime

import pytest

from ingestion.models import JobRecord, JobStatus
from ingestion.webhooks import WebhookNotifier, WebhookDeliveryError, WebhookSignatureError


def test_build_payload():
    """Test webhook payload construction."""
    notifier = WebhookNotifier()
    job = JobRecord(
        job_id="job-123",
        document_id="doc-123",
        tenant_id="tenant-1",
        user_id="user-1",
        filename="test.pdf",
        content_type="application/pdf",
        status=JobStatus.DONE,
        progress=100.0,
    )

    payload = notifier._build_payload(job)
    assert payload["event"] == "ingestion.completed"
    assert payload["data"]["job_id"] == "job-123"
    assert payload["data"]["status"] == "DONE"


def test_compute_signature():
    """Test HMAC-SHA256 signature computation."""
    notifier = WebhookNotifier()
    payload = json.dumps({"test": "data"}).encode("utf-8")
    secret = "my-secret-key"

    signature = notifier._compute_signature(payload, secret)

    # Verify using standard HMAC
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    assert signature == expected


def test_validate_webhook_url_valid():
    """Test valid webhook URL validation."""
    notifier = WebhookNotifier()
    url = notifier._validate_webhook_url("https://hooks.example.com/callback")
    assert url == "https://hooks.example.com/callback"


def test_validate_webhook_url_invalid_scheme():
    """Test invalid webhook URL scheme rejection."""
    notifier = WebhookNotifier()
    from ingestion.webhooks import WebhookError
    with pytest.raises(WebhookError) as exc:
        notifier._validate_webhook_url("ftp://hooks.example.com/callback")
    assert "Unsupported webhook URL scheme" in str(exc.value)


def test_validate_webhook_url_no_netloc():
    """Test webhook URL with no network location."""
    notifier = WebhookNotifier()
    from ingestion.webhooks import WebhookError
    with pytest.raises(WebhookError):
        notifier._validate_webhook_url("https://")
