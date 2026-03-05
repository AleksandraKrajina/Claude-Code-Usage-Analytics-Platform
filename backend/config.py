"""Application configuration and environment settings."""

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database: SQLite by default (no setup). Set DATABASE_URL for PostgreSQL.
    database_url: str = "sqlite:///./data/claude_analytics.db"
    
    # API
    api_prefix: str = "/api/v1"
    debug: bool = False
    
    # Data paths
    telemetry_logs_path: Optional[str] = None
    employees_csv_path: Optional[str] = None

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
