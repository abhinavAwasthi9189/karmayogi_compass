"""Central application configuration, loaded from environment variables / .env"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Karmayogi Compass"
    SECRET_KEY: str = "dev-secret-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    ALGORITHM: str = "HS256"
    DATABASE_URL: str = "sqlite:///./karmayogi_compass.db"

    IGOT_MODE: str = "mock"  # "mock" | "live"
    IGOT_BASE_URL: str = "https://igot.gov.in/api"
    IGOT_API_KEY: str = ""

    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini/gemini-2.5-flash"
    GEMINI_API_KEY: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
