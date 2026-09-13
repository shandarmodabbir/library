import asyncio
import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from ..config import settings, BACKEND_DIR
from ..database import engine, SessionLocal
from .. import models
from .circulation import advance_queue, utc
from .backups import backup

log = logging.getLogger(__name__)

def maintenance_tick(send_email=False):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        if engine.dialect.name == 'sqlite':
            db.execute(text('BEGIN IMMEDIATE'))
        for (book_id,) in db.query(models.Reservation.book_id).distinct().all():
            advance_queue(db, book_id)
        db.commit()
    if not send_email or not (settings.smtp_host and settings.smtp_from):
        return
    with SessionLocal() as db:
        rows = db.query(models.Borrow, models.User, models.Book).join(models.User, models.User.id == models.Borrow.user_id).join(models.Book, models.Book.id == models.Borrow.book_id).filter(models.User.email_reminders.is_(True)).all()
        for loan, user, book in rows:
            if utc(loan.due_date) > now + timedelta(days=3):
                continue
            key = f'{user.id}:{book.id}:{loan.borrowed_at.isoformat()}:{loan.due_date.isoformat()}:{now.date()}'
            if db.get(models.ReminderDelivery, key):
                continue
            message = EmailMessage()
            message['From'], message['To'] = settings.smtp_from, user.email
            message['Subject'] = 'Library: book return reminder'
            message.set_content(f'{book.name} is due on {utc(loan.due_date).date()}. Open My Library to return or renew it.')
            # Reserve delivery before sending: an uncertain SMTP failure is not retried automatically.
            db.add(models.ReminderDelivery(key=key)); db.commit()
            try:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                    if settings.smtp_starttls:
                        smtp.starttls()
                    if settings.smtp_username:
                        smtp.login(settings.smtp_username, settings.smtp_password)
                    smtp.send_message(message)
            except Exception:
                log.exception('Reminder delivery failed; delivery record retained to avoid duplicate mail')

async def run_maintenance():
    last_backup = None
    while True:
        try:
            today = datetime.now(timezone.utc).date()
            if engine.dialect.name == 'sqlite' and last_backup != today:
                await asyncio.to_thread(backup, {'library.db': engine.url.database, 'agent_sessions.db': BACKEND_DIR / 'agent_sessions.db'}, settings.backup_dir)
                last_backup = today
            await asyncio.to_thread(maintenance_tick, True)
        except Exception:
            log.exception('Library maintenance failed')
        await asyncio.sleep(60)
