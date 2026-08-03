from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str
    telegram_bot_username: str = "enigmapnbot"
    admin_telegram_ids: list[int] = []
    api_internal_url: str = "http://api:8000"
    bot_api_token: str = "dev-bot-api-token"
    brand_name: str = "Enigma_PN"
    support_telegram: str = "@alexkr1t"
    domain: str = "bigwinzone.ru"

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def parse_ids(cls, value):
        if not value:
            return []
        if isinstance(value, list):
            return [int(v) for v in value]
        return [int(x.strip()) for x in str(value).split(",") if x.strip()]


@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()
