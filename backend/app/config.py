from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "KTK ELOU-AVT Backend"
    app_version: str = "0.1.0"
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="KTK_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
