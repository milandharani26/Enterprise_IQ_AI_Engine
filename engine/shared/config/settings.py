from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv

# Resolve engine/.env deterministically so DATABASE_URL etc. are identical in
# debugger and terminal runs regardless of current working directory.
_engine_root = Path(__file__).resolve().parents[2]
_env_file = _engine_root / ".env"
load_dotenv(_env_file)
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_platform",
        alias="DATABASE_URL",
    )
    schema_name: str = Field(default="", alias="SCHEMA_NAME")
    # LLM Providers
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    # App
    app_name: str = Field(default="ai-platform-engine", alias="APP_NAME")
    env: str = Field(default="local", alias="ENV")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_secret_key: str = Field(default="change-me", alias="APP_SECRET_KEY")
    cors_origins: str = Field(
        default="http://127.0.0.1:8080,http://localhost:8080,http://127.0.0.1:8000,http://localhost:8000",
        alias="CORS_ORIGINS",
    )

    # Encryption
    secrets_encryption_key: str = Field(default="", alias="SECRETS_ENCRYPTION_KEY")
    password_secret: str = Field(default="iconflux", alias="PASSWORD_SECRET")

    # JWT/Auth
    jwt_secret: str = Field(default="dev-secret-do-not-use-in-production", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_min: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MIN")
    refresh_token_expire_min: int = Field(default=30, alias="REFRESH_TOKEN_EXPIRE_MIN")

    # Assistant runtime (preload + chat graph)
    # mock_json: graphs from engine/assistant/mocks JSON (preloader keys = JSON assistant_id; resolve from DB row via assistant_code)
    # database: graphs from assistant.assistants rows (preloader keys = str(assistant_id UUID))
    assistant_config_source: str = Field(
        default="mock_json",
        alias="ASSISTANT_CONFIG_SOURCE",
        description="mock_json | database — where assistant runtime config is loaded at startup",
    )

    # Defaults
    default_llm_provider: str = Field(default="anthropic", alias="DEFAULT_LLM_PROVIDER")
    default_llm_model: str = Field(default="claude-sonnet-4-20250514", alias="DEFAULT_LLM_MODEL")
    default_llm_max_tokens: int = Field(default=4096, alias="DEFAULT_LLM_MAX_TOKENS")
    default_llm_temperature: float = Field(default=0.1, alias="DEFAULT_LLM_TEMPERATURE")
    llm_request_timeout_seconds: int = Field(
        default=30,
        alias="LLM_REQUEST_TIMEOUT_SECONDS",
        description="Per-request timeout for chat model calls.",
    )
    llm_max_retries: int = Field(
        default=1,
        alias="LLM_MAX_RETRIES",
        description="Max retries for transient LLM API errors (incl. rate limits).",
    )
    llm_config_priority: str = Field(
        default="assistant",
        alias="LLM_CONFIG_PRIORITY",
        description="assistant | env — whether assistant.llm_config or DEFAULT_LLM_* takes precedence",
    )

    # Redis (optional)
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    # database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_platform", alias="DATABASE_URL")
    # database_url: str = Field(default="", alias="DATABASE_URL")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file_path: str = Field(default="logs/queries.log", alias="LOG_FILE_PATH")
    log_sql_queries: bool = Field(default=True, alias="LOG_SQL_QUERIES")

    # ===== DOCUMENT INGESTION: CLOUD STORAGE (AWS S3) =====
    aws_s3_enabled: bool = Field(default=True, alias="AWS_S3_ENABLED", description="Enable S3 document fetching")
    aws_s3_bucket: str = Field(default="", alias="AWS_S3_BUCKET", description="S3 bucket name for documents")
    aws_s3_region: str = Field(default="us-east-1", alias="AWS_S3_REGION", description="AWS region")

    # ===== DOCUMENT INGESTION: GOOGLE CLOUD STORAGE =====
    gcs_enabled: bool = Field(default=False, alias="GCS_ENABLED", description="Enable GCS document fetching")
    gcs_project_id: str = Field(default="", alias="GCS_PROJECT_ID", description="GCP project ID")
    gcs_bucket: str = Field(default="", alias="GCS_BUCKET", description="GCS bucket name for documents")
    gcs_credentials_path: str = Field(default="", alias="GCS_CREDENTIALS_PATH", description="Path to GCP service account JSON key file")

    # ===== DOCUMENT INGESTION: EMBEDDING =====
    # Preferred embedding env vars
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER", description="Embedding provider: openai, groq")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL", description="Embedding model ID")
    # Backward-compatible aliases used in some local env files
    default_embedding_provider: str = Field(default="", alias="DEFAULT_EMBEDDING_PROVIDER")
    default_embedding_model: str = Field(default="", alias="DEFAULT_EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS", description="Vector dimensions (1536 for OpenAI text-embedding-3-small)")
    embedding_batch_size: int = Field(default=100, alias="EMBEDDING_BATCH_SIZE", description="Batch size for embedding API calls")

    # ===== DOCUMENT INGESTION: PROCESSING =====
    max_document_size_mb: int = Field(default=50, alias="MAX_DOCUMENT_SIZE_MB", description="Maximum document file size in MB")
    chunk_size_tokens: int = Field(default=512, alias="CHUNK_SIZE_TOKENS", description="Target tokens per chunk")
    chunk_overlap_tokens: int = Field(default=50, alias="CHUNK_OVERLAP_TOKENS", description="Overlap between chunks in tokens")
    max_chunk_size_tokens: int = Field(default=2048, alias="MAX_CHUNK_SIZE_TOKENS", description="Hard limit for chunk size")
    supported_mimetypes: str = Field(
        default="application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/csv,application/vnd.openxmlformats-officedocument.presentationml.presentation",
        alias="SUPPORTED_MIMETYPES",
        description="Comma-separated MIME types allowed for ingestion",
    )

    # ===== DOCUMENT INGESTION: ASYNC TASKS =====
    enable_async_indexing: bool = Field(default=True, alias="ENABLE_ASYNC_INDEXING", description="Enable background async indexing")
    indexing_task_timeout_seconds: int = Field(default=3600, alias="INDEXING_TASK_TIMEOUT_SECONDS", description="Timeout for indexing job in seconds")
    indexing_task_retries: int = Field(default=3, alias="INDEXING_TASK_RETRIES", description="Number of retries for failed indexing jobs")

    # ===== DOCUMENT INGESTION: PGVECTOR =====
    vector_store_type: str = Field(default="postgres", alias="VECTOR_STORE_TYPE", description="Vector store type (only postgres in Phase 1)")
    pgvector_search_type: str = Field(default="cosine", alias="PGVECTOR_SEARCH_TYPE", description="Similarity metric: cosine, l2, innerproduct")
    pgvector_ivf_lists: int = Field(default=100, alias="PGVECTOR_IVF_LISTS", description="IVF index parameter (lists count)")

    # ===== PHASE 2: CELERY + REDIS =====
    celery_broker_url: str = Field(default="redis://localhost:6379/0", alias="CELERY_BROKER_URL", description="Celery broker (task queue)")
    celery_result_backend: str = Field(default="redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND", description="Celery result backend")
    celery_task_serializer: str = Field(default="json", alias="CELERY_TASK_SERIALIZER")
    celery_accept_content: list = Field(default=["json"], alias="CELERY_ACCEPT_CONTENT")
    celery_result_serializer: str = Field(default="json", alias="CELERY_RESULT_SERIALIZER")
    celery_timezone: str = Field(default="UTC", alias="CELERY_TIMEZONE")
    celery_enable_utc: bool = Field(default=True, alias="CELERY_ENABLE_UTC")
    celery_task_track_started: bool = Field(default=True, alias="CELERY_TASK_TRACK_STARTED")
    celery_task_time_limit: int = Field(default=600, alias="CELERY_TASK_TIME_LIMIT", description="Hard limit seconds")
    celery_task_soft_time_limit: int = Field(default=540, alias="CELERY_TASK_SOFT_TIME_LIMIT", description="Soft limit seconds")
    celery_task_max_retries: int = Field(default=3, alias="CELERY_TASK_MAX_RETRIES")
    celery_task_default_retry_delay: int = Field(default=60, alias="CELERY_TASK_DEFAULT_RETRY_DELAY")
    celery_worker_prefetch_multiplier: int = Field(default=4, alias="CELERY_WORKER_PREFETCH_MULTIPLIER")
    celery_worker_max_tasks_per_child: int = Field(default=1000, alias="CELERY_WORKER_MAX_TASKS_PER_CHILD")
    celery_result_expires: int = Field(default=3600, alias="CELERY_RESULT_EXPIRES", description="Result TTL seconds")
    use_celery_for_indexing: bool = Field(default=False, alias="USE_CELERY_FOR_INDEXING", description="Use Celery for indexing (Phase 2); else Phase 1 background task")

    # ===== PHASE 2: EMBEDDING (OpenAI) =====
    embedding_max_retries: int = Field(default=3, alias="EMBEDDING_MAX_RETRIES")
    embedding_timeout_seconds: int = Field(default=120, alias="EMBEDDING_TIMEOUT_SECONDS")
    embedding_model_cost_per_1m_tokens: float = Field(default=0.02, alias="EMBEDDING_MODEL_COST_PER_1M_TOKENS", description="OpenAI cost per 1M tokens")

    # ===== PHASE 2: WEBHOOKS =====
    webhook_success_endpoint: str = Field(default="", alias="WEBHOOK_SUCCESS_ENDPOINT", description="EnterpriseGPT success webhook URL")
    webhook_failure_endpoint: str = Field(default="", alias="WEBHOOK_FAILURE_ENDPOINT", description="EnterpriseGPT failure webhook URL")
    webhook_status_endpoint: str = Field(default="", alias="WEBHOOK_STATUS_ENDPOINT", description="EnterpriseGPT simple status webhook URL")
    webhook_secret: str = Field(default="", alias="WEBHOOK_SECRET", description="HMAC signing secret (min 32 chars)")
    webhook_timeout: int = Field(default=10, alias="WEBHOOK_TIMEOUT", description="Request timeout seconds")

    # ===== MEETING AGENT =====
    meeting_bot_base_url: str = Field(
        default="http://46.224.60.121:8000",
        alias="MEETING_BOT_BASE_URL",
        description="Recorder bot server URL: full API root (…/api/v1) or origin only (e.g. http://host:8000 — /api/v1 is appended automatically)",
    )
    meeting_bot_default_provider: str = Field(default="google_meet", alias="MEETING_BOT_DEFAULT_PROVIDER")
    meeting_bot_default_name: str = Field(default="Meeting Recorder Bot", alias="MEETING_BOT_DEFAULT_NAME")
    meeting_bot_webhook_url: str = Field(
        default="",
        alias="MEETING_BOT_WEBHOOK_URL",
        description="Optional override for bot callback base ({scheme}://{host}/api/v1/agents). Legacy …/api/v1 is auto-corrected. If empty, POST /agents/meeting/process derives it from the request.",
    )
    meeting_bot_webhook_secret: str = Field(default="", alias="MEETING_BOT_WEBHOOK_SECRET", description="Shared secret for verifying bot webhooks (X-Webhook-Signature)")
    meeting_cron_interval_seconds: int = Field(default=5, alias="MEETING_CRON_INTERVAL_SECONDS")
    meeting_cron_enabled: bool = Field(default=False, alias="MEETING_CRON_ENABLED", description="Enable bot status reconciliation cron")
    meeting_recording_s3_bucket: str = Field(default="", alias="MEETING_RECORDING_S3_BUCKET")
    meeting_recording_s3_prefix: str = Field(default="agents/meetings", alias="MEETING_RECORDING_S3_PREFIX")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_audio_api_version: str = Field(default="2024-06-01", alias="AZURE_OPENAI_AUDIO_API_VERSION")
    azure_openai_audio_deployment: str = Field(default="whisper-001", alias="AZURE_OPENAI_AUDIO_DEPLOYMENT")
    azure_openai_audio_model: str = Field(default="whisper-1", alias="AZURE_OPENAI_AUDIO_MODEL")

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Backward-compatible uppercase accessors used by legacy modules.
    @property
    def DATABASE_URL(self) -> str:
        return self.database_url

    @property
    def REDIS_URL(self) -> str:
        return self.redis_url

    @property
    def ENV(self) -> str:
        return self.env

    @property
    def APP_NAME(self) -> str:
        return self.app_name

    @property
    def CORS_ORIGINS(self) -> str:
        return self.cors_origins

    @property
    def JWT_SECRET(self) -> str:
        return self.jwt_secret

    @property
    def JWT_ALGORITHM(self) -> str:
        return self.jwt_algorithm

    @property
    def ACCESS_TOKEN_EXPIRE_MIN(self) -> int:
        return self.access_token_expire_min

    @property
    def REFRESH_TOKEN_EXPIRE_MIN(self) -> int:
        return self.refresh_token_expire_min

    @property
    def PASSWORD_SECRET(self) -> str:
        return self.password_secret

    @field_validator("meeting_bot_base_url", mode="after")
    @classmethod
    def _meeting_bot_base_url_non_empty(cls, value: str) -> str:
        """Treat blank MEETING_BOT_BASE_URL as unset so the default bot URL is used."""
        stripped = (value or "").strip()
        if not stripped:
            return "http://46.224.60.121:8000"
        return stripped


@lru_cache()
def get_settings() -> Settings:
    return Settings()
