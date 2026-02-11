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

    # OTP Bypass Settings (for development/testing)
    otp_bypass_enabled: bool = True  # Enable OTP bypass mode
    otp_bypass_code: str = "950826"  # Master OTP code that always works

    class Config:
        env_file = ".env"


settings = Settings()