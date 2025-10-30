"""Configuration settings for data_postgres_api service."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str

    # Application
    app_name: str = "data_postgres_api"
    log_level: str = "INFO"

    # API
    api_v1_prefix: str = "/api/v1"

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False


settings = Settings()
