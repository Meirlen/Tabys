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

    class Config:
        env_file = ".env"
        extra = "forbid"  # Запрет дополнительных полей

@lru_cache
def get_settings() -> Settings:
    return Settings()
