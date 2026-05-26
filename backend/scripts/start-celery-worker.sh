#!/usr/bin/env bash
# Start Celery worker (+ Beat) for local development.
#
# Dev: worker and beat run in one process (--beat).
# Prod: run worker and beat separately, e.g.
#   celery -A workers.celery_app worker -Q ingestion,default,ai,notifications,celery
#   celery -A workers.celery_app beat
#
# Includes the legacy "celery" queue to drain tasks queued before route fixes.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_ROOT"

# ── Load environment ──────────────────────────────────────────────────────────
# Load OPENAI_API_KEY and other env vars from ~/.zshrc (or .env if present)
if [[ -f "$BACKEND_ROOT/.env" ]]; then
  set -a; source "$BACKEND_ROOT/.env"; set +a
elif [[ -f "$HOME/.zshrc" ]]; then
  # Extract OPENAI_API_KEY from .zshrc if set
  _loaded_key="$(grep '^export OPENAI_API_KEY=' "$HOME/.zshrc" 2>/dev/null | head -1 | sed 's/^export //')"
  if [[ -n "$_loaded_key" ]]; then
    eval "export $_loaded_key"
  fi
fi

if [[ -x "$BACKEND_ROOT/.venv/bin/celery" ]]; then
  CELERY_BIN="$BACKEND_ROOT/.venv/bin/celery"
elif [[ -x "$BACKEND_ROOT/../.venv/bin/celery" ]]; then
  CELERY_BIN="$BACKEND_ROOT/../.venv/bin/celery"
else
  echo "No Celery found. Run: cd backend && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

exec "$CELERY_BIN" -A workers.celery_app worker \
  --beat \
  --loglevel=info \
  -Q ingestion,default,ai,notifications,celery
