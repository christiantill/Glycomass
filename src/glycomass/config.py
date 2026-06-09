from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration from environment (prefix GLYCOMASS_)."""

    model_config = SettingsConfigDict(env_prefix="GLYCOMASS_", env_file=".env", extra="ignore")

    environment: str = "development"
    log_json: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
