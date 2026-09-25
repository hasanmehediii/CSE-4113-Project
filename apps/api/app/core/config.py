from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    api_cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    ml_service_url: str = "http://127.0.0.1:8001"


@lru_cache
def get_settings() -> Settings:
    return Settings()
