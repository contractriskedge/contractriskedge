#!/bin/bash
# Start the ContractRiskEdge API server
# Uses the local venv at /tmp/contractrisk-venv for fast startup

VENV="/tmp/contractrisk-venv"
API_DIR="/Volumes/home/ContractRiskEdge/api"

if [ ! -f "$VENV/bin/python" ]; then
    echo "Creating local venv at $VENV..."
    cd /Volumes/home/ContractRiskEdge
    python3.11 -m venv "$VENV" --clear
    "$VENV/bin/pip" install -r "$API_DIR/requirements.txt" -q
    echo "Venv created and packages installed"
fi

echo "Starting server..."
cd "$API_DIR"
"$VENV/bin/python" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-delay 5 --reload-dir "$API_DIR"
