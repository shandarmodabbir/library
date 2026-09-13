from fastapi import APIRouter, Depends, status, HTTPException, Response, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional, List, Literal
from ..database import get_db
from .. import models, schemas, oauth2
from ..services.book_service import book_service

router = APIRouter(
    prefix="/books",
    tags=['Books']
)


@router.get("/", response_model= List[schemas.BookOut])
def get_book(
    db: Session = Depends(get_db),
    name: Optional[str] = "",
    author: Optional[str] = "",
    category: Optional[str] = ""
):

    return book_service.search_book(db, name, author, category)

@router.post("/", response_model=schemas.BookOut)
def create_book(
    book: schemas.BookCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):

    return book_service.create_book(db, book, current_user)

@router.get('/catalog')
def catalog(db: Session = Depends(get_db), name: str = '', author: str = '', category: str = '',
            availability: Literal['all', 'available', 'unavailable'] = 'all',
            sort: Literal['title', 'author', 'newest'] = 'title',
            page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=48)):
    query = db.query(models.Book)
    for column, value in [(models.Book.name,name),(models.Book.author,author),(models.Book.category,category)]:
        if value:
            query = query.filter(column.ilike(f'%{value}%'))
    free = ~models.Book.loans.any() & ~models.Book.reservations.any()
    if availability == 'available':
        query = query.filter(free)
    elif availability == 'unavailable':
        query = query.filter(~free)
    grouped = query.with_entities(models.Book.title_id, func.min(models.Book.name).label('name'), func.min(models.Book.author).label('author'), func.max(models.Book.id).label('newest')).group_by(models.Book.title_id).subquery()
    titles = db.query(grouped)
    count = titles.count()
    order = grouped.c.newest.desc() if sort == 'newest' else func.lower(grouped.c.author if sort == 'author' else grouped.c.name)
    rows = titles.order_by(order, grouped.c.title_id).offset((page-1)*page_size).limit(page_size).all()
    items = []
    for row in rows:
        copies = db.query(models.Book).filter_by(title_id=row.title_id).order_by(models.Book.id).all()
        representative = next((b for b in copies if b.available == (availability != 'unavailable')), copies[0])
        items.append({'title_id': row.title_id, 'book': schemas.BookOut.model_validate(representative),
                      'copies': len(copies), 'available_copies': sum(b.available for b in copies)})
    return {'items': items, 'total': count, 'page': page, 'page_size': page_size}

@router.get('/{book_id}/copies', response_model=list[schemas.BookOut])
def copies(book_id: int, db: Session = Depends(get_db)):
    book = db.get(models.Book, book_id)
    if not book:
        raise HTTPException(404, 'Book not found')
    return db.query(models.Book).filter_by(title_id=book.title_id).order_by(models.Book.id).all()

@router.get("/{id}", response_model=schemas.BookOut)
def get_book(id: int, db: Session = Depends(get_db)):

    fetched_book = db.query(models.Book).filter(models.Book.id == id).first()

    if not fetched_book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"book with id {id} not found")

    return fetched_book


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_book(id: int, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):

    book_query = db.query(models.Book).filter(models.Book.id == id)

    fetched_book = book_query.first()

    if fetched_book == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"book with id {id} not found")

    if fetched_book.provider_user_id != current_user.id and current_user.role != "librarian":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"not authorized to perform requested action")

    if fetched_book.reservations:
        raise HTTPException(409, "Reservations must be cancelled before removing this copy")
    if fetched_book.loans:
        raise HTTPException(status_code=409, detail="Return this book before removing it")
    book_query.delete(synchronize_session=False)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.put("/{id}", response_model=schemas.BookBase)
def update_book(id: int, book: schemas.BookBase, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):

    book_query = db.query(models.Book).filter(models.Book.id == id)

    fetched_book = book_query.first()

    if fetched_book == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"book with id {id} not found")

    if fetched_book.provider_user_id != current_user.id and current_user.role != "librarian":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"not authorized to perform requested action")

    for field, value in book.model_dump().items():
        setattr(fetched_book, field, value)
    from ..services.book_service import assign_title
    assign_title(db, fetched_book)
    db.commit()

    return book_query.first()
