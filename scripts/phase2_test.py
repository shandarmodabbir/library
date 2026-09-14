"""Reservations, renewals, reminders, ISBN lookup, history and backup recovery."""
import os
os.environ['MAINTENANCE_ENABLED'] = 'false'
import sys
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_URL'] = f'sqlite:///{tmp}/library.db'
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import SessionLocal, engine
    from app import models
    from app.services.maintenance import maintenance_tick
    from app.services.backups import backup, verify
    from app.routers import isbn
    with TestClient(app) as c:
        def account(name):
            r = c.post('/users/', json={'email': f'{name}@example.com', 'password': 'test-password'})
            token = c.post('/login/', data={'username': f'{name}@example.com', 'password': 'test-password'}).json()['access_token']
            return r.json()['id'], {'Authorization': f'Bearer {token}'}
        aid,a = account('a'); bid,b = account('b'); cid,cc = account('c')
        body = {'name': 'A Book', 'author': 'Author', 'category': 'Fiction', 'isbn':'9780441172719'}
        book = c.post('/books/', headers=a, json=body).json()['id']
        copy = c.post('/books/', headers=a, json=body).json()['id']
        c.post('/books/', headers=a, json={**body,'name':'Z Book','isbn':''})
        catalog = c.get('/books/catalog?page_size=1').json()
        assert catalog['total'] == 2 and len(catalog['items']) == 1
        assert catalog['items'][0]['copies'] == 2
        assert len(c.get(f'/books/{book}/copies').json()) == 2
        assert c.get('/books/catalog?page=0').status_code == 422
        assert c.post('/borrow/', headers=a,json={'book_id':book,'dir':1}).status_code == 201
        due = c.get('/library/mine',headers=a).json()['loans'][0]['due_date']
        r = c.post(f'/borrow/{book}/renew',headers=a)
        assert r.status_code == 200 and r.json()['renewals'] == 1
        assert datetime.fromisoformat(r.json()['due_date']) - datetime.fromisoformat(due) == timedelta(days=14)
        assert c.post(f'/borrow/{book}/renew',headers=b).status_code == 404
        assert c.post(f'/borrow/{book}/reserve',headers=b).status_code == 200
        assert c.post(f'/borrow/{book}/reserve',headers=b).status_code == 200
        assert c.post(f'/borrow/{book}/reserve',headers=cc).status_code == 200
        assert c.get('/library/mine',headers=cc).json()['reservations'][0]['position'] == 2
        assert c.post(f'/borrow/{book}/renew',headers=a).status_code == 409
        assert c.post('/borrow/', headers=a,json={'book_id':book,'dir':0}).status_code == 201
        assert len(c.get('/library/mine',headers=a).json()['history']) == 1
        assert c.get('/library/mine',headers=b).json()['history'] == []
        assert c.get('/library/mine',headers=b).json()['reservations'][0]['ready_until']
        assert c.post('/borrow/',headers=cc,json={'book_id':book,'dir':1}).status_code == 409
        assert c.delete(f'/books/{book}',headers=a).status_code == 409
        with SessionLocal() as db:
            db.query(models.Reservation).filter_by(user_id=bid).one().ready_until = datetime.now(timezone.utc)-timedelta(seconds=1)
            db.commit()
        maintenance_tick()
        assert c.get('/library/mine',headers=b).json()['reservations'] == []
        assert c.get('/library/mine',headers=cc).json()['reservations'][0]['ready_until']
        assert c.post('/borrow/',headers=cc,json={'book_id':book,'dir':1}).status_code == 201
        assert c.get('/library/mine',headers=cc).json()['reservations'] == []
        assert c.post(f'/borrow/{book}/reserve',headers=b).status_code == 200
        assert c.delete(f'/borrow/{book}/reserve',headers=b).status_code == 200
        with SessionLocal() as db:
            db.query(models.Borrow).filter_by(book_id=book).one().due_date = datetime.now(timezone.utc)+timedelta(days=1)
            db.commit()
        assert c.get('/library/mine',headers=cc).json()['loans'][0]['due_soon']
        response = MagicMock()
        response.json.return_value = {'ISBN:9780441172719':{'title':'Dune','authors':[{'name':'Frank Herbert'}],'publish_date':'1965','cover':{'medium':'https://covers.openlibrary.org/test.jpg'}}}
        with patch.object(isbn.httpx,'get',return_value=response):
            assert c.get('/books/isbn/9780441172719',headers=a).json()['name'] == 'Dune'
            assert c.get('/books/isbn/9780441172710',headers=a).status_code == 422
        assert c.post('/borrow/',headers=cc,json={'book_id':book,'dir':0}).status_code == 201
        assert c.delete(f'/books/{book}',headers=a).status_code == 204
        old = c.get('/library/mine',headers=a).json()['history'][0]
        assert old['book_id'] is None and old['name'] == 'A Book'
    import sqlite3
    with sqlite3.connect(Path(tmp)/'library.db') as wal_db:
        wal_db.execute('PRAGMA journal_mode=WAL')
    folder = backup({'library.db':Path(tmp)/'library.db'}, Path(tmp)/'backups')
    assert 'library.db' in verify(folder)
    assert not list(folder.glob('*-wal'))
    assert not list(folder.glob('*-shm'))
    target = Path(tmp)/'recovery'
    subprocess.run([sys.executable,'scripts/restore_db.py',str(folder),'--destination',str(target)],check=True)
    import sqlite3
    with sqlite3.connect(target/'library.db') as restored:
        assert restored.execute('SELECT COUNT(*) FROM loan_history').fetchone()[0] == 2
    (folder/'library.db').write_bytes(b'corrupted')
    try:
        verify(folder)
        raise AssertionError('Corrupt backup accepted')
    except ValueError:
        pass
    engine.dispose()
print('PASS: copies, pagination, renewals, FIFO reservations, expiry, claim, history preservation, in-app due-date reminders, ISBN, verified backup/restore')
