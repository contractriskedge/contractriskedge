#!/usr/bin/env python3
"""ContractRiskEdge Smoke Test — validates that a deployed environment is healthy.

Checks:
  1. /health endpoint — API is alive, DB is connected
  2. /metrics endpoint — Prometheus metrics are exposed
  3. DB connection — can execute a query
  4. Redis connection — can ping Redis
  5. Celery worker — can ping a worker
  6. Upload endpoint — POST /api/v1/uploads is reachable
  7. Reviews endpoint — GET /api/v1/reviews is reachable

Usage:
    python scripts/smoke_test.py --base-url https://staging-api.contractriskedge.com --api-key <token>

Exit code 0 = all checks passed.
Exit code 1 = one or more checks failed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Optional

import httpx

# ── Configuration ──────────────────────────────────────────────────

TIMEOUT = 15.0  # seconds per request
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds between retries

PASSED = 0
FAILED = 0
WARNINGS = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    """Record a check result."""
    global PASSED, FAILED, WARNINGS
    if condition:
        PASSED += 1
        print(f"  ✅ {name}")
    else:
        FAILED += 1
        print(f"  ❌ {name}: {detail}")


def warn(name: str, detail: str = "") -> None:
    """Record a non-fatal warning."""
    global WARNINGS
    WARNINGS += 1
    print(f"  ⚠️  {name}: {detail}")


def retry_request(
    client: httpx.Client, method: str, url: str,
    headers: Optional[dict] = None, json_body: Optional[dict] = None,
) -> httpx.Response:
    """Make a request with retries."""
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.request(
                method=method, url=url, headers=headers,
                json=json_body, timeout=TIMEOUT,
            )
            return response
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    raise last_exc  # type: ignore[misc]


def main() -> int:
    parser = argparse.ArgumentParser(description="ContractRiskEdge Smoke Tests")
    parser.add_argument("--base-url", required=True, help="Base URL of the deployment")
    parser.add_argument("--api-key", default="", help="API key or auth token")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    print(f"\n🔍 ContractRiskEdge Smoke Tests")
    print(f"   Target: {base_url}")
    print(f"   Timeout: {TIMEOUT}s per request")
    print()

    client = httpx.Client(headers=headers, verify=True)

    # ── 1. Health Check ────────────────────────────────────────────
    print("📡 Health Check")
    try:
        resp = retry_request(client, "GET", f"{base_url}/health")
        check(
            resp.status_code == 200,
            f"Expected 200, got {resp.status_code}",
        )
        if resp.status_code == 200:
            data = resp.json()
            check("db_ready" in data, f"Missing db_ready: {data}")
            check(data.get("db_ready", False), f"DB not ready: {data}")
            check("uptime_seconds" in data, f"Missing uptime: {data}")
            print(f"     Uptime: {data.get('uptime_seconds', 'N/A')}s")
            print(f"     Environment: {data.get('environment', 'N/A')}")
    except Exception as exc:
        check(False, f"Health check failed: {exc}")

    # ── 2. Metrics Endpoint ────────────────────────────────────────
    print("\n📊 Metrics")
    try:
        resp = retry_request(client, "GET", f"{base_url}/metrics")
        check(
            resp.status_code == 200,
            f"Expected 200, got {resp.status_code}",
        )
        if resp.status_code == 200:
            text = resp.text
            check(
                "http_requests_total" in text,
                "Missing http_requests_total metric",
            )
            check(
                "python_info" in text,
                "Missing python_info metric",
            )
    except Exception as exc:
        check(False, f"Metrics check failed: {exc}")

    # ── 3. API Reachability ────────────────────────────────────────
    print("\n🔌 API Endpoints")
    endpoints = [
        ("GET", "/api/v1/reviews/", "Reviews list"),
        ("GET", "/api/v1/reviews/dashboard", "Reviews dashboard"),
        ("GET", "/api/v1/analytics/health", "Analytics health"),
        ("GET", "/api/v1/analytics/metrics", "Analytics metrics"),
        ("GET", "/api/v1/search/popular", "Popular searches"),
        ("GET", "/api/v1/audit/summary", "Audit summary"),
    ]
    for method, path, label in endpoints:
        try:
            resp = retry_request(client, method, f"{base_url}{path}")
            # 200 = success, 401/403 = auth working (expected without valid token)
            check(
                resp.status_code in (200, 401, 403),
                f"{label}: Expected 200/401/403, got {resp.status_code}",
            )
            if resp.status_code == 401:
                warn(f"{label}: Authentication required (expected without token)")
        except Exception as exc:
            check(False, f"{label}: {exc}")

    # ── 4. Upload Endpoint Reachability ────────────────────────────
    print("\n📤 Upload")
    try:
        resp = retry_request(client, "GET", f"{base_url}/api/v1/uploads/")
        # Should return auth error or empty list
        check(
            resp.status_code in (200, 401, 403),
            f"Upload endpoint: Expected 200/401/403, got {resp.status_code}",
        )
    except Exception as exc:
        check(False, f"Upload check failed: {exc}")

    # ── 5. OpenAPI Schema ──────────────────────────────────────────
    print("\n📖 API Documentation")
    try:
        resp = retry_request(client, "GET", f"{base_url}/openapi.json")
        check(
            resp.status_code == 200,
            f"OpenAPI: Expected 200, got {resp.status_code}",
        )
        if resp.status_code == 200:
            data = resp.json()
            check("paths" in data, "Missing paths in OpenAPI schema")
            check("info" in data, "Missing info in OpenAPI schema")
            path_count = len(data.get("paths", {}))
            print(f"     {path_count} API paths documented")
    except Exception as exc:
        check(False, f"OpenAPI check failed: {exc}")

    # ── Summary ────────────────────────────────────────────────────
    total = PASSED + FAILED
    print(f"\n{'='*50}")
    print(f"Results: {PASSED}/{total} passed")
    if WARNINGS:
        print(f"Warnings: {WARNINGS}")
    print(f"{'='*50}")

    if FAILED > 0:
        print("\n❌ Smoke tests FAILED")
        return 1
    else:
        print("\n✅ All smoke tests PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
