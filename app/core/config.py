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
    vault_root: str = Field(default="~/Developer/context-vault", validation_alias="VAULT_ROOT")
    vault_auto_commit: bool = Field(default=True, validation_alias="VAULT_AUTO_COMMIT")
    open_brain_api_token: str = Field(default="change-me", validation_alias="OPEN_BRAIN_API_TOKEN")


settings = Settings()
