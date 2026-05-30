from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    dart_api_key: str = ""
    naver_client_id: str = ""
    naver_client_secret: str = ""
    ecos_api_key: str = ""
    anthropic_api_key: str = ""

    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Shared secret protecting cost-incurring / data-exposing API routes.
    # Empty = those routes are disabled (503) rather than open.
    api_token: str = ""

    classifier_model: str = "claude-sonnet-4-6"
    summary_model: str = "claude-haiku-4-5-20251001"

    max_items_per_section: int = 15
    request_timeout_seconds: float = 20.0

    @property
    def enabled_notifiers(self) -> list[str]:
        names = []
        if self.discord_webhook_url:
            names.append("discord")
        if self.telegram_bot_token and self.telegram_chat_id:
            names.append("telegram")
        return names
