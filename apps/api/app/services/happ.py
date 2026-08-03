from __future__ import annotations

import base64
from datetime import datetime
from decimal import Decimal
from urllib.parse import quote

from app.config import Settings, get_settings
from app.models.entities import Subscription
from app.services.marzban import links_to_subscription_body


def build_sub_url(sub_token: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return f"{settings.subscription_base_url}/{sub_token}"


def build_happ_deep_link(sub_url: str) -> str:
    return f"happ://import/{quote(sub_url, safe='')}"


def subscription_userinfo(
    *,
    upload: int = 0,
    download: int = 0,
    total: int | None,
    expire: datetime,
) -> str:
    expire_ts = int(expire.timestamp())
    total_bytes = 0 if total is None else int(total * 1024**3)
    return f"upload={upload}; download={download}; total={total_bytes}; expire={expire_ts}"


def profile_title_header(title: str) -> str:
    encoded = base64.b64encode(title.encode("utf-8")).decode("ascii")
    return f"base64:{encoded}"


def enrich_links_for_happ(links: list[str]) -> list[str]:
    """Ensure server names keep country flags for Happ UI."""
    return links


def build_subscription_response(
    subscription: Subscription,
    links: list[str],
    settings: Settings | None = None,
) -> tuple[str, dict[str, str]]:
    settings = settings or get_settings()
    body = links_to_subscription_body(enrich_links_for_happ(links))
    used = float(subscription.traffic_used_gb or Decimal("0"))
    used_bytes = int(used * 1024**3)
    headers = {
        "profile-title": profile_title_header(settings.happ_profile_title),
        "subscription-userinfo": subscription_userinfo(
            upload=0,
            download=used_bytes,
            total=subscription.traffic_limit_gb,
            expire=subscription.ends_at,
        ),
        "profile-update-interval": "12",
        "content-disposition": f'attachment; filename="{settings.brand_name}.txt"',
    }
    if settings.happ_provider_id:
        headers["provider-id"] = settings.happ_provider_id
    return body, headers
