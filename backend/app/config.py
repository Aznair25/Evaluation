from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://cefr:cefr_pass@localhost:5432/cefr_db"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    frontend_url: str = "http://localhost:3000"

    # Deepgram
    deepgram_api_key: str = ""

    # Azure Speech
    azure_speech_key: str = ""
    azure_speech_region: str = "eastus"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_s3_region: str = "us-east-1"

    # Audio
    audio_retention_days: int = 0
    max_audio_size_mb: int = 200

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
