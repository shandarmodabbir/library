"""Integration checks for availability, reading shelves, roles, and AI loan data."""
import os
os.environ["MAINTENANCE_ENABLED"] = "false"
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_URL'] = f'sqlite:///{tmp}/test.db'
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import SessionLocal, engine
    from app import models
    from app.agent.tools import current_user_id_ctx, my_loans_tool, search_book_tool
    with TestClient(app) as c:
        def account(name):
            response = c.post('/users/', json={'email': f'{name}@example.com', 'password': 'testing-123', 'role': 'librarian'})
            assert response.json()['role'] == 'reader'
            token = c.post('/login/', data={'username': f'{name}@example.com', 'password': 'testing-123'}).json()['access_token']
            return response.json()['id'], {'Authorization': f'Bearer {token}'}
        owner, a = account('owner')
        reader, b = account('reader')
        admin, staff = account('staff')
        with SessionLocal() as db:
            db.get(models.User, admin).role = 'librarian'
            db.commit()
        body = {'name': 'Dune', 'author': 'Frank Herbert', 'category': 'Science fiction', 'description': 'A desert world.', 'isbn': '9780441172719', 'publication_year': 1965, 'cover_url': 'https://example.com/cover.jpg'}
        result = c.post('/books/', headers=a, json=body)
        assert result.status_code == 200, result.text
        book = result.json()['id']
        assert result.json()['available'] is True
        assert c.put(f'/books/{book}', headers=b, json=body).status_code == 403
        assert c.put(f'/books/{book}', headers=staff, json=body).status_code == 200
        assert c.get('/library/manage', headers=b).status_code == 403
        assert c.get('/library/manage', headers=staff).status_code == 200
        assert c.get(f'/users/{owner}', headers=b).status_code == 403
        assert c.get(f'/users/{owner}').status_code == 401
        assert c.post('/books/', headers=a, json={**body, 'cover_url': 'javascript:alert(1)'}).status_code == 422
        # Two readers compete for the same physical copy.
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda headers: c.post('/borrow/', headers=headers, json={'book_id': book, 'dir': 1}).status_code, [a, b]))
        assert sorted(responses) == [201, 409], responses
        assert c.get(f'/books/{book}').json()['available'] is False
        assert c.delete(f'/books/{book}', headers=staff).status_code == 409
        with SessionLocal() as db:
            loan = db.query(models.Borrow).one()
            borrower = loan.user_id
            loan.due_date = datetime.now(timezone.utc) - timedelta(days=1)
            db.commit()
        borrower_headers = a if borrower == owner else b
        other_headers = b if borrower == owner else a
        assert c.get('/library/mine', headers=borrower_headers).json()['loans'][0]['overdue'] is True
        assert c.get('/library/mine', headers=other_headers).json()['loans'] == []
        token = current_user_id_ctx.set(borrower)
        try:
            assert 'overdue: True' in my_loans_tool()
            assert f'/book/{book}' in search_book_tool('Dune')
        finally:
            current_user_id_ctx.reset(token)
        assert c.put(f'/library/reading/{book}', headers=a, json={'status': 'reading'}).status_code == 200
        assert c.get('/library/mine', headers=a).json()['reading'][0]['status'] == 'reading'
        assert c.get('/library/mine', headers=b).json()['reading'] == []
        assert c.put(f'/library/reading/{book}', headers=a, json={'status': 'bad'}).status_code == 422
        assert c.delete(f'/library/loans/{book}', headers=b).status_code == 403
        assert c.delete(f'/library/loans/{book}', headers=staff).status_code == 200
        assert c.get(f'/books/{book}').json()['available'] is True
        assert c.delete(f'/books/{book}', headers=staff).status_code == 204
        assert c.get('/library/mine', headers=a).json()['reading'] == []
    engine.dispose()
print('PASS: concurrent borrowing, availability, overdue dates, roles, profile privacy, metadata, reading shelves, AI loan data')
