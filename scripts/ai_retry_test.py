import os
os.environ['MAINTENANCE_ENABLED'] = 'false'
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_URL'] = f'sqlite:///{tmp}/library.db'
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import SessionLocal, engine
    from app.models import Book
    from app.config import settings
    from app.agent.library_agent import agent
    from app.agent.tools import create_book_tool
    attempts=[]
    def run(*args,**kwargs):
        result = create_book_tool('Retry Book','Author','Fiction')
        attempts.append(result)
        if len(attempts)==1:
            raise RuntimeError('Provider failed after action committed')
        return SimpleNamespace(content='Book saved')
    with TestClient(app) as c, patch.object(settings,'groq_api_key','test'), patch.object(agent,'run',side_effect=run):
        c.post('/users/',json={'email':'retry@example.com','password':'testing-123'})
        token=c.post('/login/',data={'username':'retry@example.com','password':'testing-123'}).json()['access_token']
        h={'Authorization':f'Bearer {token}'}
        body={'message':'Add a book','request_id':'stable-id'}
        r=c.post('/agent/chat',headers=h,json=body)
        assert r.status_code==502 and 'Completed actions:' in r.json()['detail'],r.text
        r=c.post('/agent/chat',headers=h,json=body)
        assert r.status_code==200 and len(r.json()['actions'])==1,r.text
        assert attempts[0]==attempts[1]
        replay=c.post('/agent/chat',headers=h,json=body)
        assert replay.json()==r.json() and len(attempts)==2
        assert c.post('/agent/chat',headers=h,json={**body,'message':'Different'}).status_code==409
        assert c.get('/agent/requests/stable-id',headers=h).json()['status']=='completed'
        with SessionLocal() as db:
            assert db.query(Book).count()==1
    engine.dispose()
print('PASS: failed AI reply retry creates only one book; completed response replay, request binding, action status')
