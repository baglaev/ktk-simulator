from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "KTK ELOU-AVT Backend"
    app_version: str = "0.3.0"
    environment: str = "development"
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    simulation_auto_run: bool = True
    simulation_tick_interval_ms: int = Field(default=1_000, gt=0)
    database_url: str = "sqlite+pysqlite:///./ktk_simulator.sqlite3"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="KTK_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
