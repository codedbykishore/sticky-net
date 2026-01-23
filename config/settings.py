"""Application settings using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API
    api_key: str
    port: int = 8080
    debug: bool = False

    # Google Cloud
    google_cloud_project: str
    vertex_ai_location: str = "us-central1"
    google_application_credentials: str | None = None

    # Firestore
    firestore_collection: str = "conversations"
    firestore_emulator_host: str | None = None

    # Agent
    llm_model: str = "gemini-3-pro"
    llm_temperature: float = 0.7
    max_engagement_turns: int = 50


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
