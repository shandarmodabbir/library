from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2
from ..database import get_db
from ..services.circulation import return_loan, lock_book, queue, utc
from ..config import settings

router = APIRouter(prefix="/library", tags=["My library"])

def librarian(user=Depends(oauth2.get_current_user)):
    if user.role != 'librarian':
        raise HTTPException(403, 'Librarian access required')
    return user

def loan_out(loan, book):
    due = loan.due_date.replace(tzinfo=timezone.utc) if loan.due_date.tzinfo is None else loan.due_date
    return {'book': schemas.BookOut.model_validate(book), 'user_id': loan.user_id,
            'renewals': loan.renewals, 'due_soon': datetime.now(timezone.utc) <= due <= datetime.now(timezone.utc) + timedelta(days=3), 'borrowed_at': loan.borrowed_at, 'due_date': due, 'overdue': due < datetime.now(timezone.utc)}

@router.get('/mine')
def mine(db: Session = Depends(get_db), user=Depends(oauth2.get_current_user)):
    loans = db.query(models.Borrow, models.Book).join(models.Book, models.Book.id == models.Borrow.book_id).filter(models.Borrow.user_id == user.id).all()
    reading = db.query(models.ReadingStatus, models.Book).join(models.Book, models.Book.id == models.ReadingStatus.book_id).filter(models.ReadingStatus.user_id == user.id).all()
    reservations = db.query(models.Reservation, models.Book).join(models.Book, models.Book.id == models.Reservation.book_id).filter(models.Reservation.user_id == user.id).all()
    history = db.query(models.LoanHistory).filter_by(user_id=user.id).order_by(models.LoanHistory.returned_at.desc()).all()
    return {'email_reminders': user.email_reminders, 'email_configured': bool(settings.smtp_host and settings.smtp_from),
            'reservations': [{'book': schemas.BookOut.model_validate(book), 'position': next(i+1 for i,r in enumerate(queue(db,book.id)) if r.user_id == user.id), 'ready_until': utc(r.ready_until) if r.ready_until else None} for r,book in reservations],
            'history': [{'id': h.id, 'book_id': h.book_id, 'name': h.book_name, 'author': h.book_author, 'borrowed_at': utc(h.borrowed_at), 'due_date': utc(h.due_date), 'returned_at': utc(h.returned_at), 'renewals': h.renewals} for h in history],
            'contributions': [schemas.BookOut.model_validate(b) for b in db.query(models.Book).filter(models.Book.provider_user_id == user.id).all()],
            'loans': [loan_out(loan, book) for loan, book in loans],
            'reading': [{'book': schemas.BookOut.model_validate(book), 'status': status.status} for status, book in reading]}

class ReadingRequest(BaseModel):
    status: Literal['want_to_read', 'reading', 'finished'] | None

@router.put('/reading/{book_id}')
def reading_status(book_id: int, body: ReadingRequest, db: Session = Depends(get_db), user=Depends(oauth2.get_current_user)):
    if db.get(models.Book, book_id) is None:
        raise HTTPException(404, 'Book not found')
    entry = db.get(models.ReadingStatus, (user.id, book_id))
    if body.status is None:
        if entry:
            db.delete(entry)
    elif entry:
        entry.status = body.status
    else:
        db.add(models.ReadingStatus(user_id=user.id, book_id=book_id, status=body.status))
    db.commit()
    return {'status': body.status}

@router.get('/manage')
def manage(db: Session = Depends(get_db), user=Depends(librarian)):
    loans = db.query(models.Borrow, models.Book).join(models.Book, models.Book.id == models.Borrow.book_id).all()
    return {'members': [schemas.UserOut.model_validate(u) for u in db.query(models.User).all()],
            'loans': [loan_out(loan, book) for loan, book in loans]}

@router.delete('/loans/{book_id}')
def return_book(book_id: int, db: Session = Depends(get_db), user=Depends(librarian)):
    db.rollback()
    book = lock_book(db, book_id)
    loan = db.query(models.Borrow).filter_by(book_id=book_id).first()
    if loan:
        return_loan(db, loan, book)
    db.commit()
    return {'message': 'Book returned'}


class ReminderPreference(BaseModel):
    enabled: bool

@router.put('/reminders')
def reminders(body: ReminderPreference, db: Session = Depends(get_db), user=Depends(oauth2.get_current_user)):
    if body.enabled and not (settings.smtp_host and settings.smtp_from):
        raise HTTPException(503, 'Email delivery is not configured yet')
    user.email_reminders = body.enabled
    db.commit()
    return {'enabled': user.email_reminders}
