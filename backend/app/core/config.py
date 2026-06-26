from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Database Copilot"
    SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite:///./ai_copilot.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # AI
    GEMINI_API_KEY: str = ""
    GEMINI_FLASH_MODEL: str = "gemini-2.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-2.5-pro"

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # Security
    BCRYPT_ROUNDS: int = 12
    MAX_QUERY_LENGTH: int = 2000
    QUERY_TIMEOUT_SECONDS: int = 30
    MAX_QUERY_ROWS: int = 1000
    MAX_UPLOAD_SIZE_MB: int = 10
    READ_ONLY_MODE: bool = True
    FERNET_KEY: str = ""

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()