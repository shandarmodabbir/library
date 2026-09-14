import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from ..config import settings, BACKEND_DIR
from ..database import engine, SessionLocal
from .. import models
from .circulation import advance_queue
from .backups import backup

log = logging.getLogger(__name__)

def maintenance_tick():
    with SessionLocal() as db:
        if engine.dialect.name == 'sqlite':
            db.execute(text('BEGIN IMMEDIATE'))
        for (book_id,) in db.query(models.Reservation.book_id).distinct().all():
            advance_queue(db, book_id)
        db.commit()

async def run_maintenance():
    last_backup = None
    while True:
        try:
            today = datetime.now(timezone.utc).date()
            if last_backup != today:
                await asyncio.to_thread(backup, {'library.db': engine.url.database, 'agent_sessions.db': BACKEND_DIR / 'agent_sessions.db'}, settings.backup_dir)
                last_backup = today
            await asyncio.to_thread(maintenance_tick)
        except Exception:
            log.exception('Library maintenance failed')
        await asyncio.sleep(60)
