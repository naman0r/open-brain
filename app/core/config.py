from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Open Brain"
    app_env: str = "dev"
    api_version: str = "v1"
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", validation_alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(default="", validation_alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_db_url: str = Field(default="", validation_alias="SUPABASE_DB_URL")
    open_brain_api_token: str = Field(default="change-me", validation_alias="OPEN_BRAIN_API_TOKEN")
    embedding_provider: str = Field(default="local", validation_alias="EMBEDDING_PROVIDER")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_embed_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="OPENAI_EMBED_MODEL",
    )
    retrieval_score_threshold: float = Field(default=0.15, validation_alias="RETRIEVAL_SCORE_THRESHOLD")
    retrieval_max_top_k: int = Field(default=50, validation_alias="RETRIEVAL_MAX_TOP_K")


settings = Settings()
