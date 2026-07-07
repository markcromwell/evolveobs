from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "EVOLVE Observability"
    version: str = "0.1.0"
    database_url: str = "sqlite:///./app.db"  # override via env for Postgres

    x_api_key: str = ""
    mcp_url: str = Field(
        "http://mcp-internal",
        validation_alias=AliasChoices("mcp_url", "uat_mcp_url")
    )
    request_timeout: float = 5.0


settings = Settings()

