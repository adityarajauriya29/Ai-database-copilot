from pydantic_settings import BaseSettings
from typing import List
import json
import os


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

    # AI / LLM routing
    # Primary is intentionally low-cost and token-efficient. Configure Groq/OpenRouter
    # only when you want automatic fallback providers.
    PRIMARY_LLM: str = "gemini"
    FALLBACK_LLM: str = "groq"
    OPTIONAL_LLM: str = "openrouter"

    GEMINI_API_KEY: str = ""
    GEMINI_FLASH_MODEL: str = "gemini-2.0-flash-lite"
    GEMINI_PRO_MODEL: str = "gemini-2.5-flash"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "deepseek/deepseek-chat-v3-0324:free"
    APP_URL: str = ""

    # CORS — default is permissive in development. In production set the env
    # var ALLOWED_ORIGINS to a JSON list of your real frontend URLs, or "*"
    # to allow every origin. This is the single most common reason the app
    # shows "Demo connection failed" when the browser calls the backend —
    # the server rejects the browser origin and the JSON `detail` never
    # reaches the toast.
    ALLOWED_ORIGINS: List[str] = ["*"]

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


def _parse_origins(raw):
    """Accept a JSON list, a comma-separated string, or '*'."""
    if isinstance(raw, list):
        return raw
    if not raw:
        return ["*"]
    raw = str(raw).strip()
    if raw == "*":
        return ["*"]
    try:
        v = json.loads(raw)
        if isinstance(v, list):
            return v
    except Exception:
        pass
    return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
# Normalize whatever came in from the env var into a real Python list
settings.ALLOWED_ORIGINS = _parse_origins(
    os.getenv("ALLOWED_ORIGINS", settings.ALLOWED_ORIGINS)
)
