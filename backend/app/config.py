from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    database_url: str | None = None
    database_hostname: str = "localhost"
    database_port: str = "5432"
    database_password: str = ""
    database_name: str = "library"
    database_username: str = "postgres"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_from: str = ""
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    maintenance_enabled: bool = True
    backup_dir: str = str(BACKEND_DIR / "backups")
    google_api_key: str = ""
    groq_api_key: str = ""

    model_config = SettingsConfigDict(env_file=(BACKEND_DIR / ".env", BACKEND_DIR / ".env.local"))

settings = Settings()
