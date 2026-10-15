from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
LEGACY_GEMINI_MODELS = {"gemini-2.5-flash"}


class Settings(BaseSettings):
    app_name: str = Field(default="ATLAS AI", validation_alias="ATLAS_APP_NAME")
    environment: str = Field(default="development", validation_alias="ATLAS_ENVIRONMENT")
    api_host: str = Field(default="127.0.0.1", validation_alias="ATLAS_API_HOST")
    api_port: int = Field(default=8000, validation_alias="ATLAS_API_PORT")
    log_level: str = Field(default="INFO", validation_alias="ATLAS_LOG_LEVEL")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default=DEFAULT_GEMINI_MODEL, validation_alias="GEMINI_MODEL")
    memory_backend: str = Field(default="local", validation_alias="ATLAS_MEMORY_BACKEND")
    local_db_path: str = Field(default="", validation_alias="ATLAS_LOCAL_DB_PATH")
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_key: str = Field(default="", validation_alias="SUPABASE_KEY")

    @field_validator("gemini_model", mode="before")
    @classmethod
    def migrate_legacy_gemini_model(cls, value: object) -> object:
        """Replace the retired default model so existing .env files keep working."""
        if isinstance(value, str) and value.strip() in LEGACY_GEMINI_MODELS:
            return DEFAULT_GEMINI_MODEL
        return value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
