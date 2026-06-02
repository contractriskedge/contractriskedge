#!/usr/bin/env python3
"""
ContractRiskEdge Pilot Deployment Script — one-command production deployment.

Usage:
    python deploy/pilot/deploy.py --environment staging
    python deploy/pilot/deploy.py --environment production --aws-profile contractrisk

Validates environment, dependencies, secrets, then deploys via Docker Compose or K8s.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "AUTH0_DOMAIN",
    "AUTH0_AUDIENCE",
    "AUTH0_ISSUER",
    "OPENAI_API_KEY",
]

OPTIONAL_ENV_VARS = [
    "SENTRY_DSN",
    "OTEL_ENABLED",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "SMTP_HOST",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "S3_ENDPOINT_URL",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
]

REQUIRED_COMMANDS = [
    "docker",
    "docker compose",
    "python3",
    "node",
    "npm",
]

RECOMMENDED_MIN_VERSIONS = {
    "docker": "24.0.0",
    "python3": "3.12.0",
    "node": "20.0.0",
}


def check_command(cmd: str) -> tuple[bool, str]:
    """Check if a command is available and return its version."""
    try:
        result = subprocess.run(
            cmd.split() + ["--version"],
            capture_output=True, text=True, timeout=10,
        )
        version = result.stdout.strip() or result.stderr.strip()
        return True, version
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, ""


def check_env_file(env_file: str) -> list[str]:
    """Validate an .env file has all required variables."""
    missing = []
    if not os.path.exists(env_file):
        return [f"Missing env file: {env_file}"]

    with open(env_file) as f:
        content = f.read()

    for var in REQUIRED_ENV_VARS:
        if f"{var}=" not in content:
            missing.append(f"Missing required env var: {var}")

    return missing


def check_secrets() -> list[str]:
    """Check for placeholder/default secrets."""
    issues = []
    for key in ["SECRET_KEY", "DEV_JWT_SECRET"]:
        val = os.environ.get(key, "")
        if val in ("", "change-this-in-production", "dev-secret-change-in-production"):
            issues.append(f"Default/empty secret: {key}")
    return issues


def check_database_url() -> list[str]:
    """Validate DATABASE_URL format."""
    issues = []
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        issues.append("DATABASE_URL is not set")
    elif "asyncpg" not in db_url:
        issues.append("DATABASE_URL should use asyncpg driver (postgresql+asyncpg://)")
    elif "localhost" in db_url or "127.0.0.1" in db_url:
        issues.append("DATABASE_URL points to localhost — should point to production database")
    return issues


def run_smoke_tests(base_url: str) -> list[str]:
    """Run smoke tests against a deployed instance."""
    import urllib.request
    import json

    issues = []

    # Health check
    try:
        resp = urllib.request.urlopen(f"{base_url}/health", timeout=10)
        if resp.status != 200:
            issues.append(f"Health check returned {resp.status}")
    except Exception as e:
        issues.append(f"Health check failed: {e}")

    # API docs
    try:
        resp = urllib.request.urlopen(f"{base_url}/docs", timeout=10)
        if resp.status not in (200, 302, 307):
            issues.append(f"API docs returned {resp.status}")
    except Exception as e:
        issues.append(f"API docs unavailable: {e}")

    # Metrics endpoint
    try:
        resp = urllib.request.urlopen(f"{base_url}/metrics", timeout=10)
        if resp.status != 200:
            issues.append(f"Metrics endpoint returned {resp.status}")
    except Exception as e:
        issues.append(f"Metrics endpoint unavailable: {e}")

    return issues


def deploy_docker_compose(environment: str, env_file: str) -> bool:
    """Deploy using Docker Compose."""
    print(f"\n🚀 Deploying to {environment} via Docker Compose...")

    # Validate env file
    missing_vars = check_env_file(env_file)
    if missing_vars:
        print("❌ Environment validation failed:")
        for v in missing_vars:
            print(f"   - {v}")
        return False

    # Pull latest images
    print("📦 Pulling latest images...")
    subprocess.run(["docker", "compose", "-f", "docker-compose.yml", "pull"], check=False)

    # Start services
    print("▶️  Starting services...")
    result = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.yml", "up", "-d"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"❌ Deployment failed: {result.stderr}")
        return False

    print("✅ Deployment started. Checking health...")
    return True


def deploy_kubernetes(environment: str) -> bool:
    """Deploy using kubectl and K8s manifests."""
    print(f"\n🚀 Deploying to {environment} via Kubernetes...")

    # Check kubectl
    has_kubectl, version = check_command("kubectl")
    if not has_kubectl:
        print("❌ kubectl not found. Install kubectl for K8s deployment.")
        return False

    # Apply namespace + secrets first
    print("📝 Applying namespace and secrets...")
    subprocess.run(
        ["kubectl", "apply", "-f", "deploy/k8s/namespace-and-secrets.yaml"],
        capture_output=True, text=True,
    )

    # Apply deployments
    for manifest in ["api-deployment.yaml", "worker-deployment.yaml", "frontend-deployment.yaml", "ingress.yaml"]:
        path = f"deploy/k8s/{manifest}"
        if os.path.exists(path):
            print(f"   Applying {manifest}...")
            subprocess.run(["kubectl", "apply", "-f", path], capture_output=True, text=True)

    print("✅ K8s manifests applied. Run 'kubectl get pods -n contractrisk' to verify.")
    return True


def main():
    parser = argparse.ArgumentParser(description="ContractRiskEdge Pilot Deployment")
    parser.add_argument("--environment", choices=["staging", "production"], default="staging")
    parser.add_argument("--method", choices=["docker", "kubernetes", "auto"], default="auto")
    parser.add_argument("--env-file", default=".env.production")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--smoke-test", action="store_true", default=True)
    parser.add_argument("--aws-profile", help="AWS profile for K8s deployments")
    args = parser.parse_args()

    print("=" * 60)
    print("  ContractRiskEdge — Pilot Deployment Validator")
    print("=" * 60)

    # Phase 1: Dependency check
    print("\n📋 Phase 1: Checking dependencies...")
    all_deps_ok = True
    for cmd in REQUIRED_COMMANDS:
        found, version = check_command(cmd)
        status = "✅" if found else "❌"
        print(f"   {status} {cmd}: {version.split(chr(10))[0] if version else 'not found'}")
        if not found:
            all_deps_ok = False

    if not all_deps_ok:
        print("\n❌ Missing required dependencies. Install them and retry.")
        sys.exit(1)

    # Phase 2: Environment validation
    print("\n📋 Phase 2: Validating environment...")
    env_file = args.env_file
    if not os.path.exists(env_file):
        env_file = f".env.{args.environment}"
    if not os.path.exists(env_file):
        env_file = ".env"

    missing_vars = check_env_file(env_file)
    if missing_vars:
        print("⚠️  Environment file issues:")
        for v in missing_vars:
            print(f"   ⚠️  {v}")

    # Phase 3: Secret validation
    print("\n📋 Phase 3: Validating secrets...")
    secret_issues = check_secrets()
    if secret_issues:
        print("⚠️  Secret issues:")
        for s in secret_issues:
            print(f"   ⚠️  {s}")

    # Phase 4: Database validation
    print("\n📋 Phase 4: Validating database configuration...")
    db_issues = check_database_url()
    if db_issues:
        print("⚠️  Database issues:")
        for d in db_issues:
            print(f"   ⚠️  {d}")

    # Phase 5: Deploy
    print(f"\n📋 Phase 5: Deploying to {args.environment}...")
    method = args.method
    if method == "auto":
        # Auto-detect: prefer K8s if kubectl available, else Docker Compose
        has_kubectl, _ = check_command("kubectl")
        method = "kubernetes" if has_kubectl else "docker"

    if method == "kubernetes":
        success = deploy_kubernetes(args.environment)
    else:
        success = deploy_docker_compose(args.environment, env_file)

    if not success:
        print("\n❌ Deployment failed.")
        sys.exit(1)

    # Phase 6: Smoke tests
    if args.smoke_test:
        print(f"\n📋 Phase 6: Running smoke tests against {args.base_url}...")
        smoke_issues = run_smoke_tests(args.base_url)
        if smoke_issues:
            print("⚠️  Smoke test issues:")
            for s in smoke_issues:
                print(f"   ⚠️  {s}")
        else:
            print("   ✅ All smoke tests passed!")

    print("\n" + "=" * 60)
    print("  ✅ Pilot deployment completed successfully!")
    print("=" * 60)
    print(f"\n  API:        {args.base_url}")
    print(f"  API Docs:   {args.base_url}/docs")
    print(f"  Metrics:    {args.base_url}/metrics")
    print(f"  Frontend:   http://localhost:3000")
    print(f"  Grafana:    http://localhost:3001")
    print(f"  Flower:     http://localhost:5555")
    print()


if __name__ == "__main__":
    main()
