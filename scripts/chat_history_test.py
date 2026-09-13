"""Test persisted conversations and ownership without an AI provider call."""
import os
os.environ["MAINTENANCE_ENABLED"] = "false"
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from time import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_URL'] = f'sqlite:///{tmp}/library.db'
    from fastapi.testclient import TestClient
    from agno.db.sqlite import SqliteDb
    from agno.db.base import SessionType
    from agno.session.agent import AgentSession
    from agno.run.agent import RunOutput
    from agno.run.base import RunStatus
    from agno.models.message import Message
    from app.main import app
    from app.routers import agent as router
    from app.agent.library_agent import agent
    from app.database import engine
    from app.agent.tools import current_user_id_ctx

    history = SqliteDb(db_file=f'{tmp}/history.db')
    def fake_run(message, user_id, session_id):
        session = history.get_session(session_id, session_type=SessionType.AGENT) or AgentSession(
            session_id=session_id, user_id=user_id, agent_id='test', created_at=int(time()))
        assert current_user_id_ctx.get() == int(user_id)
        run = RunOutput(status=RunStatus.completed, run_id=str(time()), agent_id='test', content='Saved reply', messages=[
            Message(role='user', content=message), Message(role='assistant', content='Saved reply')])
        session.upsert_run(run)
        session.updated_at = int(time())
        history.upsert_session(session)
        history.upsert_run(run, session_id=session_id, user_id=user_id, run_index=len(session.runs) - 1)
        return run

    with patch.object(router, 'history_db', history), patch.object(router.settings, 'groq_api_key', 'test'), patch.object(agent, 'run', side_effect=fake_run), TestClient(app) as client:
        def login(email):
            assert client.post('/users/', json={'email': email, 'password': 'test-password'}).status_code == 201
            token = client.post('/login/', data={'username': email, 'password': 'test-password'}).json()['access_token']
            return {'Authorization': f'Bearer {token}'}
        first = login('first@example.com')
        second = login('second@example.com')
        assert client.get('/agent/sessions').status_code == 401
        assert client.get('/agent/sessions', headers=first).json() == []
        result = client.post('/agent/chat', headers=first, json={'message': 'Find a novel'})
        assert result.status_code == 200, result.text
        session_id = result.json()['session_id']
        assert current_user_id_ctx.get() is None
        result = client.post('/agent/chat', headers=first, json={'message': 'Another one', 'session_id': session_id})
        assert result.status_code == 200, result.text
        assert len(client.get(f'/agent/sessions/{session_id}', headers=first).json()['messages']) == 4, client.get(f'/agent/sessions/{session_id}', headers=first).json()
        listing = client.get('/agent/sessions', headers=first).json()
        assert listing[0]['title'] == 'Find a novel'
        assert client.get('/agent/sessions', headers=second).json() == []
        assert client.get(f'/agent/sessions/{session_id}', headers=second).status_code == 404
        assert client.post('/agent/chat', headers=second, json={'message': 'intrude', 'session_id': session_id}).status_code == 404
        result = client.post('/agent/chat', headers=first, json={'message': 'New topic'})
        assert result.json()['session_id'] != session_id
        assert len(client.get('/agent/sessions', headers=first).json()) == 2
        assert client.post('/agent/chat', headers=first, json={'message': '   '}).status_code == 422
        # Reopen through a fresh DB connection, as after a server restart.
        with patch.object(router, 'history_db', SqliteDb(db_file=f'{tmp}/history.db')):
            assert len(client.get(f'/agent/sessions/{session_id}', headers=first).json()['messages']) == 4, client.get(f'/agent/sessions/{session_id}', headers=first).json()
        assert client.patch(f'/agent/sessions/{session_id}', headers=second, json={'title': 'Intrude'}).status_code == 404
        assert client.delete(f'/agent/sessions/{session_id}', headers=second).status_code == 404
        assert client.patch(f'/agent/sessions/{session_id}', headers=first, json={'title': 'Reading plans'}).status_code == 200
        assert any(s['title'] == 'Reading plans' for s in client.get('/agent/sessions', headers=first).json())
        with patch.object(router, 'history_db', SqliteDb(db_file=f'{tmp}/history.db')):
            assert any(s['title'] == 'Reading plans' for s in client.get('/agent/sessions', headers=first).json())
        assert client.patch(f'/agent/sessions/{session_id}', headers=first, json={'title': '   '}).status_code == 422
        assert client.delete(f'/agent/sessions/{session_id}', headers=first).status_code == 200
        assert client.get(f'/agent/sessions/{session_id}', headers=first).status_code == 404
    engine.dispose()
print('PASS: new chats, history, continuation, persistence, user isolation, authentication, blank messages')
