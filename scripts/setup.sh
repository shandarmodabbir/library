#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v uv >/dev/null || { echo 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/'; exit 1; }
uv venv --python 3.12 --allow-existing backend/.venv
uv pip sync --python backend/.venv/bin/python backend/requirements.txt
backend/.venv/bin/python - <<'PY'
from pathlib import Path
import secrets
root = Path.cwd()
env = root / 'backend/.env'
if not env.exists():
    env.write_text((root / 'backend/.env.example').read_text().replace('replace-with-a-random-secret', secrets.token_hex(32)))
local = root / 'backend/.env.local'
if not local.exists():
    local.write_text(f'DATABASE_URL=sqlite:///{root / "backend/library.db"}\n')
PY
npm --prefix frontend ci
npm --prefix frontend run build
