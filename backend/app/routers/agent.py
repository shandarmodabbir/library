from uuid import uuid4
import hashlib
import json
from sqlalchemy.exc import IntegrityError
from ..database import SessionLocal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from agno.db.base import SessionType
from agno.db.sqlite import SqliteDb
from .. import models, oauth2
from ..config import settings, BACKEND_DIR
from ..agent.tools import current_user_id_ctx, current_request_id_ctx

router = APIRouter(prefix="/agent", tags=["Librarian"])
history_db = SqliteDb(db_file=str(BACKEND_DIR / "agent_sessions.db"))

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    session_id: str | None = None
    request_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=100)

class ChatResponse(BaseModel):
    response: str
    session_id: str
    actions: list[str] = Field(default_factory=list)


def visible_messages(session):
    return [
        {"role": message.role, "content": message.content}
        for message in session.get_messages()
        if message.role in ("user", "assistant") and isinstance(message.content, str)
        and message.content and not message.tool_calls
    ]


def owned_session(session_id, user_id):
    session = history_db.get_session(session_id, session_type=SessionType.AGENT, user_id=str(user_id))
    if session is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return session


@router.get("/sessions")
def list_sessions(current_user: models.User = Depends(oauth2.get_current_user)):
    sessions = history_db.get_sessions(
        session_type=SessionType.AGENT, user_id=str(current_user.id),
        sort_by="updated_at", sort_order="desc",
    )
    return [
        {"id": session.session_id,
         "title": (session.session_data or {}).get("session_name") or next((m["content"][:80] for m in visible_messages(session) if m["role"] == "user"), "Conversation"),
         "updated_at": session.updated_at}
        for session in sessions
    ]


@router.get("/sessions/{session_id}")
def get_session(session_id: str, current_user: models.User = Depends(oauth2.get_current_user)):
    session = owned_session(session_id, current_user.id)
    return {"id": session.session_id, "messages": visible_messages(session)}


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, current_user: models.User = Depends(oauth2.get_current_user)):
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be empty")
    user_id = current_user.id
    fingerprint = hashlib.sha256(json.dumps([message, body.session_id]).encode()).hexdigest()
    with SessionLocal() as db:
        record = models.ChatRequestRecord(user_id=user_id, request_id=body.request_id, fingerprint=fingerprint, session_id=body.session_id or str(uuid4()), status='running')
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            record = db.get(models.ChatRequestRecord, (user_id, body.request_id))
            if not record or record.fingerprint != fingerprint:
                raise HTTPException(409, 'This request ID belongs to a different message')
            if record.status == 'deleted':
                raise HTTPException(410, 'This conversation was deleted')
            if record.status == 'completed':
                return {'response': record.response, 'session_id': record.session_id, 'actions': action_results(db, user_id, body.request_id)}
            if record.status == 'running':
                raise HTTPException(409, 'This message is still processing. Retry later with the same message.')
            claimed = db.query(models.ChatRequestRecord).filter_by(user_id=user_id, request_id=body.request_id, status='failed').update({'status': 'running'})
            db.commit()
            if not claimed:
                raise HTTPException(409, 'This message is already processing')
        session_id = record.session_id
    token = current_user_id_ctx.set(user_id)
    request_token = current_request_id_ctx.set(body.request_id)
    try:
        if body.session_id:
            owned_session(body.session_id, user_id)
        if not settings.groq_api_key:
            raise HTTPException(503, 'AI librarian requires GROQ_API_KEY in backend/.env')
        from ..agent.library_agent import agent
        result = agent.run(message, user_id=str(user_id), session_id=session_id)
        with SessionLocal() as db:
            record = db.get(models.ChatRequestRecord, (user_id, body.request_id))
            record.status, record.response = 'completed', str(result.content or '')
            db.commit()
            return {'response': record.response, 'session_id': session_id, 'actions': action_results(db, user_id, body.request_id)}
    except Exception as exc:
        with SessionLocal() as db:
            record = db.get(models.ChatRequestRecord, (user_id, body.request_id))
            record.status = 'failed'
            db.commit()
            actions = action_results(db, user_id, body.request_id)
        if isinstance(exc, HTTPException):
            raise
        detail = 'The AI reply failed. You can retry this message safely.'
        if actions:
            detail += ' Completed actions: ' + '; '.join(actions)
        raise HTTPException(502, detail) from exc
    finally:
        current_user_id_ctx.reset(token)
        current_request_id_ctx.reset(request_token)


def action_results(db, user_id, request_id):
    return [a.result for a in db.query(models.AgentAction).filter_by(user_id=user_id, request_id=request_id).all()]

@router.get('/requests/{request_id}')
def request_status(request_id: str, user=Depends(oauth2.get_current_user)):
    with SessionLocal() as db:
        record = db.get(models.ChatRequestRecord, (user.id, request_id))
        if not record:
            raise HTTPException(404, 'Request not found')
        return {'status': record.status, 'actions': action_results(db, user.id, request_id)}


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)

@router.patch('/sessions/{session_id}')
def rename_session(session_id: str, body: RenameRequest, user=Depends(oauth2.get_current_user)):
    owned_session(session_id, user.id)
    title = body.title.strip()
    if not title:
        raise HTTPException(422, 'Title cannot be blank')
    saved = history_db.rename_session(session_id, SessionType.AGENT, title, user_id=str(user.id))
    if saved is None:
        raise HTTPException(404, "Conversation not found")
    return {'title': title}

@router.delete('/sessions/{session_id}')
def delete_session(session_id: str, user=Depends(oauth2.get_current_user)):
    owned_session(session_id, user.id)
    history_db.delete_session(session_id, user_id=str(user.id))
    with SessionLocal() as db:
        db.query(models.ChatRequestRecord).filter_by(user_id=user.id, session_id=session_id).update({'status': 'deleted', 'response': None})
        db.commit()
    return {'message': 'Conversation deleted'}
