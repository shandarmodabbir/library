#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.database import engine
from app.config import settings, BACKEND_DIR
from app.services.backups import backup
parser = argparse.ArgumentParser()
parser.add_argument('--destination', default=settings.backup_dir)
args = parser.parse_args()
if engine.dialect.name != 'sqlite':
    parser.error('This command is for SQLite; use PostgreSQL backup tooling for PostgreSQL')
print(backup({'library.db': engine.url.database, 'agent_sessions.db': BACKEND_DIR / 'agent_sessions.db'}, args.destination))
