from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRES_DB: str
    POSTGRES_DB_HOST: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    PGADMIN_DEFAULT_EMAIL: str
    PGADMIN_DEFAULT_PASSWORD: str
    OPEN_AI_API_KEY: str
    WHATSAPP_API_KEY: str
    WHATSAPP_INSTANCE: str
    MOBIZON_API_KEY: str
    telegram_bot_token: str = ""  # Optional: for broadcast messaging

    # Resend API configuration for email notifications
    RESEND_API_KEY: str = ""  # Resend API key
    RESEND_FROM_EMAIL: str = ""  # Verified sender email (e.g., noreply@yourdomain.com)
    RESEND_FROM_NAME: str = "SARYARQA JASTARY"  # Sender name in emails

    class Config:
        env_file = ".env"
        extra = "ignore"  # Игнорировать дополнительные поля

@lru_cache
def get_settings() -> Settings:
    return Settings()
