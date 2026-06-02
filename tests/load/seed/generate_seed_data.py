#!/usr/bin/env python3
"""
ContractRiskEdge — Synthetic Seed Data Generator for Load Testing.

Generates realistic tenant data for load validation:
    - 1000+ contracts with varied metadata
    - 50+ concurrent workflow instances
    - 100k+ embeddings (vector data)
    - Replay history
    - Alert history
    - Telemetry history

Usage:
    # Generate all seed data as SQL:
    python tests/load/seed/generate_seed_data.py --output deploy/staging/infra/seed_data.sql

    # Generate and pipe directly to staging DB:
    python tests/load/seed/generate_seed_data.py | docker compose -f deploy/staging/docker-compose.staging.yml exec -T postgres psql -U staging_user -d contract_risk_staging
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterator


# ── Configuration ──────────────────────────────────────────────────

NUM_TENANTS = 25
CONTRACTS_PER_TENANT = 50  # 25 * 50 = 1250 contracts
WORKFLOWS_PER_TENANT = 5   # 25 * 5 = 125 workflows
EMBEDDINGS_PER_CONTRACT = 80  # 1250 * 80 = 100k embeddings
ALERTS_PER_TENANT = 20
REPLAY_EVENTS_PER_TENANT = 200
TELEMETRY_POINTS_PER_TENANT = 500

START_DATE = datetime(2024, 6, 1, tzinfo=timezone.utc)
NOW = datetime(2026, 5, 27, tzinfo=timezone.utc)

CONTRACT_TYPES = [
    "MSA", "SaaS", "License", "SOW", "NDA", "Employment",
    "Distribution", "Partnership", "Service", "Procurement",
    "Lease", "Insurance", "Indemnity", "Addendum", "Amendment",
]

CONTRACT_STATUSES = ["active", "active", "active", "expiring_soon", "expired", "draft", "negotiation"]
CONTRACT_RISK_LEVELS = ["low", "low", "medium", "medium", "high", "critical"]

CLAUSE_TYPES = [
    "indemnification", "liability_cap", "termination", "confidentiality",
    "data_privacy", "force_majeure", "sla", "payment_terms",
    "insurance", "audit_rights", "assignment", "governing_law",
    "arbitration", "non_compete", "exclusivity", "renewal",
]

WORKFLOW_TYPES = [
    "review", "approval", "renewal", "amendment", "audit",
    "compliance_check", "vendor_onboarding", "risk_assessment",
]

WORKFLOW_STATUSES = ["running", "running", "running", "paused", "completed", "failed"]

ALERT_SEVERITIES = ["info", "warning", "warning", "critical"]
ALERT_CATEGORIES = [
    "renewal_overdue", "sla_breach", "risk_threshold", "compliance_violation",
    "expiration_warning", "anomaly_detected", "provider_throttled",
    "queue_backlog", "worker_starvation", "db_connection_exhaustion",
]


# ── Generators ─────────────────────────────────────────────────────


def tenant_id(index: int) -> str:
    return f"tenant_{index:04d}"


def sql_str(s: str) -> str:
    """Escape string for SQL."""
    return "'" + s.replace("'", "''") + "'"


def generate_tenants() -> Iterator[str]:
    """Generate tenant records."""
    for i in range(NUM_TENANTS):
        tid = tenant_id(i)
        name = f"Load Test Tenant {i}"
        yield (
            f"INSERT INTO tenants (id, name, slug, plan, status, created_at, updated_at) "
            f"VALUES ({sql_str(tid)}, {sql_str(name)}, {sql_str(f'load-test-{i}')}, "
            f"'enterprise', 'active', "
            f"{sql_str((START_DATE + timedelta(days=random.randint(0, 365))).isoformat())}, "
            f"{sql_str(NOW.isoformat())}) "
            f"ON CONFLICT (id) DO NOTHING;"
        )


def generate_contracts() -> Iterator[str]:
    """Generate contract records with varied metadata."""
    for t in range(NUM_TENANTS):
        tid = tenant_id(t)
        for c in range(CONTRACTS_PER_TENANT):
            cid = f"contract_{t:04d}_{c:04d}"
            name = random.choice([
                "Master Service Agreement", "Software License", "Cloud Services",
                "Professional Services", "Distribution Agreement", "Partnership Agreement",
                "Non-Disclosure Agreement", "Employment Contract", "Procurement Contract",
                "Insurance Policy", "Lease Agreement", "Service Level Agreement",
            ])
            if c % 5 == 0:
                name += f" v{random.randint(2, 5)}"
            vendor = random.choice([
                "Acme Corp", "Neon Systems", "CloudScale Inc", "DataVault LLC",
                "GlobalTech Partners", "InnoSoft Solutions", "PrimeVendor Co",
                "Strategic Systems", "Enterprise Cloud", "NextGen Services",
            ])
            counterparty = random.choice([
                "Customer A", "Customer B", "Partner X", "Partner Y",
                "Vendor Alpha", "Vendor Beta", "Supplier Gamma", "Supplier Delta",
            ])
            contract_type = random.choice(CONTRACT_TYPES)
            status = random.choice(CONTRACT_STATUSES)
            risk_level = random.choice(CONTRACT_RISK_LEVELS)
            value = random.randint(10000, 5000000)
            currency = random.choice(["USD", "EUR", "GBP", "CAD"])
            created = START_DATE + timedelta(days=random.randint(0, 700))
            effective = created + timedelta(days=random.randint(0, 30))
            expiry = effective + timedelta(days=random.choice([180, 365, 730, 1095, 1460]))
            updated = min(expiry, NOW) - timedelta(days=random.randint(0, 30))

            metadata_json = json.dumps({"source": "load-test-seed", "batch": c // 50})
            yield (
                f"INSERT INTO contracts (id, tenant_id, title, contract_type, vendor_name, "
                f"counterparty_name, status, risk_level, contract_value, currency, "
                f"execution_date, effective_date, expiration_date, auto_renewal, "
                f"description, metadata, created_at, updated_at) "
                f"VALUES ({sql_str(cid)}, {sql_str(tid)}, {sql_str(name)}, "
                f"{sql_str(contract_type)}, {sql_str(vendor)}, {sql_str(counterparty)}, "
                f"{sql_str(status)}, {sql_str(risk_level)}, {value}, {sql_str(currency)}, "
                f"{sql_str(created.isoformat())}, {sql_str(effective.isoformat())}, "
                f"{sql_str(expiry.isoformat())}, {random.choice(['true', 'false'])}, "
                f"{sql_str(f'Load test contract #{c} for tenant {t}')}, "
                f"{sql_str(metadata_json)}, "
                f"{sql_str(created.isoformat())}, {sql_str(updated.isoformat())}) "
                f"ON CONFLICT (id) DO NOTHING;"
            )


def generate_embeddings() -> Iterator[str]:
    """Generate vector embedding records (100k+)."""
    dim = 1536  # OpenAI text-embedding-3-small dimension
    vec_template = "[" + ",".join([f"{random.random():.6f}" for _ in range(dim)]) + "]"

    for t in range(NUM_TENANTS):
        tid = tenant_id(t)
        for c in range(CONTRACTS_PER_TENANT):
            cid = f"contract_{t:04d}_{c:04d}"
            for e in range(EMBEDDINGS_PER_CONTRACT):
                eid = f"emb_{t:04d}_{c:04d}_{e:04d}"
                chunk_index = e
                chunk_text = f"Sample contract text chunk {e} for contract {cid}. " * 5
                model = "text-embedding-3-small"
                yield (
                    f"INSERT INTO embeddings (id, contract_id, tenant_id, chunk_index, "
                    f"chunk_text, embedding, model_name, created_at) "
                    f"VALUES ({sql_str(eid)}, {sql_str(cid)}, {sql_str(tid)}, "
                    f"{chunk_index}, {sql_str(chunk_text[:500])}, "
                    f"'{vec_template}'::vector, "
                    f"{sql_str(model)}, {sql_str(NOW.isoformat())}) "
                    f"ON CONFLICT (id) DO NOTHING;"
                )


def generate_workflows() -> Iterator[str]:
    """Generate workflow instances."""
    for t in range(NUM_TENANTS):
        tid = tenant_id(t)
        for w in range(WORKFLOWS_PER_TENANT):
            wid = f"wf_{t:04d}_{w:04d}"
            wf_type = random.choice(WORKFLOW_TYPES)
            status = random.choice(WORKFLOW_STATUSES)
            cid = f"contract_{t:04d}_{random.randint(0, CONTRACTS_PER_TENANT-1):04d}"
            created = START_DATE + timedelta(days=random.randint(0, 700))
            updated = min(created + timedelta(days=random.randint(1, 90)), NOW)
            _step = random.choice(["init", "review", "approve", "complete"])
            _priority = random.choice([1, 2, 3])
            _retries = random.randint(0, 3)
            state_json = json.dumps({"step": _step, "retries": _retries})

            yield (
                f"INSERT INTO workflows (id, tenant_id, contract_id, workflow_type, "
                f"status, state, priority, created_at, updated_at) "
                f"VALUES ({sql_str(wid)}, {sql_str(tid)}, {sql_str(cid)}, "
                f"{sql_str(wf_type)}, {sql_str(status)}, "
                f"{sql_str(state_json)}, "
                f"{_priority}, "
                f"{sql_str(created.isoformat())}, {sql_str(updated.isoformat())}) "
                f"ON CONFLICT (id) DO NOTHING;"
            )


def generate_alerts() -> Iterator[str]:
    """Generate alert history."""
    for t in range(NUM_TENANTS):
        tid = tenant_id(t)
        for a in range(ALERTS_PER_TENANT):
            aid = f"alert_{t:04d}_{a:04d}"
            severity = random.choice(ALERT_SEVERITIES)
            category = random.choice(ALERT_CATEGORIES)
            cid = f"contract_{t:04d}_{random.randint(0, CONTRACTS_PER_TENANT-1):04d}"
            created = START_DATE + timedelta(days=random.randint(0, 700))
            resolved = created + timedelta(hours=random.randint(1, 168)) if random.random() > 0.3 else None

            alert_title = f"{category.replace('_', ' ').title()} Detected"
            yield (
                f"INSERT INTO alerts (id, tenant_id, contract_id, severity, category, "
                f"title, description, status, created_at, resolved_at) "
                f"VALUES ({sql_str(aid)}, {sql_str(tid)}, {sql_str(cid)}, "
                f"{sql_str(severity)}, {sql_str(category)}, "
                f"{sql_str(alert_title)}, "
                f"{sql_str(f'Load test alert #{a} for tenant {t}')}, "
                f"{sql_str('resolved' if resolved else 'active')}, "
                f"{sql_str(created.isoformat())}, "
                f"{sql_str(resolved.isoformat()) if resolved else 'NULL'}) "
                f"ON CONFLICT (id) DO NOTHING;"
            )


def generate_replay_events() -> Iterator[str]:
    """Generate event replay history."""
    for t in range(NUM_TENANTS):
        tid = tenant_id(t)
        for r in range(REPLAY_EVENTS_PER_TENANT):
            eid = f"replay_{t:04d}_{r:04d}"
            event_type = random.choice([
                "contract.created", "contract.updated", "review.completed",
                "finding.created", "alert.triggered", "workflow.progress",
                "notification.delivered", "embedding.generated",
            ])
            cid = f"contract_{t:04d}_{random.randint(0, CONTRACTS_PER_TENANT-1):04d}"
            created = START_DATE + timedelta(days=random.randint(0, 700))

            payload_json = json.dumps({"source": "load-test", "seq": r})
            status_val = random.choice(["delivered", "delivered", "delivered", "pending"])
            yield (
                f"INSERT INTO outbox_events (id, tenant_id, aggregate_id, event_type, "
                f"payload, status, created_at) "
                f"VALUES ({sql_str(eid)}, {sql_str(tid)}, {sql_str(cid)}, "
                f"{sql_str(event_type)}, "
                f"{sql_str(payload_json)}, "
                f"{sql_str(status_val)}, "
                f"{sql_str(created.isoformat())}) "
                f"ON CONFLICT (id) DO NOTHING;"
            )


def generate_telemetry() -> Iterator[str]:
    """Generate telemetry history."""
    for t in range(NUM_TENANTS):
        tid = tenant_id(t)
        for m in range(TELEMETRY_POINTS_PER_TENANT):
            mid = f"telemetry_{t:04d}_{m:04d}"
            metric = random.choice([
                "api_latency_ms", "db_query_time_ms", "embedding_latency_ms",
                "queue_depth", "worker_utilization", "memory_usage_mb",
                "cpu_usage_pct", "ws_connections", "active_reviews",
            ])
            value = round(random.uniform(1, 10000), 2)
            created = START_DATE + timedelta(minutes=random.randint(0, 700 * 24 * 60))

            host_pod = random.randint(1, 10)
            tags_json = json.dumps({"host": f"pod-{host_pod}", "region": "us-east-1"})
            yield (
                f"INSERT INTO telemetry (id, tenant_id, metric_name, metric_value, "
                f"tags, recorded_at) "
                f"VALUES ({sql_str(mid)}, {sql_str(tid)}, {sql_str(metric)}, "
                f"{value}, "
                f"{sql_str(tags_json)}, "
                f"{sql_str(created.isoformat())}) "
                f"ON CONFLICT (id) DO NOTHING;"
            )


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic seed data for load testing")
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--disable-embeddings",
        action="store_true",
        help="Skip embedding generation (for faster seeding)",
    )
    parser.add_argument(
        "--disable-telemetry",
        action="store_true",
        help="Skip telemetry generation",
    )
    args = parser.parse_args()

    generators = [
        ("tenants", generate_tenants, False),
        ("contracts", generate_contracts, False),
        ("workflows", generate_workflows, False),
        ("alerts", generate_alerts, False),
        ("replay_events", generate_replay_events, False),
    ]

    if not args.disable_embeddings:
        generators.append(("embeddings", generate_embeddings, True))
    if not args.disable_telemetry:
        generators.append(("telemetry", generate_telemetry, False))

    output_file = None
    if args.output:
        output_file = open(args.output, "w")
        f = output_file
    else:
        f = sys.stdout

    # Write header
    f.write("-- ContractRiskEdge Load Test Seed Data\n")
    f.write(f"-- Generated: {datetime.now(timezone.utc).isoformat()}\n")
    f.write(f"-- Tenants: {NUM_TENANTS}\n")
    f.write(f"-- Contracts per tenant: {CONTRACTS_PER_TENANT}\n")
    f.write(f"-- Total contracts: {NUM_TENANTS * CONTRACTS_PER_TENANT}\n")
    f.write(f"-- Embeddings per contract: {EMBEDDINGS_PER_CONTRACT}\n")
    f.write(f"-- Total embeddings: {NUM_TENANTS * CONTRACTS_PER_TENANT * EMBEDDINGS_PER_CONTRACT}\n\n")

    f.write("BEGIN;\n\n")

    total_statements = 0
    for name, generator, is_heavy in generators:
        label = f"  [{name}] {'(heavy)' if is_heavy else ''}"
        count = 0
        for statement in generator():
            f.write(statement + "\n")
            count += 1
            total_statements += 1
            if count % 1000 == 0:
                print(f"{label} {count} records...", file=sys.stderr)
        print(f"{label} {count} records generated", file=sys.stderr)

    f.write("\nCOMMIT;\n")

    if output_file:
        output_file.close()

    print(f"\nTotal SQL statements generated: {total_statements}", file=sys.stderr)
    print(f"Estimated data size:", file=sys.stderr)
    print(f"  Contracts: {NUM_TENANTS * CONTRACTS_PER_TENANT}", file=sys.stderr)
    print(f"  Workflows: {NUM_TENANTS * WORKFLOWS_PER_TENANT}", file=sys.stderr)
    print(f"  Embeddings: {NUM_TENANTS * CONTRACTS_PER_TENANT * EMBEDDINGS_PER_CONTRACT}", file=sys.stderr)
    print(f"  Alerts: {NUM_TENANTS * ALERTS_PER_TENANT}", file=sys.stderr)
    print(f"  Replay events: {NUM_TENANTS * REPLAY_EVENTS_PER_TENANT}", file=sys.stderr)
    print(f"  Telemetry points: {NUM_TENANTS * TELEMETRY_POINTS_PER_TENANT}", file=sys.stderr)


if __name__ == "__main__":
    import json
    main()
