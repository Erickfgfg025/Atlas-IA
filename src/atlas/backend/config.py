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
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_key: str = Field(default="", validation_alias="SUPABASE_KEY")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
