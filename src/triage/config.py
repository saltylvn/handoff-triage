"""The only place secrets are read. Fails at startup, not mid-request, if one is missing."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    gemini_api_key: str = Field(min_length=1)
    gemini_model: str = "gemini-3.5-flash-lite"
    webhook_secret: str = Field(min_length=32)
    token_encryption_key: str = Field(min_length=44, max_length=44)
    public_base_url: str = "http://localhost:3000"
    hubspot_client_id: str = Field(min_length=1)
    hubspot_client_secret: str = Field(min_length=1)
    slack_bot_token: str = Field(min_length=1)
    slack_signing_secret: str = Field(min_length=1)
    slack_channel_id: str = Field(min_length=1)
    slack_approver_ids: str = ""
    confidence_threshold: float = Field(default=0.9, ge=0, le=1)
    database_path: str = "./triage.sqlite"

    @property
    def approvers(self) -> frozenset[str]:
        return frozenset(
            part.strip() for part in self.slack_approver_ids.split(",") if part.strip()
        )

    @property
    def hubspot_redirect_uri(self) -> str:
        return f"{self.public_base_url.rstrip('/')}/oauth/hubspot/callback"
