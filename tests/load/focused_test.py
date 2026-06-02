"""
ContractRiskEdge — Focused Load Test for REAL measurement.

Targets only endpoints confirmed to work on the running API.
"""
from __future__ import annotations
import random, uuid, time
from locust import FastHttpUser, task, between, events

TENANTS = [f"load-test-tenant-{i:04d}" for i in range(25)]
SEARCH_QUERIES = ["indemnification", "liability", "termination", "privacy", "sla", "confidentiality"]

class FocusedLoadUser(FastHttpUser):
    """Hits only confirmed-working endpoints with realistic mix."""
    wait_time = between(1, 3)

    def on_start(self):
        self.tenant_id = random.choice(TENANTS)
        self.headers = {
            "Authorization": f"Bearer test-token-{uuid.uuid4().hex[:16]}",
            "Content-Type": "application/json",
            "X-Tenant-ID": self.tenant_id,
        }

    @task(30)
    def list_reviews(self):
        with self.client.get("/api/v1/reviews/?page=1&page_size=25", headers=self.headers, name="list_reviews", catch_response=True) as resp:
            if resp.status_code == 200: resp.success()
            else: resp.failure(f"HTTP {resp.status_code}")

    @task(20)
    def review_dashboard(self):
        with self.client.get("/api/v1/reviews/dashboard", headers=self.headers, name="review_dashboard", catch_response=True) as resp:
            if resp.status_code == 200: resp.success()
            else: resp.failure(f"HTTP {resp.status_code}")

    @task(15)
    def executive_dashboard(self):
        with self.client.get("/api/v1/analytics/executive/dashboard?period_days=30", headers=self.headers, name="exec_dashboard", catch_response=True) as resp:
            if resp.status_code == 200: resp.success()
            else: resp.failure(f"HTTP {resp.status_code}")

    @task(10)
    def analytics_metrics(self):
        with self.client.get("/api/v1/analytics/metrics", headers=self.headers, name="analytics_metrics", catch_response=True) as resp:
            if resp.status_code == 200: resp.success()
            else: resp.failure(f"HTTP {resp.status_code}")

    @task(10)
    def analytics_health(self):
        with self.client.get("/api/v1/analytics/health", headers=self.headers, name="analytics_health", catch_response=True) as resp:
            if resp.status_code == 200: resp.success()
            else: resp.failure(f"HTTP {resp.status_code}")

    @task(5)
    def system_health(self):
        with self.client.get("/health", headers=self.headers, name="system_health", catch_response=True) as resp:
            if resp.status_code == 200: resp.success()
            else: resp.failure(f"HTTP {resp.status_code}")

    @task(5)
    def anomalies(self):
        with self.client.get("/api/v1/analytics/executive/anomalies?lookback_hours=24", headers=self.headers, name="anomalies", catch_response=True) as resp:
            if resp.status_code == 200: resp.success()
            else: resp.failure(f"HTTP {resp.status_code}")

    @task(5)
    def review_detail(self):
        rid = uuid.uuid4().hex[:12]
        with self.client.get(f"/api/v1/reviews/{rid}", headers=self.headers, name="review_detail", catch_response=True) as resp:
            if resp.status_code in (200, 404): resp.success()
            else: resp.failure(f"HTTP {resp.status_code}")


@events.test_start.add_listener
def on_start(environment, **kwargs):
    print("\n" + "="*60)
    print("  FOCUSED LOAD TEST — Working Endpoints Only")
    print("="*60)
    print(f"  Target: {environment.host}")
    print(f"  Users: {environment.runner.target_user_count if environment.runner else 'N/A'}")
    print("="*60 + "\n")

@events.test_stop.add_listener
def on_stop(environment, **kwargs):
    if not environment.runner: return
    s = environment.runner.stats
    total = s.num_requests
    fails = s.num_failures
    print("\n" + "="*60)
    print("  RESULTS")
    print("="*60)
    print(f"  Total requests:  {total}")
    print(f"  Failures:        {fails} ({fails/total*100:.1f}%)" if total else "  Failures: 0")
    print(f"  RPS:             {s.total_rps:.1f}")
    print(f"  P50:             {s.get_response_time_percentile(0.5):.1f}ms")
    print(f"  P95:             {s.get_response_time_percentile(0.95):.1f}ms")
    print(f"  P99:             {s.get_response_time_percentile(0.99):.1f}ms")
    print("="*60 + "\n")
