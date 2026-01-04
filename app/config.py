from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    telegram_bot_token: str = ""  # Optional: for broadcast messaging

    class Config:
        env_file = ".env"


settings = Settings()