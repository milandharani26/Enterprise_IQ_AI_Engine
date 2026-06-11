from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env from engine root so it works regardless of cwd
_api_root = Path(__file__).resolve().parent.parent
_env_file = _api_root / ".env"


# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(
#         env_file=_env_file,
#         extra="ignore",
#     )

#     """App-level settings (auth, DB, Redis, CORS). Ingestion/Celery use config.settings."""
#     APP_NAME: str = "ai-platform-engine"
#     ENV: str = "local"
#     DATABASE_URL: str = "postgresql+asyncpg://ai_user:ai_pass@localhost:5432/ai_platform"
#     # JWT (for auth); set in .env or env in production; default for local/Docker only
#     JWT_SECRET: str = "dev-secret-do-not-use-in-production"
#     JWT_ALGORITHM: str = "HS256"
#     ACCESS_TOKEN_EXPIRE_MIN: int = 15
#     REFRESH_TOKEN_EXPIRE_MIN: int = 30
#     REDIS_URL: str = "redis://localhost:6379/0"
#     PASSWORD_SECRET: str = "iconflux"
#     CORS_ORIGINS: str = "http://127.0.0.1:8080,http://localhost:8080,http://127.0.0.1:8000,http://localhost:8000"



# settings = Settings()
