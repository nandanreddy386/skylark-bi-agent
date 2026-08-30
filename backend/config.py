"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Monday.com
    monday_api_token: str = ""
    deals_board_id: str = ""
    work_orders_board_id: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # App
    app_name: str = "Skylark BI Agent"
    debug: bool = False

    # CORS
    frontend_url: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
