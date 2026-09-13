"""Consistent SQLite snapshots with a manifest and integrity verification."""
from contextlib import closing
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def backup(sources, destination):
    folder = Path(destination) / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True, mode=0o700)
    manifest = {}
    for name, path in sources.items():
        path = Path(path)
        if not path.exists():
            continue
        target = folder / name
        with closing(sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True)) as source, closing(sqlite3.connect(target)) as out:
            source.backup(out)
            # A snapshot of a WAL-mode source may inherit WAL mode. Make the
            # backup self-contained before hashing or restoring just the .db file.
            out.execute('PRAGMA journal_mode=DELETE')
            if out.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError(f'Backup verification failed for {name}')
        target.chmod(0o600)
        manifest[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    if not manifest:
        folder.rmdir()
        raise ValueError('No SQLite database files found')
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return folder


def verify(folder):
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text())
    if not manifest or any(name not in ('library.db', 'agent_sessions.db') for name in manifest):
        raise ValueError('Invalid backup manifest')
    for name, digest in manifest.items():
        path = folder / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Checksum mismatch: {name}')
        with closing(sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError(f'Database integrity check failed: {name}')
    return manifest
