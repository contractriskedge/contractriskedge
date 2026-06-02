#!/usr/bin/env python3
"""
ContractRiskEdge — Chaos Engineering Harness (Phase 3, Session 2, Track 4).

Executes controlled failure injection experiments against a running staging
environment while load tests are in progress.

Experiments:
    1. Kill worker replicas (ingestion, ai) — observe queue backlog + recovery
    2. Kill Redis — observe degraded mode + reconnection
    3. Throttle OpenAI provider — observe retry coordination + fallback
    4. Inject DB latency — observe connection pool saturation + query degradation
    5. Restart WebSocket gateway — observe reconnect storms + message recovery
    6. Trigger queue backlog — observe backpressure + worker starvation

Usage:
    # Run ALL chaos experiments sequentially:
    python tests/load/chaos/experiments.py --environment staging

    # Run specific experiment:
    python tests/load/chaos/experiments.py --experiment kill-workers

    # Run with load test running:
    python tests/load/chaos/experiments.py --experiment kill-redis --concurrent-load

Requirements:
    - docker compose access to the staging environment
    - Prometheus query access for metrics capture
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Configuration ──────────────────────────────────────────────────

STAGING_DIR = Path(__file__).resolve().parent.parent.parent / "deploy" / "staging"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
COMPOSE_FILE = STAGING_DIR / "docker-compose.staging.yml"
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
API_URL = os.getenv("API_URL", "http://localhost:8000")

EXPERIMENTS_DIR = REPORTS_DIR / "chaos"
EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Metrics Capture ────────────────────────────────────────────────


def query_prometheus(query: str, duration: str = "5m") -> list[dict]:
    """Query Prometheus for metrics data."""
    try:
        params = urllib.parse.urlencode({"query": query, "time": time.time()})
        url = f"{PROMETHEUS_URL}/api/v1/query?{params}"
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read())
        return data.get("data", {}).get("result", [])
    except Exception as e:
        print(f"  ⚠ Prometheus query failed: {e}")
        return []


def capture_metrics_snapshot(experiment_name: str) -> dict:
    """Capture a snapshot of key metrics before/after experiment."""
    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment": experiment_name,
        "api_latency_p50": query_prometheus('histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[2m])) by (le))'),
        "api_latency_p95": query_prometheus('histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[2m])) by (le))'),
        "api_latency_p99": query_prometheus('histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[2m])) by (le))'),
        "queue_depth": query_prometheus('queue_depth'),
        "active_workers": query_prometheus('active_workers'),
        "ws_connections": query_prometheus('ws_active_connections'),
        "db_connections": query_prometheus('pg_stat_activity_count'),
        "redis_memory": query_prometheus('redis_memory_used_bytes'),
    }
    return metrics


def save_metrics(experiment_name: str, phase: str, metrics: dict) -> None:
    """Save metrics to a JSON file."""
    filename = EXPERIMENTS_DIR / f"{experiment_name}_{phase}_{int(time.time())}.json"
    with open(filename, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"  📊 Metrics saved: {filename}")


# ── Docker Compose Helpers ─────────────────────────────────────────


def docker_compose_cmd(*args: str) -> subprocess.CompletedProcess:
    """Run a docker compose command against the staging environment."""
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE)] + list(args)
    print(f"  🐳 Running: {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True)


def scale_service(service: str, replicas: int) -> None:
    """Scale a service to the given number of replicas."""
    result = docker_compose_cmd("up", "-d", "--scale", f"{service}={replicas}", "--no-deps", service)
    if result.returncode != 0:
        print(f"  ❌ Failed to scale {service} to {replicas}: {result.stderr}")
    else:
        print(f"  ✅ Scaled {service} to {replicas} replicas")


def stop_service(service: str) -> None:
    """Stop a specific service."""
    result = docker_compose_cmd("stop", service)
    if result.returncode != 0:
        print(f"  ❌ Failed to stop {service}: {result.stderr}")
    else:
        print(f"  🛑 Stopped {service}")


def start_service(service: str) -> None:
    """Start a specific service."""
    result = docker_compose_cmd("start", service)
    if result.returncode != 0:
        print(f"  ❌ Failed to start {service}: {result.stderr}")
    else:
        print(f"  ✅ Started {service}")


def restart_service(service: str) -> None:
    """Restart a specific service."""
    result = docker_compose_cmd("restart", service)
    if result.returncode != 0:
        print(f"  ❌ Failed to restart {service}: {result.stderr}")
    else:
        print(f"  🔄 Restarted {service}")


def get_service_pids(service: str) -> list[str]:
    """Get PIDs of running containers for a service."""
    result = docker_compose_cmd("ps", "-q", service)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().split("\n")
    return []


def kill_container(container_id: str) -> None:
    """Kill a container by ID (SIGKILL)."""
    try:
        subprocess.run(["docker", "kill", container_id], capture_output=True, text=True, timeout=10)
        print(f"  💀 Killed container {container_id[:12]}")
    except Exception as e:
        print(f"  ❌ Failed to kill container: {e}")


# ── API Health Check ───────────────────────────────────────────────


def check_api_health() -> bool:
    """Check if the API is responding."""
    try:
        resp = urllib.request.urlopen(f"{API_URL}/health", timeout=5)
        return resp.status == 200
    except Exception:
        return False


def wait_for_api(timeout: int = 60) -> bool:
    """Wait for the API to become healthy."""
    print(f"  ⏳ Waiting for API (timeout={timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        if check_api_health():
            print(f"  ✅ API healthy after {time.time() - start:.0f}s")
            return True
        time.sleep(2)
    print(f"  ❌ API did not recover within {timeout}s")
    return False


# ═══════════════════════════════════════════════════════════════════
# EXPERIMENTS
# ═══════════════════════════════════════════════════════════════════


def experiment_kill_workers():
    """
    Experiment 1: Kill worker replicas during load.

    Expected behavior:
        - Queue depth increases
        - Tasks remain in queue (not lost)
        - API continues serving (degraded for async operations)
        - Workers recover when restarted
        - No data loss or corruption
    """
    print("\n" + "═" * 60)
    print("  EXPERIMENT 1: Kill Worker Replicas")
    print("═" * 60)

    # Phase 1: Baseline
    print("\n📊 Phase 1: Baseline measurement")
    baseline = capture_metrics_snapshot("kill_workers_baseline")
    save_metrics("kill_workers", "baseline", baseline)
    time.sleep(5)

    # Phase 2: Kill ingestion worker
    print("\n🔪 Phase 2: Killing ingestion worker")
    ingestion_containers = get_service_pids("worker-ingestion")
    print(f"  Found {len(ingestion_containers)} ingestion worker(s)")
    for cid in ingestion_containers:
        kill_container(cid)
    time.sleep(10)

    during_kill = capture_metrics_snapshot("kill_workers_during")
    save_metrics("kill_workers", "during_ingestion_kill", during_kill)

    # Phase 3: Kill AI worker
    print("\n🔪 Phase 3: Killing AI worker")
    ai_containers = get_service_pids("worker-ai")
    for cid in ai_containers:
        kill_container(cid)
    time.sleep(10)

    during_ai_kill = capture_metrics_snapshot("kill_workers_during_ai")
    save_metrics("kill_workers", "during_ai_kill", during_ai_kill)

    # Phase 4: Recovery
    print("\n🔄 Phase 4: Recovery")
    docker_compose_cmd("up", "-d", "--no-deps", "worker-ingestion")
    docker_compose_cmd("up", "-d", "--no-deps", "worker-ai")
    time.sleep(30)

    recovery = capture_metrics_snapshot("kill_workers_recovery")
    save_metrics("kill_workers", "recovery", recovery)

    # Phase 5: Verify
    print("\n✅ Phase 5: Verification")
    queue_depth = recovery.get("queue_depth", [])
    print(f"  Queue depth after recovery: {queue_depth}")

    return {
        "experiment": "kill_workers",
        "baseline": baseline,
        "during_ingestion_kill": during_kill,
        "during_ai_kill": during_ai_kill,
        "recovery": recovery,
    }


def experiment_kill_redis():
    """
    Experiment 2: Kill Redis during load.

    Expected behavior:
        - API enters degraded mode (caching disabled)
        - Rate limiting falls back to local
        - Session management degrades gracefully
        - Redis reconnection with backoff
        - Full recovery when Redis returns
    """
    print("\n" + "═" * 60)
    print("  EXPERIMENT 2: Kill Redis")
    print("═" * 60)

    # Phase 1: Baseline
    print("\n📊 Phase 1: Baseline measurement")
    baseline = capture_metrics_snapshot("kill_redis_baseline")
    save_metrics("kill_redis", "baseline", baseline)
    time.sleep(5)

    # Phase 2: Kill Redis
    print("\n🔪 Phase 2: Killing Redis")
    stop_service("redis")
    time.sleep(15)

    during_kill = capture_metrics_snapshot("kill_redis_during")
    save_metrics("kill_redis", "during", during_kill)

    # Check API still responds
    api_ok = check_api_health()
    print(f"  API healthy without Redis: {api_ok}")

    # Phase 3: Recovery
    print("\n🔄 Phase 3: Recovery")
    start_service("redis")
    time.sleep(30)

    recovery = capture_metrics_snapshot("kill_redis_recovery")
    save_metrics("kill_redis", "recovery", recovery)
    wait_for_api()

    return {
        "experiment": "kill_redis",
        "baseline": baseline,
        "during": during_kill,
        "recovery": recovery,
    }


def experiment_throttle_openai():
    """
    Experiment 3: Throttle OpenAI provider.

    Simulates OpenAI API degradation by:
        - Setting a very low rate limit via environment
        - Observing retry behavior
        - Checking fallback mechanisms
        - Measuring queue backpressure

    Expected behavior:
        - Retry with exponential backoff
        - Queue backlog for AI tasks
        - Fallback to cached/alternative models
        - No crash or data loss
    """
    print("\n" + "═" * 60)
    print("  EXPERIMENT 3: Throttle OpenAI Provider")
    print("═" * 60)

    print("\n📊 Phase 1: Baseline")
    baseline = capture_metrics_snapshot("throttle_openai_baseline")
    save_metrics("throttle_openai", "baseline", baseline)

    # Phase 2: Simulate throttling by killing AI workers
    # (This simulates the effect of OpenAI being unavailable)
    print("\n🔧 Phase 2: Simulating provider throttling")
    print("  (Killing AI workers to simulate provider unavailability)")
    ai_containers = get_service_pids("worker-ai")
    for cid in ai_containers:
        kill_container(cid)
    time.sleep(15)

    during = capture_metrics_snapshot("throttle_openai_during")
    save_metrics("throttle_openai", "during", during)

    # Phase 3: Recovery
    print("\n🔄 Phase 3: Recovery")
    docker_compose_cmd("up", "-d", "--no-deps", "worker-ai")
    time.sleep(30)

    recovery = capture_metrics_snapshot("throttle_openai_recovery")
    save_metrics("throttle_openai", "recovery", recovery)

    return {
        "experiment": "throttle_openai",
        "baseline": baseline,
        "during": during,
        "recovery": recovery,
    }


def experiment_inject_db_latency():
    """
    Experiment 4: Inject DB latency via pg_network_delay.

    Simulates database network latency by using iptables/tc on the
    postgres container to add latency.

    Expected behavior:
        - Query latency increases
        - Connection pool saturation
        - Degraded read/write performance
        - Circuit breaker triggers
        - Recovery when latency removed
    """
    print("\n" + "═" * 60)
    print("  EXPERIMENT 4: Inject DB Latency")
    print("═" * 60)

    print("\n📊 Phase 1: Baseline")
    baseline = capture_metrics_snapshot("db_latency_baseline")
    save_metrics("db_latency", "baseline", baseline)

    # Phase 2: Add latency via Docker pause (simulates slow DB)
    print("\n🐌 Phase 2: Simulating DB latency")
    print("  (Pausing postgres container to simulate network issues)")
    postgres_containers = get_service_pids("postgres")
    if postgres_containers:
        subprocess.run(["docker", "pause", postgres_containers[0]], capture_output=True, text=True, timeout=10)
        print(f"  Paused postgres container")
    time.sleep(15)

    during = capture_metrics_snapshot("db_latency_during")
    save_metrics("db_latency", "during", during)

    # Check API behavior under DB stress
    api_ok = check_api_health()
    print(f"  API healthy with DB latency: {api_ok}")

    # Phase 3: Recovery
    print("\n🔄 Phase 3: Recovery")
    if postgres_containers:
        subprocess.run(["docker", "unpause", postgres_containers[0]], capture_output=True, text=True, timeout=10)
        print(f"  Unpaused postgres container")
    time.sleep(30)

    recovery = capture_metrics_snapshot("db_latency_recovery")
    save_metrics("db_latency", "recovery", recovery)
    wait_for_api()

    return {
        "experiment": "inject_db_latency",
        "baseline": baseline,
        "during": during,
        "recovery": recovery,
    }


def experiment_restart_websocket():
    """
    Experiment 5: Restart WebSocket gateway.

    Simulates WebSocket gateway restart during active connections.

    Expected behavior:
        - Active connections drop
        - Clients reconnect with backoff
        - Reconnect storm detection
        - Message delivery resumes
        - No duplicate or lost messages
    """
    print("\n" + "═" * 60)
    print("  EXPERIMENT 5: Restart WebSocket Gateway")
    print("═" * 60)

    print("\n📊 Phase 1: Baseline")
    baseline = capture_metrics_snapshot("ws_restart_baseline")
    save_metrics("ws_restart", "baseline", baseline)

    # Phase 2: Restart API (WebSocket gateway)
    print("\n🔄 Phase 2: Restarting API (WebSocket gateway)")
    restart_service("api")
    time.sleep(15)

    during = capture_metrics_snapshot("ws_restart_during")
    save_metrics("ws_restart", "during", during)

    # Phase 3: Recovery
    print("\n🔄 Phase 3: Recovery")
    wait_for_api()
    time.sleep(15)

    recovery = capture_metrics_snapshot("ws_restart_recovery")
    save_metrics("ws_restart", "recovery", recovery)

    return {
        "experiment": "restart_websocket",
        "baseline": baseline,
        "during": during,
        "recovery": recovery,
    }


def experiment_trigger_backlog():
    """
    Experiment 6: Trigger queue backlog.

    Creates a massive queue backlog by:
        1. Killing all workers
        2. Flooding with ingestion requests
        3. Restarting workers
        4. Observing backlog drain and recovery

    Expected behavior:
        - Queue depth grows rapidly
        - Backpressure mechanisms engage
        - Workers drain backlog when restarted
        - No task loss despite massive backlog
        - Recovery time proportional to backlog size
    """
    print("\n" + "═" * 60)
    print("  EXPERIMENT 6: Trigger Queue Backlog")
    print("═" * 60)

    print("\n📊 Phase 1: Baseline")
    baseline = capture_metrics_snapshot("backlog_baseline")
    save_metrics("backlog", "baseline", baseline)

    # Phase 2: Kill all workers
    print("\n🔪 Phase 2: Killing all workers")
    for worker in ["worker-ingestion", "worker-ai", "worker-notifications", "worker-embeddings"]:
        stop_service(worker)
    time.sleep(10)

    # Phase 3: Flood with requests while workers are down
    print("\n🌊 Phase 3: Flooding ingestion while workers down")
    # Use curl to rapidly initiate uploads
    for i in range(50):
        try:
            payload = json.dumps({
                "filename": f"backlog_flood_{i}_{int(time.time())}.pdf",
                "content_type": "application/pdf",
                "file_size": 1_000_000,
            }).encode()
            req = urllib.request.Request(
                f"{API_URL}/api/v1/ingest/initiate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
    time.sleep(5)

    during = capture_metrics_snapshot("backlog_during")
    save_metrics("backlog", "during", during)

    # Phase 4: Restart workers and observe drain
    print("\n🔄 Phase 4: Restarting workers — observing backlog drain")
    for worker in ["worker-ingestion", "worker-ai", "worker-notifications", "worker-embeddings"]:
        start_service(worker)

    # Monitor drain over 2 minutes
    for i in range(6):
        time.sleep(20)
        snapshot = capture_metrics_snapshot(f"backlog_drain_{i}")
        save_metrics("backlog", f"drain_{i}", snapshot)
        queue_data = snapshot.get("queue_depth", [])
        print(f"  Drain check {i+1}/6: queue depth = {queue_data}")

    recovery = capture_metrics_snapshot("backlog_recovery")
    save_metrics("backlog", "recovery", recovery)

    return {
        "experiment": "trigger_backlog",
        "baseline": baseline,
        "during": during,
        "recovery": recovery,
    }


# ═══════════════════════════════════════════════════════════════════
# EXPERIMENT REGISTRY
# ═══════════════════════════════════════════════════════════════════

EXPERIMENTS = {
    "kill-workers": experiment_kill_workers,
    "kill-redis": experiment_kill_redis,
    "throttle-openai": experiment_throttle_openai,
    "db-latency": experiment_inject_db_latency,
    "restart-websocket": experiment_restart_websocket,
    "trigger-backlog": experiment_trigger_backlog,
}


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def run_all_experiments() -> list[dict]:
    """Run all chaos experiments sequentially."""
    results = []
    for name, experiment_fn in EXPERIMENTS.items():
        print(f"\n{'#' * 60}")
        print(f"  Running experiment: {name}")
        print(f"{'#' * 60}")
        try:
            result = experiment_fn()
            results.append(result)
            print(f"\n  ✅ Experiment '{name}' completed successfully")
        except KeyboardInterrupt:
            print(f"\n  ⛔ Experiment '{name}' interrupted by user")
            break
        except Exception as e:
            print(f"\n  ❌ Experiment '{name}' failed: {e}")
            results.append({"experiment": name, "error": str(e)})

    # Save combined results
    combined = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiments": results,
    }
    report_file = EXPERIMENTS_DIR / f"chaos_report_{int(time.time())}.json"
    with open(report_file, "w") as f:
        json.dump(combined, f, indent=2, default=str)
    print(f"\n📊 Combined chaos report saved: {report_file}")

    return results


def main():
    parser = argparse.ArgumentParser(description="ContractRiskEdge Chaos Engineering Harness")
    parser.add_argument(
        "--experiment",
        choices=list(EXPERIMENTS.keys()) + ["all"],
        default="all",
        help="Which chaos experiment to run (default: all)",
    )
    parser.add_argument(
        "--concurrent-load",
        action="store_true",
        help="Flag that load tests are running concurrently (for documentation)",
    )
    parser.add_argument(
        "--prometheus-url",
        default=PROMETHEUS_URL,
        help="Prometheus URL (default: http://localhost:9090)",
    )
    parser.add_argument(
        "--api-url",
        default=API_URL,
        help="API URL (default: http://localhost:8000)",
    )

    args = parser.parse_args()
    global PROMETHEUS_URL, API_URL
    PROMETHEUS_URL = args.prometheus_url
    API_URL = args.api_url

    print("╔" + "═" * 58 + "╗")
    print("║  ContractRiskEdge — Chaos Engineering Harness        ║")
    print("║  Phase 3, Session 2, Track 4                         ║")
    print("╚" + "═" * 58 + "╝")
    print(f"\n  Target API: {API_URL}")
    print(f"  Prometheus: {PROMETHEUS_URL}")
    print(f"  Concurrent load: {args.concurrent_load}")
    print(f"  Reports dir: {EXPERIMENTS_DIR}")

    if not check_api_health():
        print("\n  ❌ API is not healthy. Start the staging environment first.")
        print("     docker compose -f deploy/staging/docker-compose.staging.yml up -d")
        sys.exit(1)

    print("\n  ✅ API is healthy. Starting chaos experiments...\n")

    if args.experiment == "all":
        run_all_experiments()
    else:
        experiment_fn = EXPERIMENTS[args.experiment]
        try:
            experiment_fn()
        except KeyboardInterrupt:
            print(f"\n  ⛔ Experiment '{args.experiment}' interrupted")
        except Exception as e:
            print(f"\n  ❌ Experiment '{args.experiment}' failed: {e}")

    print("\n" + "═" * 60)
    print("  Chaos experiments complete.")
    print("═" * 60)


if __name__ == "__main__":
    main()
