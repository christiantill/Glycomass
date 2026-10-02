from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration from environment (prefix GLYCOMASS_)."""

    model_config = SettingsConfigDict(env_prefix="GLYCOMASS_", env_file=".env", extra="ignore")

    environment: str = "development"
    log_json: bool = False
    log_level: str = "INFO"
    slow_operation_ms: float = Field(default=1000, ge=0, allow_inf_nan=False)

    database_url: str = "sqlite+aiosqlite:///./glycomass.db"
    redis_url: str = "redis://localhost:6379"
    upload_dir: Path = Path("data/uploads")
    result_dir: Path = Path("data/results")
    max_upload_bytes: int = 250 * 1024 * 1024
    # Off in production while the identifier is being developed: no new uploads are
    # accepted, but existing job status pages and result downloads keep working.
    identifier_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
