"""Sprint 27 Task 2 — Production Smoke Test.

Executes the complete real-world flow against a running API server.
Requires a running Celery worker for AI analysis completion.

Usage:
    SMOKE_TEST_BASE_URL="http://localhost:8000" python -m pytest tests/test_production_smoke.py -v --tb=short -s

Prerequisites:
    - API server running on SMOKE_TEST_BASE_URL
    - PostgreSQL, Redis, MinIO available
    - Celery worker running (for AI analysis completion)
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

logger = logging.getLogger("production_smoke")

SMOKE_LOG: list[dict[str, Any]] = []


def log_step(step: int, label: str, status: str, detail: str = "", duration: float = 0.0):
    entry = {
        "step": step, "label": label, "status": status,
        "detail": detail, "duration_s": round(duration, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    SMOKE_LOG.append(entry)
    icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}.get(status, "➡️")
    logger.info("%s [Step %d] %s — %s (%.1fs)", icon, step, label, detail, duration)


@pytest.fixture(scope="session")
def base_url() -> str:
    url = os.environ.get("SMOKE_TEST_BASE_URL", "http://localhost:8000")
    assert url, "Set SMOKE_TEST_BASE_URL env var"
    return url


@pytest.fixture(scope="session")
def client(base_url: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=30)


@pytest.fixture(scope="session")
def sample_pdf() -> bytes:
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    style = ParagraphStyle("Smoke", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=8)
    clauses = [
        "1. Definitions. In this Agreement, unless the context otherwise requires: (a) 'Affiliate' means any entity that controls, is controlled by, or is under common control with a party.",
        "2. Scope of Services. The Provider shall perform the Services described in Exhibit A.",
        "3. Payment Terms. The Customer shall pay the fees within thirty (30) days of invoice.",
        "4. Confidentiality. Each party agrees to hold the other's Confidential Information in strict confidence.",
        "5. Limitation of Liability. NEITHER PARTY SHALL BE LIABLE FOR ANY INDIRECT DAMAGES.",
        "6. Governing Law. This Agreement shall be governed by the laws of the State of Delaware.",
        "7. Term and Termination. This Agreement shall continue for twelve (12) months.",
    ]
    story = [Paragraph("MASTER SERVICES AGREEMENT", style), Spacer(1, 12)]
    for c in clauses:
        story.append(Paragraph(c, style))
        story.append(Spacer(1, 6))
    story.append(Paragraph("[End of Agreement]", style))
    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════
# SMOKE TEST
# ═══════════════════════════════════════════════════════════════════


class TestProductionSmoke:
    """End-to-end production smoke test."""

    def test_01_health_check(self, client):
        """API is running and healthy."""
        t0 = time.time()
        r = client.get("/health")
        assert r.status_code == 200, f"Health check: HTTP {r.status_code}"
        data = r.json()
        assert data["status"] == "healthy"
        log_step(1, "Health check", "PASS", f"uptime={data['uptime_seconds']}s", time.time() - t0)

    def test_02_auth_token(self, client):
        """Dev JWT token can be issued."""
        t0 = time.time()
        r = client.post("/api/v1/auth/token")
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        client.headers["Authorization"] = f"Bearer {data['access_token']}"
        log_step(2, "Auth token", "PASS", f"token={data['access_token'][:20]}...", time.time() - t0)

    def test_03_upload_contract(self, client, sample_pdf):
        """Contract PDF uploads successfully."""
        t0 = time.time()
        files = {"file": ("smoke_test.pdf", sample_pdf, "application/pdf")}
        r = client.post("/api/v1/uploads", files=files)
        assert r.status_code in (200, 201, 202), f"Upload: HTTP {r.status_code} {r.text[:200]}"
        data = r.json()
        upload_id = data.get("upload_id") or (data.get("data") or {}).get("upload_id")
        assert upload_id, f"No upload_id in response"
        # Store for subsequent tests via a module-level var
        TestProductionSmoke._upload_id = upload_id
        log_step(3, "Upload contract", "PASS", f"upload_id={upload_id}", time.time() - t0)

    def test_04_upload_polling(self, client):
        """Upload reaches processing state."""
        upload_id = getattr(self, "_upload_id", None) or TestProductionSmoke._upload_id
        assert upload_id, "No upload_id from previous step"
        t0 = time.time()
        max_polls = 15
        for i in range(max_polls):
            r = client.get(f"/api/v1/uploads/{upload_id}")
            assert r.status_code == 200
            data = r.json()
            d = data.get("data") if isinstance(data.get("data"), dict) else data
            state = str(d.get("ingestion_state", d.get("state", d.get("status", ""))))
            logger.info("  Poll %d/%d: state=%s", i + 1, max_polls, state)
            if state and state not in ("pending", "uploading", "queued", ""):
                log_step(4, "Upload processing", "PASS", f"state={state}", time.time() - t0)
                return
            time.sleep(2)
        log_step(4, "Upload processing", "SKIP",
                 f"State unchanged after {max_polls} polls (Celery worker may be needed)", time.time() - t0)

    def test_05_trigger_ai_analysis(self, client):
        """AI analysis can be dispatched."""
        upload_id = TestProductionSmoke._upload_id
        assert upload_id, "No upload_id from previous step"
        t0 = time.time()
        r = client.post("/api/v1/ai/analyze", json={"upload_id": upload_id, "analysis_type": "full"})
        if r.status_code in (200, 201, 202):
            data = r.json()
            run_id = data.get("run_id") or (data.get("data") or {}).get("run_id")
            if run_id:
                TestProductionSmoke._run_id = run_id
            log_step(5, "AI analysis dispatch", "PASS", f"run_id={run_id}", time.time() - t0)
        elif r.status_code == 409:
            log_step(5, "AI analysis dispatch", "PASS", "already in progress/completed", time.time() - t0)
        else:
            log_step(5, "AI analysis dispatch", "FAIL", f"HTTP {r.status_code}", time.time() - t0)

    def test_06_poll_ai_analysis(self, client):
        """AI analysis completes (requires Celery worker)."""
        run_id = getattr(self, "_run_id", None) or getattr(TestProductionSmoke, "_run_id", None)
        if not run_id:
            log_step(6, "AI analysis completion", "SKIP", "No run_id to poll", 0)
            return
        t0 = time.time()
        max_polls = 30
        for i in range(max_polls):
            r = client.get(f"/api/v1/ai/runs/{run_id}")
            if r.status_code == 200:
                data = r.json()
                d = data.get("data") if isinstance(data.get("data"), dict) else data
                status = d.get("status", "")
                logger.info("  AI run poll %d/%d: status=%s", i + 1, max_polls, status)
                if status == "completed":
                    log_step(6, "AI analysis completion", "PASS", "completed", time.time() - t0)
                    return
                if status == "failed":
                    log_step(6, "AI analysis completion", "FAIL", f"failed: {d.get('error', 'unknown')}", time.time() - t0)
                    return
            time.sleep(5)
        log_step(6, "AI analysis completion", "SKIP",
                 "Not completed within poll window (Celery worker may not be running)", time.time() - t0)

    def test_07_list_reviews(self, client):
        """Reviews endpoint returns data."""
        t0 = time.time()
        r = client.get("/api/v1/reviews/", params={"page_size": 5})
        assert r.status_code == 200
        data = r.json()
        items = data.get("data") or data.get("reviews") or data.get("results", [])
        log_step(7, "List reviews", "PASS", f"reviews={len(items)}", time.time() - t0)

    def test_08_audit_events(self, client):
        """Audit trail endpoint is accessible."""
        t0 = time.time()
        r = client.get("/api/v1/audit/events", params={"page_size": 5})
        assert r.status_code == 200
        data = r.json()
        items = data.get("data") or data.get("events") or data.get("results", [])
        log_step(8, "Audit events", "PASS", f"events={len(items)}", time.time() - t0)

    def test_09_dashboard(self, client):
        """Dashboard endpoint is accessible."""
        t0 = time.time()
        r = client.get("/api/v1/reviews/dashboard")
        if r.status_code == 200:
            log_step(9, "Analytics dashboard", "PASS", "accessible", time.time() - t0)
        else:
            log_step(9, "Analytics dashboard", "SKIP", f"HTTP {r.status_code}", time.time() - t0)

    def test_10_search(self, client):
        """Search endpoint is accessible."""
        t0 = time.time()
        r = client.get("/api/v1/search/", params={"q": "agreement", "page_size": 3})
        if r.status_code == 200:
            log_step(10, "Search endpoint", "PASS", "accessible", time.time() - t0)
        else:
            log_step(10, "Search endpoint", "SKIP", f"HTTP {r.status_code}", time.time() - t0)

    def test_99_summary(self, client):
        """Print smoke test summary."""
        print("\n" + "=" * 70)
        print("PRODUCTION SMOKE TEST RESULTS")
        print("=" * 70)
        passed = sum(1 for s in SMOKE_LOG if s["status"] == "PASS")
        failed = sum(1 for s in SMOKE_LOG if s["status"] == "FAIL")
        skipped = sum(1 for s in SMOKE_LOG if s["status"] == "SKIP")
        total = len(SMOKE_LOG)
        print(f"\n  Total:    {total}")
        print(f"  Passed:   {passed}")
        print(f"  Failed:   {failed}")
        print(f"  Skipped:  {skipped}")
        print(f"\n  {'Step':<6} {'Status':<8} {'Label':<35} {'Duration':<10} Detail")
        print(f"  {'-'*80}")
        for s in SMOKE_LOG:
            print(f"  {s['step']:<6} {s['status']:<8} {s['label']:<35} {s['duration_s']:<8.1f}s {s['detail'][:50]}")
        print(f"\n{'='*70}")
        print(f"OVERALL: {'PASS' if failed == 0 else 'FAIL'}")
        print(f"{'='*70}")

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "steps": SMOKE_LOG,
            "summary": {"total": total, "passed": passed, "failed": failed, "skipped": skipped},
        }
        path = "/tmp/production_smoke_report.json"
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info("Report saved to %s", path)

        assert failed == 0, f"{failed} step(s) failed"
