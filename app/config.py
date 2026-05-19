from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./portfolio.db"
    aws_endpoint_url: str | None = None
    gemini_api_key: str | None = None
    midas_base_url: str = "https://www.getmidas.com/wp-json/midas-api/v1"
    env: Literal["dev", "test", "prod"] = "dev"


settings = Settings()
