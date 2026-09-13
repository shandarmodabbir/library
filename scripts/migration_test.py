import os
os.environ["MAINTENANCE_ENABLED"] = "false"
import sqlite3
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / 'old.db'
    os.environ['DATABASE_URL'] = f'sqlite:///{path}'
    with sqlite3.connect(path) as db:
        db.executescript('''
        CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL, password VARCHAR NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, phone_number VARCHAR);
        CREATE TABLE books (id INTEGER PRIMARY KEY, name VARCHAR, author VARCHAR, category VARCHAR, provider_user_id INTEGER);
        CREATE TABLE borrow (book_id INTEGER, user_id INTEGER, borrowed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, due_date TIMESTAMP, PRIMARY KEY(book_id,user_id));
        INSERT INTO users(id,email,password) VALUES(1,'old@example.com','existing-hash');
        INSERT INTO books VALUES(1,'Existing book','Author','Fiction',1);
        INSERT INTO borrow(book_id,user_id,due_date) VALUES(1,1,'2026-10-01');
        ''')
    from app import models
    from app.migrations import upgrade
    from app.database import engine
    upgrade()
    upgrade()
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT role FROM users').fetchone()[0] == 'reader'
        assert db.execute('SELECT name,description,isbn FROM books').fetchone() == ('Existing book','','')
        assert db.execute('SELECT COUNT(*) FROM borrow').fetchone()[0] == 1
        try:
            db.execute("INSERT INTO borrow(book_id,user_id,due_date) VALUES(1,2,'2026-10-01')")
            raise AssertionError('Unique-copy constraint missing')
        except sqlite3.IntegrityError:
            pass
    engine.dispose()
print('PASS: existing records preserved, upgrade repeatable, unique-copy constraint applied')
