from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import text
from .. import models

def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

def lock_book(db, book_id):
    # Acquire a write lock before reading state, including on SQLite.
    if db.bind.dialect.name == 'sqlite':
        db.execute(text('BEGIN IMMEDIATE'))
    book = db.query(models.Book).filter_by(id=book_id).with_for_update().first()
    if not book:
        raise HTTPException(404, 'Book not found')
    return book

def queue(db, book_id):
    return db.query(models.Reservation).filter_by(book_id=book_id).order_by(models.Reservation.id).all()

def advance_queue(db, book_id):
    if db.query(models.Borrow).filter_by(book_id=book_id).first():
        return queue(db, book_id)
    now = datetime.now(timezone.utc)
    waiting = queue(db, book_id)
    while waiting and waiting[0].ready_until and utc(waiting[0].ready_until) <= now:
        db.delete(waiting.pop(0))
    if waiting and waiting[0].ready_until is None:
        waiting[0].ready_until = now + timedelta(hours=48)
    db.flush()
    return waiting

def return_loan(db, loan, book):
    db.add(models.LoanHistory(user_id=loan.user_id, book_id=book.id, book_name=book.name,
        book_author=book.author, borrowed_at=loan.borrowed_at, due_date=loan.due_date,
        returned_at=datetime.now(timezone.utc), renewals=loan.renewals))
    db.delete(loan)
    db.flush()
    advance_queue(db, book.id)
