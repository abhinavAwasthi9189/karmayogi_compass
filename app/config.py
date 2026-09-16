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
    LLM_MODEL: str = "gemini/gemini-3.6-flash"
    GEMINI_API_KEY: str = ""

    # Comma-separated list of allowed frontend origins, e.g.
    # "https://myapp.vercel.app,https://mycustomdomain.com". Defaults to "*"
    # for local dev -- set explicitly in production.
    CORS_ORIGINS: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
