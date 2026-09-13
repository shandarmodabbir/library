from fastapi import FastAPI
from . import models, database
from .routers import auth, book, borrow, user, agent, library, isbn




from .migrations import upgrade
upgrade()



from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
import asyncio
from .config import settings
from .services.maintenance import run_maintenance

@asynccontextmanager
async def lifespan(app):
    # The local launcher runs one worker. Recover requests interrupted by its previous exit.
    with database.SessionLocal() as db:
        db.query(models.ChatRequestRecord).filter_by(status='running').update({'status': 'failed'})
        db.commit()
    task = asyncio.create_task(run_maintenance()) if settings.maintenance_enabled else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

app = FastAPI(title="Library API", description="Library catalog, circulation, reservations, and assistant services.", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Library API"}


app.include_router(auth.router)
app.include_router(isbn.router)
app.include_router(book.router)
app.include_router(borrow.router)
app.include_router(user.router)
app.include_router(agent.router)
app.include_router(library.router)
