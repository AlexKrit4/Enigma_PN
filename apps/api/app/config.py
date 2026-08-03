from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    brand_name: str = "Enigma_PN"
    support_telegram: str = "@alexkr1t"

    telegram_bot_token: str = ""
    telegram_bot_username: str = "enigmapnbot"
    admin_telegram_ids: list[int] = Field(default_factory=list)

    domain: str = "bigwinzone.ru"
    sub_domain: str = "sub.bigwinzone.ru"
    api_domain: str = "api.bigwinzone.ru"
    web_domain: str = "bigwinzone.ru"

    database_url: str = "postgresql+asyncpg://enigma:enigma@postgres:5432/enigma_pn"
    redis_url: str = "redis://redis:6379/0"

    secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080
    bot_api_token: str = "dev-bot-api-token"

    # Web admin panel (bigwinzone.ru:1110)
    admin_web_username: str = ""
    admin_web_password: str = ""
    admin_web_jwt_expire_minutes: int = 720

    marzban_url: str = "https://panel.bigwinzone.ru"
    marzban_username: str = "admin"
    marzban_password: str = ""
    marzban_subscription_prefix: str = "https://sub.bigwinzone.ru/s"
    marzban_mock: bool = True

    vpn_nodes: list[dict[str, Any]] = Field(
        default_factory=lambda: [{"id": "nl-1", "name": "🇳🇱 Netherlands", "weight": 100}]
    )

    yoomoney_wallet: str = ""
    yoomoney_notification_secret: str = ""

    trial_enabled: bool = True
    trial_duration_days: int = 1
    trial_traffic_gb: int = 5
    trial_device_limit: int = 1
    default_device_limit: int = 2

    happ_provider_id: str = ""
    happ_profile_title: str = "Enigma_PN"

    # SOCKS5 Telegram proxy — per-account username/password in ProxyAccess
    socks5_enabled: bool = False
    socks5_host: str = "bigwinzone.ru"
    socks5_port: int = 40080
    socks5_passwd_path: str = "/opt/socks5/passwd"
    socks5_container: str = "socks5"

    # Legacy MTProto env names (ignored for delivery; kept so old .env does not crash)
    mtproto_enabled: bool = False
    mtproto_host: str = "bigwinzone.ru"
    mtproto_port: int = 443
    mtproto_secret: str = ""

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: Any) -> list[int]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [int(v) for v in value]
        return [int(x.strip()) for x in str(value).split(",") if x.strip()]

    @field_validator("vpn_nodes", mode="before")
    @classmethod
    def parse_vpn_nodes(cls, value: Any) -> list[dict[str, Any]]:
        if value is None or value == "":
            return [{"id": "nl-1", "name": "🇳🇱 Netherlands", "weight": 100}]
        if isinstance(value, list):
            return value
        return json.loads(str(value))

    @property
    def subscription_base_url(self) -> str:
        return self.marzban_subscription_prefix.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
