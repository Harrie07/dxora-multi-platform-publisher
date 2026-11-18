from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    discord_webhook_url: str = ""
    github_token: str = ""
    discord_guild_id: str = ""

    bluesky_handle: str = ""
    bluesky_app_password: str = ""
    bluesky_pds_url: str = "https://bsky.social"

    mastodon_base_url: str = "https://mastodon.social"
    mastodon_access_token: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()