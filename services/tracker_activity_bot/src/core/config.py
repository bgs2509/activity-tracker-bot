"""Configuration settings for tracker_activity_bot service."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram Bot
    telegram_bot_token: str

    # Data API
    data_api_url: str

    # Redis
    redis_url: str

    # AI Integration (OpenRouter)
    openrouter_api_key: str | None = None

    # Application
    app_name: str = "tracker_activity_bot"
    log_level: str = "INFO"

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False


settings = Settings()
