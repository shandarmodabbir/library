from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    database_url: str = "sqlite:///./library.db"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    maintenance_enabled: bool = True
    backup_dir: str = str(BACKEND_DIR / "backups")
    google_api_key: str = ""
    groq_api_key: str = ""

    model_config = SettingsConfigDict(extra="ignore", env_file=(BACKEND_DIR / ".env", BACKEND_DIR / ".env.local"))

settings = Settings()
