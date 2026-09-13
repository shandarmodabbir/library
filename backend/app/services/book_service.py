import hashlib
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app import schemas, models

def assign_title(db, book):
    # Match editions by ISBN; without ISBN use normalized title and author.
    isbn = ''.join(c for c in (book.isbn or '') if c.isalnum()).upper()
    identity = 'isbn:' + isbn if isbn else 'text:' + hashlib.sha256((book.name.strip().casefold() + '\0' + book.author.strip().casefold()).encode()).hexdigest()
    title = db.query(models.BookTitle).filter_by(identity=identity).first()
    if not title:
        try:
            with db.begin_nested():
                title = models.BookTitle(identity=identity)
                db.add(title)
                db.flush()
        except IntegrityError:
            title = db.query(models.BookTitle).filter_by(identity=identity).one()
    book.title_id = title.id

class BookService:
    def create_book(self, db: Session, book_data: schemas.BookCreate, current_user: models.User, commit=True):
        new_book = models.Book(provider_user_id=current_user.id, **book_data.model_dump())
        assign_title(db, new_book)
        db.add(new_book)
        db.flush()
        if commit:
            db.commit()
            db.refresh(new_book)
        return new_book

    def search_book(self, db, name=None, author=None, category=None):
        query = db.query(models.Book)
        for column, value in [(models.Book.name,name), (models.Book.author,author), (models.Book.category,category)]:
            if value:
                query = query.filter(column.ilike(f'%{value}%'))
        return query.order_by(models.Book.id).limit(100).all()

book_service = BookService()
