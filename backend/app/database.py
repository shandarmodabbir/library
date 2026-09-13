from sqlalchemy import create_engine, event, URL
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

url = settings.database_url or URL.create(
    "postgresql+psycopg", username=settings.database_username,
    password=settings.database_password, host=settings.database_hostname,
    port=int(settings.database_port), database=settings.database_name,
)
engine = create_engine(url, connect_args={"check_same_thread": False} if str(url).startswith("sqlite") else {})
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    with SessionLocal() as db:
        yield db
