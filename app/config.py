from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./portfolio.db"
    aws_endpoint_url: str | None = None
    s3_bucket: str = "portfolio-exports"
    gemini_api_key: str | None = None
    midas_base_url: str = "https://www.getmidas.com/wp-json/midas-api/v1"
    env: Literal["dev", "test", "prod"] = "dev"
    signal_score_threshold: int = 2
    signal_history_days: int = 90
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


settings = Settings()
