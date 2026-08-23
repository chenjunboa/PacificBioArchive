from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    api_prefix: str = "/api/v1"
    local_jwt_secret: str = "local-development-secret-change-me"
    local_data_dir: Path = Path(".local-data")
    inference_mode: str = "stub"
    inference_url: str = "http://localhost:8081"
    model_version: str = "local-stub-v1"
    labels_path: Path = Path("labels.txt")
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    cognito_issuer: str = ""
    max_image_bytes: int = 20 * 1024 * 1024
    max_video_bytes: int = 100 * 1024 * 1024

    @property
    def database_path(self) -> Path:
        return self.local_data_dir / "bioarchive.sqlite3"


@lru_cache
def get_settings() -> Settings:
    return Settings()
