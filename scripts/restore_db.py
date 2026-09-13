#!/usr/bin/env python3
"""Restore to an empty directory; replacing a live database requires stopping the app."""
import argparse
import os
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.services.backups import verify
parser = argparse.ArgumentParser()
parser.add_argument('backup', type=Path)
parser.add_argument('--destination', type=Path, required=True, help='New, empty recovery directory')
args = parser.parse_args()
manifest = verify(args.backup)
if args.destination.exists() and any(args.destination.iterdir()):
    parser.error('Destination must be empty; restore here first, then stop the app before switching databases')
args.destination.mkdir(parents=True, exist_ok=True, mode=0o700)
for name in manifest:
    shutil.copyfile(args.backup / name, args.destination / name)
    (args.destination / name).chmod(0o600)
print(f'Verified and restored {len(manifest)} databases to {args.destination.resolve()}')
