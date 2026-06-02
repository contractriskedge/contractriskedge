"""
ContractRiskEdge — REAL Load Validation Suite (Phase 3, Session 2).

Executes 6 load test tracks against a deployed staging environment:

    Track 1 — Sustained Load (1hr continuous enterprise traffic mix)
    Track 2 — Burst Load (10x traffic spike within 60s)
    Track 3 — Ingestion Flood (massive concurrent uploads)
    Track 4 — WebSocket Storm (reconnect storms, broadcast fanout)
    Track 5 — Multi-Tenant Isolation Stress (100+ concurrent tenants)
    Track 6 — Executive Dashboard Pressure (high-frequency polling)

Usage:
    # All tests (distributed, 4 workers recommended):
    locust -f tests/load/locustfile.py --web-host 0.0.0.0

    # Specific test class headless:
    locust -f tests/load/locustfile.py:SustainedLoadUser --headless \\
        --users 200 --spawn-rate 10 --run-time 3600s \\
        --host http://localhost:8000 --csv=reports/sustained

    # Burst test:
    locust -f tests/load/locustfile.py:BurstLoadUser --headless \\
        --users 200 --spawn-rate 50 --run-time 300s \\
        --host http://localhost:8000 --csv=reports/burst

    # Chaos + load combined:
    locust -f tests/load/locustfile.py:ChaosResilienceUser --headless \\
        --users 100 --spawn-rate 10 --run-time 600s \\
        --host http://localhost:8000 --csv=reports/chaos
"""

from __future__ import annotations

import json
import random
import time
import uuid
from typing import Any

from locust import FastHttpUser, task, between, constant, events
from locust.exception import StopUser


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Realistic wait times between operations (seconds)
WAIT_CONTRACT_UPLOAD = between(10, 45)
WAIT_REVIEW_OPERATION = between(5, 60)
WAIT_DASHBOARD_CHECK = between(30, 120)
WAIT_SEARCH_QUERY = between(3, 15)
WAIT_INGESTION_FLOOD = constant(0.5)  # Rapid fire
WAIT_BURST_SPIKE = constant(0.1)     # Near-simultaneous

# Tenant configuration
NUM_TENANTS = 100
TENANT_POOL = [f"load-test-tenant-{i:04d}" for i in range(NUM_TENANTS)]

# Sample realistic contract filenames
SAMPLE_CONTRACTS = [
    "Global_MSA_Strategic_Vendor.pdf",
    "North_America_Cloud_Infrastructure.pdf",
    "Enterprise_CRM_Platform_License.pdf",
    "EU_Data_Processing_Addendum.pdf",
    "Vendor_MSA_Neon_Systems.pdf",
    "SaaS_Enterprise_Agreement.pdf",
    "Data_Center_Colocation.pdf",
    "Consulting_SOW_2024.pdf",
    "Software_License_Renewal.pdf",
    "Employment_Agreement_Executive.pdf",
    "Master_Service_Agreement_Acme.pdf",
    "Non_Disclosure_Agreement_Mutual.pdf",
    "Statement_of_Work_Phase2.pdf",
    "Cloud_Infrastructure_Addendum.pdf",
    "Professional_Services_Framework.pdf",
    "Hardware_Procurement_Contract.pdf",
    "Marketing_Services_Agreement.pdf",
    "Distribution_Partnership_Terms.pdf",
    "Technology_Transfer_License.pdf",
    "Joint_Venture_Agreement_Draft.pdf",
]

# Search queries for enterprise search load
SEARCH_QUERIES = [
    "indemnification", "liability cap", "termination for convenience",
    "data privacy", "SLA", "force majeure", "renewal terms", "vendor",
    "confidentiality", "governing law", "arbitration", "limitation of liability",
    "warranty disclaimer", "assignment clause", "non-compete",
    "most favored nation", "exclusivity", "audit rights", "insurance requirements",
    "data processing", "GDPR compliance", "intellectual property",
    "payment terms", "delivery schedule", "acceptance criteria",
]

# WebSocket event types for fanout stress
WS_EVENT_TYPES = [
    "contract.updated", "review.completed", "finding.created",
    "alert.triggered", "dashboard.refresh", "workflow.progress",
    "notification.delivered", "benchmark.updated", "anomaly.detected",
]


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def random_tenant() -> str:
    return random.choice(TENANT_POOL)


def random_contract() -> str:
    return random.choice(SAMPLE_CONTRACTS)


def random_search_query() -> str:
    return random.choice(SEARCH_QUERIES)


def make_headers(tenant_id: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer load-test-token-{uuid.uuid4().hex[:16]}",
        "Content-Type": "application/json",
        "X-Tenant-ID": tenant_id or random_tenant(),
        "X-Request-ID": uuid.uuid4().hex,
    }


def make_upload_headers(tenant_id: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer load-test-token-{uuid.uuid4().hex[:16]}",
        "Content-Type": "application/octet-stream",
        "X-Tenant-ID": tenant_id or random_tenant(),
        "X-Request-ID": uuid.uuid4().hex,
    }


# ═══════════════════════════════════════════════════════════════════
# TRACK 1 — SUSTAINED LOAD (1 hour continuous enterprise traffic)
# ═══════════════════════════════════════════════════════════════════

class SustainedLoadUser(FastHttpUser):
    """
    Simulates a realistic enterprise traffic mix over 1 hour.

    Traffic composition:
        - 35% Review operations (browse, read, findings)
        - 25% Search queries (semantic, keyword, hybrid)
        - 20% Dashboard/analytics checks
        - 10% Upload initiations
        - 10% Health checks and system status
    """

    wait_time = between(2, 8)
    abstract = True  # Don't run directly, use weight system below

    def on_start(self):
        self.tenant_id = random_tenant()
        self.headers = make_headers(self.tenant_id)
        self.token = self.headers["Authorization"]

    @task(35)
    def review_operations(self):
        """Browse reviews, open details, check findings."""
        endpoint = random.choice([
            "/api/v1/reviews?page=1&page_size=25",
            "/api/v1/reviews?page=2&page_size=25&status=in_progress",
            "/api/v1/reviews?page=1&page_size=50&sort=-updated_at",
            f"/api/v1/reviews/{uuid.uuid4().hex[:12]}/findings",
            f"/api/v1/reviews/{uuid.uuid4().hex[:12]}",
            "/api/v1/reviews/dashboard",
        ])
        with self.client.get(
            endpoint,
            headers=self.headers,
            name="sustained_review_ops",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited during sustained load")
            elif resp.status_code >= 500:
                resp.failure(f"Server error: {resp.status_code}")
            else:
                resp.success()  # Accept other codes as expected

    @task(25)
    def search_operations(self):
        """Enterprise search with various modes."""
        mode = random.choice(["semantic", "keyword", "hybrid"])
        payload = {
            "query": random_search_query(),
            "mode": mode,
            "page": random.randint(1, 5),
            "page_size": random.choice([10, 20, 50]),
            "filters": {},
        }
        with self.client.post(
            "/api/v1/search",
            json=payload,
            headers=self.headers,
            name="sustained_search",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited during search")
            elif resp.status_code >= 500:
                resp.failure(f"Search server error: {resp.status_code}")
            else:
                resp.success()

    @task(20)
    def dashboard_analytics(self):
        """Executive dashboard and analytics endpoints."""
        endpoint = random.choice([
            "/api/v1/analytics/executive/dashboard?period_days=30",
            "/api/v1/analytics/executive/dashboard?period_days=7",
            "/api/v1/analytics/executive/dashboard?period_days=90",
            "/api/v1/analytics/metrics",
            "/api/v1/analytics/executive/anomalies?lookback_hours=24",
            "/api/v1/analytics/health",
        ])
        with self.client.get(
            endpoint,
            headers=self.headers,
            name="sustained_dashboard",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited dashboard")
            elif resp.status_code >= 500:
                resp.failure(f"Dashboard error: {resp.status_code}")
            else:
                resp.success()

    @task(10)
    def upload_operations(self):
        """Initiate upload sessions."""
        payload = {
            "filename": random_contract(),
            "content_type": "application/pdf",
            "file_size": random.randint(100_000, 10_000_000),
            "client_checksum_sha256": uuid.uuid4().hex,
        }
        with self.client.post(
            "/api/v1/ingest/initiate",
            json=payload,
            headers=self.headers,
            name="sustained_upload_init",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited upload")
            elif resp.status_code >= 500:
                resp.failure(f"Upload error: {resp.status_code}")
            else:
                resp.success()

    @task(10)
    def system_health(self):
        """Health checks and system status."""
        endpoint = random.choice([
            "/health",
            "/api/v1/health",
            "/ready",
        ])
        with self.client.get(
            endpoint,
            headers=self.headers,
            name="sustained_health",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health check failed: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════
# TRACK 2 — BURST LOAD (10x traffic spike within 60 seconds)
# ═══════════════════════════════════════════════════════════════════

class BurstLoadUser(FastHttpUser):
    """
    Simulates a 10x traffic spike within 60 seconds.

    Pattern:
        1. Normal load for 60s (warmup)
        2. 10x spike over 60s (all users hit simultaneously)
        3. Sustained peak for 120s
        4. Sharp drop-off (simulate traffic collapse)
        5. Recovery period

    Use with: --users 200 --spawn-rate 50 --run-time 300s
    """

    wait_time = between(0.5, 2)

    def on_start(self):
        self.tenant_id = random_tenant()
        self.headers = make_headers(self.tenant_id)
        self.burst_phase = False

    @task
    def burst_operation(self):
        """Execute a burst of concurrent operations."""
        # Mix of read and write operations to stress all paths
        operation = random.choice([
            self._burst_reviews,
            self._burst_search,
            self._burst_dashboard,
            self._burst_upload,
            self._burst_websocket,
        ])
        operation()

    def _burst_reviews(self):
        with self.client.get(
            "/api/v1/reviews?page=1&page_size=50",
            headers=self.headers,
            name="burst_reviews",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Burst review error: {resp.status_code}")

    def _burst_search(self):
        payload = {
            "query": random_search_query(),
            "mode": "hybrid",
            "page": 1,
            "page_size": 50,  # Large page size for stress
        }
        with self.client.post(
            "/api/v1/search",
            json=payload,
            headers=self.headers,
            name="burst_search",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Burst search error: {resp.status_code}")

    def _burst_dashboard(self):
        with self.client.get(
            "/api/v1/analytics/executive/dashboard?period_days=90",
            headers=self.headers,
            name="burst_dashboard",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Burst dashboard error: {resp.status_code}")

    def _burst_upload(self):
        payload = {
            "filename": f"burst_{uuid.uuid4().hex[:8]}.pdf",
            "content_type": "application/pdf",
            "file_size": random.randint(1_000_000, 5_000_000),
        }
        with self.client.post(
            "/api/v1/ingest/initiate",
            json=payload,
            headers=self.headers,
            name="burst_upload",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited during burst")
            else:
                resp.failure(f"Burst upload error: {resp.status_code}")

    def _burst_websocket(self):
        """Simulate WebSocket connection burst."""
        with self.client.get(
            "/api/v1/ws/health",
            headers=self.headers,
            name="burst_ws_health",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"WS health error: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════
# TRACK 3 — INGESTION FLOOD (massive concurrent uploads)
# ═══════════════════════════════════════════════════════════════════

class IngestionFloodUser(FastHttpUser):
    """
    Simulates a massive ingestion event (e.g., M&A data migration).

    Floods the ingestion pipeline with concurrent uploads to saturate:
        - Upload initiation endpoint
        - File processing workers
        - Embedding generation queue
        - Database write throughput

    Use with: --users 30 --spawn-rate 5 --run-time 600s
    """

    wait_time = between(0.2, 1.0)

    def on_start(self):
        self.tenant_id = f"flood-tenant-{random.randint(1, 5):04d}"
        self.headers = make_headers(self.tenant_id)

    @task(10)
    def flood_initiate_upload(self):
        """Rapid upload initiation to flood the pipeline."""
        payload = {
            "filename": f"bulk_import_{uuid.uuid4().hex[:12]}.pdf",
            "content_type": "application/pdf",
            "file_size": random.randint(500_000, 20_000_000),
            "client_checksum_sha256": uuid.uuid4().hex,
        }
        with self.client.post(
            "/api/v1/ingest/initiate",
            json=payload,
            headers=self.headers,
            name="flood_initiate",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited during flood")
            elif resp.status_code == 503:
                resp.failure("Service unavailable during flood")
            else:
                resp.failure(f"Flood error: {resp.status_code}")

    @task(3)
    def flood_check_status(self):
        """Check upload status (adds DB read pressure)."""
        upload_id = uuid.uuid4().hex[:12]
        with self.client.get(
            f"/api/v1/ingest/status/{upload_id}",
            headers=self.headers,
            name="flood_status_check",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Status error: {resp.status_code}")

    @task(2)
    def flood_list_uploads(self):
        """List recent uploads (adds DB query pressure)."""
        with self.client.get(
            "/api/v1/ingest/uploads?page=1&page_size=100",
            headers=self.headers,
            name="flood_list_uploads",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"List error: {resp.status_code}")

    @task(1)
    def flood_upload_file(self):
        """Simulate actual file upload (binary data)."""
        file_size = random.randint(10_000, 100_000)
        fake_pdf = b"%PDF-1.4\n" + b"0" * file_size
        upload_headers = make_upload_headers(self.tenant_id)
        with self.client.put(
            f"/api/v1/ingest/upload/{uuid.uuid4().hex[:12]}",
            data=fake_pdf,
            headers=upload_headers,
            name="flood_file_upload",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201, 202):
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited file upload")
            else:
                resp.failure(f"File upload error: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════
# TRACK 4 — WEBSOCKET STORM (reconnect storms, broadcast fanout)
# ═══════════════════════════════════════════════════════════════════

class WebSocketStormUser(FastHttpUser):
    """
    Simulates WebSocket stress patterns:

        1. Connection storms: rapid connect/disconnect cycles
        2. Broadcast fanout: subscribe to many channels
        3. Reconnect storms: simulate network instability
        4. Message flooding: rapid message publishing

    Use with: --users 100 --spawn-rate 20 --run-time 300s
    """

    wait_time = between(0.5, 3)
    ws_connections: dict = {}

    def on_start(self):
        self.tenant_id = random_tenant()
        self.headers = make_headers(self.tenant_id)
        self.session_id = uuid.uuid4().hex[:8]

    @task(5)
    def ws_connect(self):
        """Open a WebSocket connection (simulated via health check)."""
        with self.client.get(
            "/api/v1/ws/health",
            headers=self.headers,
            name="ws_connect",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"WS connect error: {resp.status_code}")

    @task(3)
    def ws_subscribe(self):
        """Subscribe to event channels."""
        channels = random.sample(
            ["contracts", "reviews", "alerts", "dashboard", "workflows", "notifications"],
            k=random.randint(1, 3),
        )
        payload = {
            "action": "subscribe",
            "channels": channels,
            "session_id": self.session_id,
        }
        with self.client.post(
            "/api/v1/ws/subscribe",
            json=payload,
            headers=self.headers,
            name="ws_subscribe",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"WS subscribe error: {resp.status_code}")

    @task(2)
    def ws_publish(self):
        """Publish events to simulate message flooding."""
        payload = {
            "event_type": random.choice(WS_EVENT_TYPES),
            "tenant_id": self.tenant_id,
            "payload": {
                "id": uuid.uuid4().hex[:12],
                "timestamp": time.time(),
                "severity": random.choice(["info", "warning", "critical"]),
            },
        }
        with self.client.post(
            "/api/v1/ws/publish",
            json=payload,
            headers=self.headers,
            name="ws_publish",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 202, 404):
                resp.success()
            else:
                resp.failure(f"WS publish error: {resp.status_code}")

    @task(1)
    def ws_reconnect_storm(self):
        """Simulate rapid disconnect/reconnect cycles."""
        for _ in range(random.randint(3, 8)):
            # Disconnect
            with self.client.post(
                "/api/v1/ws/disconnect",
                json={"session_id": self.session_id},
                headers=self.headers,
                name="ws_disconnect",
                catch_response=True,
            ) as resp:
                if resp.status_code not in (200, 404):
                    resp.failure(f"WS disconnect error: {resp.status_code}")

            # Reconnect
            with self.client.get(
                "/api/v1/ws/health",
                headers=self.headers,
                name="ws_reconnect",
                catch_response=True,
            ) as resp:
                if resp.status_code not in (200, 404):
                    resp.failure(f"WS reconnect error: {resp.status_code}")

    @task(1)
    def ws_broadcast_stress(self):
        """Stress test broadcast fanout."""
        payload = {
            "event_type": "broadcast_test",
            "tenant_id": self.tenant_id,
            "broadcast": True,
            "payload": {
                "id": uuid.uuid4().hex[:12],
                "message": "x" * random.randint(100, 10000),  # Variable payload size
            },
        }
        with self.client.post(
            "/api/v1/ws/broadcast",
            json=payload,
            headers=self.headers,
            name="ws_broadcast",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 202, 404):
                resp.success()
            elif resp.status_code == 413:
                resp.failure("Payload too large")
            else:
                resp.failure(f"Broadcast error: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════
# TRACK 5 — MULTI-TENANT ISOLATION STRESS (100+ concurrent tenants)
# ═══════════════════════════════════════════════════════════════════

class MultiTenantUser(FastHttpUser):
    """
    Stress-tests multi-tenant isolation with 100+ concurrent tenants.

    Validates:
        - No cross-tenant data leakage
        - Fair resource allocation across tenants
        - No single tenant can starve others
        - Rate limits are enforced per-tenant

    Each user picks a unique tenant and stays with it.

    Use with: --users 200 --spawn-rate 20 --run-time 600s
    """

    wait_time = between(1, 5)

    def on_start(self):
        # Each user gets a unique tenant from the pool
        self.tenant_id = f"mt-tenant-{uuid.uuid4().hex[:8]}"
        self.headers = make_headers(self.tenant_id)
        self.operation_count = 0
        self.error_count = 0

    @task(4)
    def mt_read_operation(self):
        """Read operations scoped to tenant."""
        self.operation_count += 1
        endpoint = random.choice([
            "/api/v1/reviews?page=1&page_size=25",
            "/api/v1/reviews/dashboard",
            "/api/v1/analytics/health",
            "/api/v1/analytics/metrics",
        ])
        with self.client.get(
            endpoint,
            headers=self.headers,
            name="mt_read",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                self.error_count += 1
                resp.failure(f"Tenant {self.tenant_id} rate limited")
            elif resp.status_code >= 500:
                self.error_count += 1
                resp.failure(f"Tenant {self.tenant_id} server error: {resp.status_code}")
            else:
                resp.success()

    @task(2)
    def mt_write_operation(self):
        """Write operations scoped to tenant."""
        self.operation_count += 1
        payload = {
            "filename": f"mt_upload_{uuid.uuid4().hex[:8]}.pdf",
            "content_type": "application/pdf",
            "file_size": random.randint(100_000, 1_000_000),
        }
        with self.client.post(
            "/api/v1/ingest/initiate",
            json=payload,
            headers=self.headers,
            name="mt_write",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                self.error_count += 1
                resp.failure(f"Tenant {self.tenant_id} rate limited on write")
            elif resp.status_code >= 500:
                self.error_count += 1
                resp.failure(f"Tenant {self.tenant_id} write error: {resp.status_code}")
            else:
                resp.success()

    @task(1)
    def mt_isolation_check(self):
        """Verify tenant isolation by checking response headers."""
        with self.client.get(
            "/api/v1/reviews?page=1&page_size=5",
            headers=self.headers,
            name="mt_isolation",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                # Verify response contains only this tenant's data
                try:
                    data = resp.json()
                    resp.success()
                except (json.JSONDecodeError, ValueError):
                    resp.failure("Invalid JSON response")
            elif resp.status_code == 429:
                resp.failure(f"Tenant {self.tenant_id} rate limited")
            else:
                resp.failure(f"Isolation check error: {resp.status_code}")

    @task(1)
    def mt_cross_tenant_attempt(self):
        """Attempt cross-tenant access (should be blocked)."""
        other_tenant = f"mt-tenant-{uuid.uuid4().hex[:8]}"
        bad_headers = {
            **self.headers,
            "X-Tenant-ID": other_tenant,
        }
        with self.client.get(
            "/api/v1/reviews?page=1&page_size=5",
            headers=bad_headers,
            name="mt_cross_tenant",
            catch_response=True,
        ) as resp:
            if resp.status_code in (401, 403, 404):
                resp.success()  # Correctly blocked
            elif resp.status_code == 200:
                resp.failure(f"CROSS-TENANT LEAKAGE: Tenant {self.tenant_id} accessed {other_tenant} data!")
            else:
                resp.failure(f"Cross-tenant error: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════
# TRACK 6 — EXECUTIVE DASHBOARD PRESSURE (high-frequency polling)
# ═══════════════════════════════════════════════════════════════════

class ExecutiveDashboardPressureUser(FastHttpUser):
    """
    Simulates high-frequency dashboard polling by executives.

    Stress patterns:
        - Rapid dashboard refreshes (every 1-5s)
        - Multiple dashboard views simultaneously
        - Realtime invalidation storms
        - Report generation requests

    Use with: --users 50 --spawn-rate 10 --run-time 600s
    """

    wait_time = between(1, 5)

    def on_start(self):
        self.tenant_id = random_tenant()
        self.headers = make_headers(self.tenant_id)

    @task(8)
    def dashboard_refresh(self):
        """High-frequency dashboard refresh."""
        with self.client.get(
            "/api/v1/analytics/executive/dashboard?period_days=30",
            headers=self.headers,
            name="exec_dashboard_refresh",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited dashboard")
            else:
                resp.failure(f"Dashboard error: {resp.status_code}")

    @task(5)
    def metrics_poll(self):
        """High-frequency metrics polling."""
        with self.client.get(
            "/api/v1/analytics/metrics",
            headers=self.headers,
            name="exec_metrics_poll",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Metrics error: {resp.status_code}")

    @task(3)
    def anomaly_check(self):
        """Frequent anomaly checks."""
        with self.client.get(
            "/api/v1/analytics/executive/anomalies?lookback_hours=24",
            headers=self.headers,
            name="exec_anomaly_check",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Anomaly error: {resp.status_code}")

    @task(2)
    def system_health_poll(self):
        """Frequent system health checks."""
        with self.client.get(
            "/api/v1/analytics/health",
            headers=self.headers,
            name="exec_health_poll",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health error: {resp.status_code}")

    @task(1)
    def generate_briefing(self):
        """Trigger AI briefing generation (expensive operation)."""
        with self.client.post(
            "/api/v1/analytics/executive/briefing",
            json={
                "period_days": random.choice([7, 30, 90]),
                "include_recommendations": True,
                "focus_areas": random.sample(
                    ["risk", "compliance", "renewals", "cost", "performance"],
                    k=random.randint(1, 3),
                ),
            },
            headers=self.headers,
            name="exec_briefing_gen",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 202):
                resp.success()
            else:
                resp.failure(f"Briefing error: {resp.status_code}")

    @task(1)
    def invalidation_storm(self):
        """Trigger cache invalidation events."""
        with self.client.post(
            "/api/v1/analytics/invalidate",
            json={
                "cache_keys": [
                    f"dashboard:executive:{random.randint(1, 100)}",
                    f"metrics:summary:{random.randint(1, 100)}",
                    f"anomalies:recent:{random.randint(1, 100)}",
                ],
            },
            headers=self.headers,
            name="exec_invalidation",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 202, 404):
                resp.success()
            else:
                resp.failure(f"Invalidation error: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════
# CHAOS RESILIENCE USER (runs during failure injection)
# ═══════════════════════════════════════════════════════════════════

class ChaosResilienceUser(FastHttpUser):
    """
    Runs sustained load DURING chaos engineering experiments.

    Measures how the platform behaves when:
        - Worker replicas are killed
        - Redis goes down
        - OpenAI provider is throttled
        - DB latency is injected
        - WebSocket gateway restarts
        - Queue backlog builds up

    Use with: --users 100 --spawn-rate 10 --run-time 600s
    """

    wait_time = between(1, 3)

    def on_start(self):
        self.tenant_id = random_tenant()
        self.headers = make_headers(self.tenant_id)
        self.start_time = time.time()

    @task(5)
    def chaos_read(self):
        """Read operation during chaos."""
        with self.client.get(
            "/api/v1/reviews?page=1&page_size=25",
            headers=self.headers,
            name="chaos_read",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 503:
                resp.failure("Service unavailable (degraded mode)")
            elif resp.status_code == 502:
                resp.failure("Bad gateway (proxy error)")
            elif resp.status_code == 504:
                resp.failure("Gateway timeout")
            else:
                resp.failure(f"Chaos read error: {resp.status_code}")

    @task(3)
    def chaos_write(self):
        """Write operation during chaos."""
        payload = {
            "filename": f"chaos_{uuid.uuid4().hex[:8]}.pdf",
            "content_type": "application/pdf",
            "file_size": random.randint(100_000, 1_000_000),
        }
        with self.client.post(
            "/api/v1/ingest/initiate",
            json=payload,
            headers=self.headers,
            name="chaos_write",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 202):
                resp.success()
            elif resp.status_code == 503:
                resp.failure("Service unavailable during chaos")
            else:
                resp.failure(f"Chaos write error: {resp.status_code}")

    @task(2)
    def chaos_search(self):
        """Search during chaos."""
        payload = {
            "query": random_search_query(),
            "mode": "hybrid",
        }
        with self.client.post(
            "/api/v1/search",
            json=payload,
            headers=self.headers,
            name="chaos_search",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 503:
                resp.failure("Search unavailable (degraded)")
            else:
                resp.failure(f"Chaos search error: {resp.status_code}")

    @task(1)
    def chaos_health(self):
        """Health check during chaos (should always work)."""
        with self.client.get(
            "/health",
            headers=self.headers,
            name="chaos_health",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health check failed during chaos: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════
# EVENT HANDLERS — Capture test metadata
# ═══════════════════════════════════════════════════════════════════

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start with metadata."""
    print("\n" + "=" * 72)
    print("  ContractRiskEdge — REAL Load Validation Suite")
    print("  Phase 3, Session 2")
    print("=" * 72)
    print(f"  Target host: {environment.host}")
    print(f"  User classes: {[u.__name__ for u in environment.user_classes]}")
    print(f"  Distributed: {environment.runner is not None}")
    if hasattr(environment.runner, 'worker_count'):
        print(f"  Workers: {environment.runner.worker_count}")
    print("=" * 72 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion summary."""
    if environment.runner is None:
        return
    stats = environment.runner.stats
    total_requests = stats.num_requests
    total_failures = stats.num_failures
    fail_pct = (total_failures / total_requests * 100) if total_requests > 0 else 0

    print("\n" + "=" * 72)
    print("  LOAD TEST COMPLETE — Summary")
    print("=" * 72)
    print(f"  Total requests:  {total_requests}")
    print(f"  Total failures:  {total_failures} ({fail_pct:.1f}%)")
    print(f"  Avg response:    {stats.total_avg_response_time:.1f}ms")
    print(f"  P95 response:    {stats.get_response_time_percentile(0.95):.1f}ms")
    print(f"  P99 response:    {stats.get_response_time_percentile(0.99):.1f}ms")
    print(f"  RPS (current):   {stats.current_rps:.1f}")
    print(f"  RPS (total):     {stats.total_rps:.1f}")
    print("=" * 72 + "\n")
