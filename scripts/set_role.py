"""Local administrator command; public registration always creates a reader."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.database import SessionLocal
from app.models import User
from app.migrations import upgrade
parser = argparse.ArgumentParser()
parser.add_argument('email')
parser.add_argument('role', choices=['reader', 'librarian'])
args = parser.parse_args()
upgrade()
with SessionLocal() as db:
    user = db.query(User).filter(User.email == args.email).first()
    if not user:
        parser.error('Register this account in the app first')
    user.role = args.role
    db.commit()
print(f'{args.email}: {args.role}')
