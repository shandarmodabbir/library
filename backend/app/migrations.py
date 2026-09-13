"""Additive upgrade for the original unversioned library schema."""
from sqlalchemy import inspect, text
from .database import engine, Base

def upgrade():
    # Check conflicts before making any changes; never discard an existing loan.
    inspector = inspect(engine)
    if 'borrow' in inspector.get_table_names():
        with engine.connect() as connection:
            conflicts = connection.execute(text('SELECT book_id FROM borrow GROUP BY book_id HAVING COUNT(*) > 1')).scalars().all()
            if conflicts:
                raise RuntimeError(f'Return duplicate loans before upgrading. Book IDs: {conflicts}')
    Base.metadata.create_all(bind=engine)
    additions = {
        'borrow': {'renewals': 'INTEGER NOT NULL DEFAULT 0'},
        'users': {'email_reminders': 'BOOLEAN NOT NULL DEFAULT FALSE', 'role': "VARCHAR NOT NULL DEFAULT 'reader'"},
        'books': {'title_id': 'INTEGER REFERENCES book_titles(id)', 'description': "TEXT NOT NULL DEFAULT ''", 'isbn': "VARCHAR NOT NULL DEFAULT ''",
                  'publication_year': 'INTEGER', 'cover_url': "VARCHAR NOT NULL DEFAULT ''"},
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {column['name'] for column in inspect(connection).get_columns(table)}
            for column, definition in columns.items():
                if column not in existing:
                    connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {definition}'))
        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_borrow_book ON borrow (book_id)'))

    from .services.book_service import assign_title
    from .database import SessionLocal
    from .models import Book
    with SessionLocal() as db:
        for book in db.query(Book).filter(Book.title_id.is_(None)).all():
            assign_title(db, book)
        db.commit()
