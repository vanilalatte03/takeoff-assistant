from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "Takeoff Assistant API"
    app_version: str = "0.1.0"
    ai_api_key: SecretStr = SecretStr("")
    ai_model: str = ""
    ai_vision_model: str = ""
    data_dir: Path = REPO_ROOT / "data"
    uploads_dir: Path = REPO_ROOT / "data" / "uploads"
    rendered_pages_dir: Path = REPO_ROOT / "data" / "rendered"
    exports_dir: Path = REPO_ROOT / "exports"
    database_url: str = f"sqlite:///{(REPO_ROOT / 'data' / 'takeoff_assistant.db').as_posix()}"

    model_config = SettingsConfigDict(env_prefix="TAKEOFF_")


settings = Settings()
