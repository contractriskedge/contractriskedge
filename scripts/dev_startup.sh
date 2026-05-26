#!/usr/bin/env bash
# ── ContractRiskEdge Dev Startup Script ─────────────────────────────
# Stable, reproducible local development environment bootstrap.
#
# Usage:
#   ./scripts/dev_startup.sh          # Full startup (docker + migrations)
#   ./scripts/dev_startup.sh --quick  # Skip rebuild, just start services
#   ./scripts/dev_startup.sh --down   # Tear down everything
#   ./scripts/dev_startup.sh --reset  # Full reset (destroy volumes + rebuild)
#
# This script:
#   1. Checks prerequisites (Docker, Python)
#   2. Starts infrastructure services (PostgreSQL, Redis, MinIO)
#   3. Runs database migrations
#   4. Seeds development data
#   5. Starts the backend API server
#   6. Starts the Celery worker
#   7. Starts the frontend dev server
# ────────────────────────────────────────────────────────────────────

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Preflight Checks ──
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed. Please install Docker Desktop."
        exit 1
    fi

    if ! docker compose version &>/dev/null; then
        log_error "Docker Compose v2 is required."
        exit 1
    fi

    if ! command -v python3 &>/dev/null; then
        log_error "Python 3 is not installed."
        exit 1
    fi

    log_ok "All prerequisites satisfied."
}

# ── Docker Compose Management ──
start_infrastructure() {
    log_info "Starting infrastructure services (PostgreSQL, Redis, MinIO)..."
    cd "$PROJECT_ROOT"

    docker compose up -d postgres redis minio
    log_info "Waiting for PostgreSQL to be healthy..."
    sleep 3

    # Verify all services are running
    for service in postgres redis minio; do
        if docker compose ps "$service" | grep -q "healthy"; then
            log_ok "$service is healthy."
        else
            log_warn "$service may not be ready yet."
        fi
    done
}

start_all_services() {
    log_info "Starting all services..."
    cd "$PROJECT_ROOT"
    docker compose up -d
    log_ok "All services started."
}

stop_all_services() {
    log_info "Stopping all services..."
    cd "$PROJECT_ROOT"
    docker compose down
    log_ok "All services stopped."
}

reset_environment() {
    log_warn "Resetting entire environment (volumes will be destroyed)..."
    cd "$PROJECT_ROOT"
    docker compose down -v
    log_ok "Volumes cleared. Ready for fresh start."
}

# ── Database Migrations ──
run_migrations() {
    log_info "Running database migrations..."
    cd "$PROJECT_ROOT/backend"

    # Check if virtual environment exists
    if [ -d "../.venv" ]; then
        PYTHON="../.venv/bin/python"
    elif [ -d "venv" ]; then
        PYTHON="venv/bin/python"
    else
        PYTHON="python3"
    fi

    # Install dependencies if needed
    if [ ! -f "../.venv/bin/alembic" ] && [ ! -f "venv/bin/alembic" ]; then
        log_info "Installing Python dependencies..."
        $PYTHON -m pip install -r requirements.txt -q 2>/dev/null || true
    fi

    # Run migrations
    if $PYTHON -m alembic upgrade head 2>/dev/null; then
        log_ok "Database migrations applied successfully."
    else
        log_warn "Alembic migration failed. You may need to run it manually:"
        log_warn "  cd backend && $PYTHON -m alembic upgrade head"
    fi
}

seed_data() {
    log_info "Seeding development data..."
    cd "$PROJECT_ROOT"

    # Run seed SQL if psql is available
    if command -v psql &>/dev/null; then
        PGPASSWORD=dev_password psql -h localhost -U dev_user -d contract_risk_dev \
            -f "$PROJECT_ROOT/infra/seed_data.sql" 2>/dev/null && \
            log_ok "Seed data loaded." || \
            log_warn "Seed data loading skipped (may already exist)."
    else
        log_warn "psql not found. Seed data must be loaded manually."
    fi
}

# ── Create MinIO Bucket ──
setup_minio() {
    log_info "Setting up MinIO bucket..."
    # Wait for MinIO to be ready
    sleep 2

    # Install mc client if not present
    if ! command -v mc &>/dev/null; then
        docker run --rm --network=host \
            --entrypoint /bin/sh minio/mc \
            -c "
                mc alias set local http://localhost:9000 minioadmin minioadmin
                mc mb local/contract-uploads --ignore-existing
                mc policy set public local/contract-uploads
            " 2>/dev/null && log_ok "MinIO bucket created." || \
            log_warn "MinIO bucket setup skipped."
    else
        mc alias set local http://localhost:9000 minioadmin minioadmin 2>/dev/null
        mc mb local/contract-uploads --ignore-existing 2>/dev/null
        log_ok "MinIO bucket configured."
    fi
}

# ── Main ──
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║        ContractRiskEdge Development Environment         ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""

    case "${1:-}" in
        --down)
            stop_all_services
            exit 0
            ;;
        --reset)
            reset_environment
            exit 0
            ;;
        --quick)
            check_prerequisites
            start_all_services
            echo ""
            log_info "Environment is running!"
            log_info "  Backend API:  http://localhost:8000"
            log_info "  Frontend:     http://localhost:3000"
            log_info "  MinIO Console: http://localhost:9001"
            log_info "  Flower:       http://localhost:5555"
            exit 0
            ;;
        *)
            check_prerequisites
            start_infrastructure
            setup_minio
            run_migrations
            seed_data
            start_all_services
            echo ""
            log_info "╔══════════════════════════════════════════════════╗"
            log_info "║  Environment is fully operational!              ║"
            log_info "║                                                ║"
            log_info "║  Backend API:   http://localhost:8000           ║"
            log_info "║  API Docs:      http://localhost:8000/docs      ║"
            log_info "║  Frontend:      http://localhost:3000           ║"
            log_info "║  MinIO Console: http://localhost:9001           ║"
            log_info "║  Flower (Celery): http://localhost:5555         ║"
            log_info "║                                                ║"
            log_info "║  PostgreSQL:    localhost:5432                  ║"
            log_info "║  Redis:         localhost:6379                  ║"
            log_info "║  MinIO S3:      http://localhost:9000           ║"
            log_info "╚══════════════════════════════════════════════════╝"
            echo ""
            log_info "To stop:  ./scripts/dev_startup.sh --down"
            log_info "To reset: ./scripts/dev_startup.sh --reset"
            ;;
    esac
}

main "$@"
