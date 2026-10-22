from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="ATLAS AI", validation_alias="ATLAS_APP_NAME")
    environment: str = Field(default="development", validation_alias="ATLAS_ENVIRONMENT")
    api_host: str = Field(default="127.0.0.1", validation_alias="ATLAS_API_HOST")
    api_port: int = Field(default=8000, validation_alias="ATLAS_API_PORT")
    log_level: str = Field(default="INFO", validation_alias="ATLAS_LOG_LEVEL")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", validation_alias="GEMINI_MODEL")
    chat_provider: str = Field(default="gemini", validation_alias="ATLAS_CHAT_PROVIDER")
    openjarvis_base_url: str = Field(default="", validation_alias="OPENJARVIS_BASE_URL")
    openjarvis_model: str = Field(default="default", validation_alias="OPENJARVIS_MODEL")
    openjarvis_api_key: str = Field(default="", validation_alias="OPENJARVIS_API_KEY")
    hermes_agent_enabled: bool = Field(default=False, validation_alias="HERMES_AGENT_ENABLED")
    hermes_agent_path: str = Field(default="", validation_alias="HERMES_AGENT_PATH")
    hermes_agent_model: str = Field(default="", validation_alias="HERMES_AGENT_MODEL")
    hermes_agent_task_timeout_seconds: int = Field(
        default=90,
        ge=10,
        le=300,
        validation_alias="HERMES_AGENT_TASK_TIMEOUT_SECONDS",
    )
    memory_backend: str = Field(default="local", validation_alias="ATLAS_MEMORY_BACKEND")
    local_db_path: str = Field(default="", validation_alias="ATLAS_LOCAL_DB_PATH")
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_key: str = Field(default="", validation_alias="SUPABASE_KEY")
    fish_audio_api_key: str = Field(default="", validation_alias="FISH_AUDIO_API_KEY")
    fish_audio_reference_id: str = Field(default="", validation_alias="FISH_AUDIO_REFERENCE_ID")
    fish_audio_model: str = Field(default="s2.1-pro-free", validation_alias="FISH_AUDIO_MODEL")
    max_audio_upload_mb: int = Field(
        default=20,
        ge=1,
        le=50,
        validation_alias="ATLAS_MAX_AUDIO_UPLOAD_MB",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
