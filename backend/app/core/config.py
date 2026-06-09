from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/cashflow_mvp"
    SECRET_KEY: str = "dev-secret-key"
    OPENWEATHER_API_KEY: str = ""
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "cashflow_verify"
    DEBUG: bool = True

    # Forecast config
    FORECAST_HORIZON_DAYS: int = 90
    MIN_HISTORY_DAYS: int = 14
    SAFETY_BUFFER_DAYS: int = 7

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()