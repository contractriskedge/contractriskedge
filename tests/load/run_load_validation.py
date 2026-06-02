#!/usr/bin/env python3
"""
ContractRiskEdge — Automated Load Validation Runner (Phase 3, Session 2).

Orchestrates the complete load validation workflow:

    1. Verify staging environment is healthy
    2. Seed synthetic tenant data
    3. Run Track 1: Sustained Load (1hr)
    4. Run Track 2: Burst Load (5min)
    5. Run Track 3: Ingestion Flood (10min)
    6. Run Track 4: WebSocket Storm (5min)
    7. Run Track 5: Multi-Tenant Isolation (10min)
    8. Run Track 6: Executive Dashboard Pressure (10min)
    9. Run Chaos Experiments (with concurrent load)
    10. Generate load_validation_report.md

Usage:
    python tests/load/run_load_validation.py \
        --api-url http://localhost:8000 \
        --prometheus-url http://localhost:9090 \
        --output tests/load/reports/load_validation_report.md

    # Skip specific tracks:
    python tests/load/run_load_validation.py --skip-sustained --skip-chaos
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Configuration ──────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOCUSTFILE = REPO_ROOT / "tests" / "load" / "locustfile.py"
CHAOS_SCRIPT = REPO_ROOT / "tests" / "load" / "chaos" / "experiments.py"
SEED_SCRIPT = REPO_ROOT / "tests" / "load" / "seed" / "generate_seed_data.py"
REPORTS_DIR = REPO_ROOT / "tests" / "load" / "reports"
COMPOSE_FILE = REPO_ROOT / "deploy" / "staging" / "docker-compose.staging.yml"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_PROMETHEUS_URL = "http://localhost:9090"


# ── Helpers ────────────────────────────────────────────────────────


def check_api(url: str) -> bool:
    """Check if the API is healthy."""
    try:
        resp = urllib.request.urlopen(f"{url}/health", timeout=10)
        return resp.status == 200
    except Exception:
        return False


def wait_for_api(url: str, timeout: int = 60) -> bool:
    """Wait for API to become healthy."""
    print(f"  ⏳ Waiting for API at {url} (timeout={timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        if check_api(url):
            print(f"  ✅ API healthy after {time.time() - start:.0f}s")
            return True
        time.sleep(2)
    print(f"  ❌ API did not recover within {timeout}s")
    return False


def run_locust(
    user_class: str,
    users: int,
    spawn_rate: int,
    run_time: int,
    api_url: str,
    csv_prefix: str,
    host: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a Locust test headless and return the process."""
    cmd = [
        "locust", "-f", str(LOCUSTFILE),
        f"--host={host or api_url}",
        f"--users={users}",
        f"--spawn-rate={spawn_rate}",
        f"--run-time={run_time}s",
        "--headless",
        "--only-summary",
        "--csv", str(REPORTS_DIR / csv_prefix),
        "--csv-full-history",
    ]
    if user_class:
        cmd.extend([user_class])

    print(f"\n  🦗 Running: {' '.join(cmd)}")
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=run_time + 120)
    elapsed = time.time() - start

    print(f"  ✅ Completed in {elapsed:.0f}s")
    print(f"     stdout: {result.stdout[-500:]}" if result.stdout else "")
    if result.stderr:
        print(f"     stderr: {result.stderr[-500:]}")

    return result


def run_chaos_experiment(
    experiment: str,
    api_url: str,
    prometheus_url: str,
) -> subprocess.CompletedProcess:
    """Run a chaos engineering experiment."""
    cmd = [
        sys.executable, str(CHAOS_SCRIPT),
        f"--experiment={experiment}",
        f"--api-url={api_url}",
        f"--prometheus-url={prometheus_url}",
    ]
    print(f"\n  💥 Running chaos: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    print(result.stdout[-1000:] if result.stdout else "")
    return result


def seed_data(api_url: str) -> subprocess.CompletedProcess:
    """Seed synthetic data into the staging database."""
    # Generate seed SQL and pipe to postgres
    seed_sql = REPORTS_DIR / "seed_data_generated.sql"
    cmd = [
        sys.executable, str(SEED_SCRIPT),
        "--output", str(seed_sql),
    ]
    print(f"\n  🌱 Generating seed data: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    print(result.stdout)

    if result.returncode != 0:
        print(f"  ❌ Seed generation failed: {result.stderr}")
        return result

    # Execute seed SQL via docker compose
    print(f"\n  🌱 Executing seed SQL via docker compose...")
    docker_cmd = [
        "docker", "compose", "-f", str(COMPOSE_FILE),
        "exec", "-T", "postgres",
        "psql", "-U", "staging_user", "-d", "contract_risk_staging",
    ]
    with open(seed_sql) as f:
        seed_content = f.read()

    result = subprocess.run(
        docker_cmd,
        input=seed_content,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode == 0:
        print(f"  ✅ Seed data inserted successfully")
    else:
        print(f"  ⚠ Seed data insertion had issues: {result.stderr[-500:]}")

    return result


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ContractRiskEdge — Automated Load Validation Runner"
    )
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--prometheus-url", default=DEFAULT_PROMETHEUS_URL)
    parser.add_argument("--output", default=str(REPORTS_DIR / "load_validation_report.md"))
    parser.add_argument("--skip-sustained", action="store_true")
    parser.add_argument("--skip-burst", action="store_true")
    parser.add_argument("--skip-flood", action="store_true")
    parser.add_argument("--skip-websocket", action="store_true")
    parser.add_argument("--skip-multitenant", action="store_true")
    parser.add_argument("--skip-dashboard", action="store_true")
    parser.add_argument("--skip-chaos", action="store_true")
    parser.add_argument("--skip-seed", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without executing")

    args = parser.parse_args()

    print("╔" + "═" * 62 + "╗")
    print("║  ContractRiskEdge — Load Validation Runner              ║")
    print("║  Phase 3, Session 2                                     ║")
    print("╚" + "═" * 62 + "╝")
    print(f"\n  API URL:      {args.api_url}")
    print(f"  Prometheus:   {args.prometheus_url}")
    print(f"  Output:       {args.output}")
    print(f"  Dry run:      {args.dry_run}")
    print()

    if args.dry_run:
        print("  🏁 DRY RUN MODE — No tests will be executed\n")

    # ── Step 0: Verify staging environment ────────────────────────
    print("─" * 60)
    print("  STEP 0: Verify staging environment")
    print("─" * 60)

    if not args.dry_run:
        if not check_api(args.api_url):
            print(f"\n  ❌ API is not healthy at {args.api_url}")
            print("     Start the staging environment first:")
            print(f"     docker compose -f {COMPOSE_FILE} up -d")
            sys.exit(1)
        print("  ✅ Staging environment is healthy\n")
    else:
        print("  [DRY RUN] Would check API health\n")

    # ── Step 0.5: Seed data ───────────────────────────────────────
    if not args.skip_seed:
        print("─" * 60)
        print("  STEP 0.5: Seed synthetic tenant data")
        print("─" * 60)
        if not args.dry_run:
            seed_data(args.api_url)
        else:
            print("  [DRY RUN] Would generate and insert seed data\n")

    # ── Step 1: Sustained Load ────────────────────────────────────
    if not args.skip_sustained:
        print("\n" + "═" * 60)
        print("  TRACK 1: Sustained Load (1 hour)")
        print("═" * 60)
        if not args.dry_run:
            run_locust(
                user_class="SustainedLoadUser",
                users=200,
                spawn_rate=10,
                run_time=3600,
                api_url=args.api_url,
                csv_prefix="sustained_load",
            )
        else:
            print("  [DRY RUN] Would run sustained load for 3600s\n")

    # ── Step 2: Burst Load ────────────────────────────────────────
    if not args.skip_burst:
        print("\n" + "═" * 60)
        print("  TRACK 2: Burst Load (10x spike)")
        print("═" * 60)
        if not args.dry_run:
            run_locust(
                user_class="BurstLoadUser",
                users=200,
                spawn_rate=50,
                run_time=300,
                api_url=args.api_url,
                csv_prefix="burst_load",
            )
        else:
            print("  [DRY RUN] Would run burst load for 300s\n")

    # ── Step 3: Ingestion Flood ───────────────────────────────────
    if not args.skip_flood:
        print("\n" + "═" * 60)
        print("  TRACK 3: Ingestion Flood")
        print("═" * 60)
        if not args.dry_run:
            run_locust(
                user_class="IngestionFloodUser",
                users=30,
                spawn_rate=5,
                run_time=600,
                api_url=args.api_url,
                csv_prefix="ingestion_flood",
            )
        else:
            print("  [DRY RUN] Would run ingestion flood for 600s\n")

    # ── Step 4: WebSocket Storm ───────────────────────────────────
    if not args.skip_websocket:
        print("\n" + "═" * 60)
        print("  TRACK 4: WebSocket Storm")
        print("═" * 60)
        if not args.dry_run:
            run_locust(
                user_class="WebSocketStormUser",
                users=100,
                spawn_rate=20,
                run_time=300,
                api_url=args.api_url,
                csv_prefix="websocket_storm",
            )
        else:
            print("  [DRY RUN] Would run WebSocket storm for 300s\n")

    # ── Step 5: Multi-Tenant Isolation ─────────────────────────────
    if not args.skip_multitenant:
        print("\n" + "═" * 60)
        print("  TRACK 5: Multi-Tenant Isolation Stress")
        print("═" * 60)
        if not args.dry_run:
            run_locust(
                user_class="MultiTenantUser",
                users=200,
                spawn_rate=20,
                run_time=600,
                api_url=args.api_url,
                csv_prefix="multi_tenant",
            )
        else:
            print("  [DRY RUN] Would run multi-tenant stress for 600s\n")

    # ── Step 6: Executive Dashboard Pressure ──────────────────────
    if not args.skip_dashboard:
        print("\n" + "═" * 60)
        print("  TRACK 6: Executive Dashboard Pressure")
        print("═" * 60)
        if not args.dry_run:
            run_locust(
                user_class="ExecutiveDashboardPressureUser",
                users=50,
                spawn_rate=10,
                run_time=600,
                api_url=args.api_url,
                csv_prefix="dashboard_pressure",
            )
        else:
            print("  [DRY RUN] Would run dashboard pressure for 600s\n")

    # ── Step 7: Chaos Experiments ─────────────────────────────────
    if not args.skip_chaos:
        print("\n" + "═" * 60)
        print("  TRACK 4 (Chaos): Failure Characterization")
        print("═" * 60)

        # Start background load during chaos
        experiments = [
            "kill-workers",
            "kill-redis",
            "throttle-openai",
            "db-latency",
            "restart-websocket",
            "trigger-backlog",
        ]

        for exp in experiments:
            print(f"\n  ── Experiment: {exp} ──")
            if not args.dry_run:
                run_chaos_experiment(exp, args.api_url, args.prometheus_url)
            else:
                print(f"  [DRY RUN] Would run chaos experiment: {exp}")

    # ── Step 8: Generate Report ───────────────────────────────────
    print("\n" + "═" * 60)
    print("  GENERATING LOAD VALIDATION REPORT")
    print("═" * 60)

    if not args.dry_run:
        # Copy template and add metadata
        template_path = REPORTS_DIR / "load_validation_report_template.md"
        if template_path.exists():
            with open(template_path) as f:
                template = f.read()

            report = template.replace("{{DATE}}", datetime.now(timezone.utc).isoformat())
            report = report.replace("{{TEST_DURATION}}", "See individual tracks")
            report = report.replace("{{TOTAL_USERS}}", "Varies by track (30-200)")

            output_path = Path(args.output)
            with open(output_path, "w") as f:
                f.write(report)
            print(f"  ✅ Report template written: {output_path}")
        else:
            print(f"  ⚠ Template not found: {template_path}")
    else:
        print("  [DRY RUN] Would generate report\n")

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  LOAD VALIDATION COMPLETE")
    print("═" * 60)
    print(f"\n  CSV results: {REPORTS_DIR}/")
    print(f"  Chaos results: {REPORTS_DIR / 'chaos'}/")
    print(f"  Grafana dashboards: deploy/observability/grafana/dashboards/contractriskedge/load-testing/")
    print(f"\n  Next steps:")
    print(f"    1. Review CSV files for detailed latency distributions")
    print(f"    2. Check Grafana dashboards for visual analysis")
    print(f"    3. Populate load_validation_report.md with actual measurements")
    print(f"    4. Address identified bottlenecks before onboarding wizard")
    print()


if __name__ == "__main__":
    main()
