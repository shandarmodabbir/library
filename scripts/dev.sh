#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
pids=()
cleanup() { for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done; }
trap cleanup EXIT
trap 'exit 130' INT TERM
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 &
pids+=("$!")
npm --prefix frontend run dev -- --host 127.0.0.1 &
pids+=("$!")
while kill -0 "${pids[0]}" 2>/dev/null && kill -0 "${pids[1]}" 2>/dev/null; do sleep 1; done
exit 1
