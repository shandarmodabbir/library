from typing import Optional, List
from ..database import SessionLocal
from .. import models, schemas
from ..services.book_service import book_service


import contextvars

current_request_id_ctx = contextvars.ContextVar("request_id", default=None)

current_user_id_ctx = contextvars.ContextVar("current_user_id", default=None)

def create_book_tool(name: str, author: str, category: str) -> str:

    db = SessionLocal()
    try:
        user_id = current_user_id_ctx.get()
        if not user_id:
            return "User not authenticated or user id not found in context"

        user = db.query(models.User).filter(models.User.id == user_id).first()

        if not user:
            return "User not found"

        book_data = schemas.BookCreate(name=name, author=author, category=category)

        import hashlib
        from sqlalchemy.exc import IntegrityError
        request_id = current_request_id_ctx.get()
        action_key = hashlib.sha256((book_data.name.casefold() + "\0" + book_data.author.casefold()).encode()).hexdigest()
        if request_id:
            prior = db.get(models.AgentAction, (user_id, request_id, action_key))
            if prior:
                return prior.result
        book = book_service.create_book(db, book_data, user, commit=False)
        result = f"Created [{book.name}](/book/{book.id}) successfully"
        if request_id:
            db.add(models.AgentAction(user_id=user_id, request_id=request_id, action_key=action_key, result=result))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            prior = db.get(models.AgentAction, (user_id, request_id, action_key)) if request_id else None
            if prior:
                return prior.result
            raise
        return result
    finally:
        db.close()

def search_book_tool(name: str | None = None, author: str | None = None, category: str | None = None):

    db = SessionLocal()
    try:

        fetched_books = book_service.search_book(db, name, author, category)

        if not fetched_books:
            return "No books found matching the search criteria."

        result = "Search matches with these books:\n"
        for book in fetched_books:
            result += f"- [{book.name}](/book/{book.id}) by {book.author} (Category: {book.category}, available: {book.available})\n"

        return result

    finally:
        db.close()


def my_loans_tool() -> str:
    """Get the authenticated reader's active loans, due dates, and overdue flags."""
    from datetime import datetime, timezone
    user_id = current_user_id_ctx.get()
    if user_id is None:
        return 'Authentication required'
    with SessionLocal() as db:
        rows = db.query(models.Borrow, models.Book).join(models.Book, models.Book.id == models.Borrow.book_id).filter(models.Borrow.user_id == user_id).all()
        results = []
        for loan, book in rows:
            due = loan.due_date.replace(tzinfo=timezone.utc) if loan.due_date.tzinfo is None else loan.due_date
            results.append(f'[{book.name}](/book/{book.id}) — due {due.isoformat()}, overdue: {due < datetime.now(timezone.utc)}')
        return '\n'.join(results) or 'You have no active loans.'
