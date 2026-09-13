from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas, database, models, oauth2
from ..services.circulation import lock_book, advance_queue, return_loan, utc

router = APIRouter(prefix='/borrow', tags=['Borrow'])

@router.post('/', status_code=201)
def borrow(body: schemas.Borrow, db: Session = Depends(database.get_db), user=Depends(oauth2.get_current_user)):
    # Auth uses another session so this transaction can lock before its first read.
    db.rollback()
    book = lock_book(db, body.book_id)
    loan = db.query(models.Borrow).filter_by(book_id=book.id).first()
    if body.dir == 1:
        if loan:
            if loan.user_id != user.id:
                raise HTTPException(409, 'This copy is already on loan')
        else:
            waiting = advance_queue(db, book.id)
            if waiting and waiting[0].user_id != user.id:
                db.commit()
                raise HTTPException(409, 'This copy is held for the next reader in the reservation queue')
            if waiting:
                db.delete(waiting[0])
            db.add(models.Borrow(book_id=book.id, user_id=user.id))
    elif loan and loan.user_id == user.id:
        return_loan(db, loan, book)
    db.commit()
    return {'message': 'Successfully borrowed' if body.dir else 'Book returned'}

@router.get('/mine', response_model=list[schemas.BookOut])
def mine(db: Session = Depends(database.get_db), user=Depends(oauth2.get_current_user)):
    return db.query(models.Book).join(models.Borrow).filter(models.Borrow.user_id == user.id).all()

@router.post('/{book_id}/renew')
def renew(book_id: int, db: Session = Depends(database.get_db), user=Depends(oauth2.get_current_user)):
    db.rollback()
    book = lock_book(db, book_id)
    loan = db.query(models.Borrow).filter_by(book_id=book.id, user_id=user.id).first()
    if not loan:
        raise HTTPException(404, 'Active loan not found')
    if db.query(models.Reservation).filter_by(book_id=book.id).first():
        raise HTTPException(409, 'Another reader is waiting; please return this copy')
    if utc(loan.due_date) < datetime.now(timezone.utc):
        raise HTTPException(409, 'Overdue loans must be returned before borrowing again')
    if loan.renewals >= 2:
        raise HTTPException(409, 'This loan has reached its two-renewal limit')
    loan.due_date = utc(loan.due_date) + timedelta(days=14)
    loan.renewals += 1
    db.commit()
    return {'due_date': utc(loan.due_date), 'renewals': loan.renewals}

@router.post('/{book_id}/reserve')
def reserve(book_id: int, db: Session = Depends(database.get_db), user=Depends(oauth2.get_current_user)):
    db.rollback()
    book = lock_book(db, book_id)
    loan = db.query(models.Borrow).filter_by(book_id=book.id).first()
    waiting = advance_queue(db, book.id)
    if loan and loan.user_id == user.id:
        raise HTTPException(409, 'You already have this copy')
    if not loan and not waiting:
        raise HTTPException(409, 'This copy is available; borrow it now')
    if not any(r.user_id == user.id for r in waiting):
        db.add(models.Reservation(book_id=book.id, user_id=user.id))
        db.flush()
    db.commit()
    return {'message': 'Reservation saved'}

@router.delete('/{book_id}/reserve')
def cancel(book_id: int, db: Session = Depends(database.get_db), user=Depends(oauth2.get_current_user)):
    db.rollback()
    lock_book(db, book_id)
    db.query(models.Reservation).filter_by(book_id=book_id,user_id=user.id).delete()
    advance_queue(db, book_id)
    db.commit()
    return {'message': 'Reservation cancelled'}
