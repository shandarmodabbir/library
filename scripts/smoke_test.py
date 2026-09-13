"""Exercise the API against an isolated temporary database."""
import os
os.environ["MAINTENANCE_ENABLED"] = "false"
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_URL'] = f'sqlite:///{tmp}/test.db'
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import engine
    with TestClient(app) as client:
        credentials = {'email': 'reader@example.com', 'password': 'test-password-123'}
        assert client.post('/users/', json=credentials).status_code == 201
        assert client.post('/users/', json=credentials).status_code == 409
        result = client.post('/login/', data={'username': credentials['email'], 'password': credentials['password']})
        assert result.status_code == 200, result.text
        headers = {'Authorization': f'Bearer {result.json()["access_token"]}'}
        book = {'name': 'Test Book', 'author': 'Test Author', 'category': 'Fiction'}
        result = client.post('/books/', json=book, headers=headers)
        assert result.status_code == 200, result.text
        book_id = result.json()['id']
        assert len(client.get('/books/?name=Test').json()) == 1
        assert client.post('/borrow/', json={'book_id': book_id, 'dir': 1}, headers=headers).status_code == 201
        assert client.get('/borrow/mine', headers=headers).json()[0]['id'] == book_id
        assert client.post('/borrow/', json={'book_id': book_id, 'dir': 0}, headers=headers).status_code == 201
        assert client.get('/borrow/mine', headers=headers).json() == []
        assert client.put(f'/books/{book_id}', json={**book, 'name': 'Updated'}, headers=headers).status_code == 200
        assert client.delete(f'/books/{book_id}', headers=headers).status_code == 204
        assert client.get('/books/').json() == []
        assert client.get('/borrow/mine').status_code == 401
    engine.dispose()
print('PASS: registration, duplicate email, login, search, create, borrow, return, update, delete, authentication')
