from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings, BACKEND_DIR

url = make_url(settings.database_url)
if url.drivername != "sqlite":
    raise ValueError("DATABASE_URL must use sqlite:/// followed by a database file path")
if url.database and url.database != ":memory:":
    path = Path(url.database)
    if not path.is_absolute():
        url = url.set(database=str((BACKEND_DIR / path).resolve()))
engine = create_engine(url, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    with SessionLocal() as db:
        yield db
