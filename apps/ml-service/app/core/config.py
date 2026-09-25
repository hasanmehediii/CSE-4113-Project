from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore", env_prefix="ML_"
    )

    app_name: str = "DubsiBhai ML Service"
    model_path: Path = REPO_ROOT / "apps/ml-service/weights/classifier.joblib"


@lru_cache
def get_settings() -> Settings:
    return Settings()
