from __future__ import annotations

import base64
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import quote

from app.config import Settings, get_settings
from app.models.entities import Subscription
from app.services.marzban import links_to_subscription_body


def build_sub_url(sub_token: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return f"{settings.subscription_base_url}/{sub_token}"


def build_happ_deep_link(sub_url: str) -> str:
    """Native Happ deep link — opens app and imports subscription URL."""
    return f"happ://add/{sub_url}"


def build_happ_open_url(sub_token: str, settings: Settings | None = None) -> str:
    """HTTPS page Telegram can open as a button; redirects into Happ."""
    settings = settings or get_settings()
    base = settings.subscription_base_url.rstrip("/").rsplit("/s", 1)[0]
    return f"{base}/add/{sub_token}"


def build_happ_redirect_html(sub_url: str, brand: str = "Enigma_PN") -> str:
    deep = build_happ_deep_link(sub_url)
    deep_alt = f"happ://import/{quote(sub_url, safe='')}"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Открыть в Happ — {brand}</title>
  <style>
    body {{
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      font-family: Georgia, "Times New Roman", serif;
      background: radial-gradient(1000px 520px at 15% 0%, #d9ebff, #f6f1e8 52%, #ebe2d4);
      color: #1b2433; padding: 24px;
    }}
    .card {{
      width: min(420px, 100%); background: rgba(255,255,255,.86);
      border: 1px solid rgba(27,36,51,.08); border-radius: 24px;
      padding: 28px 24px; box-shadow: 0 18px 50px rgba(27,36,51,.08);
      text-align: center;
    }}
    h1 {{ margin: 0 0 10px; font-size: 1.5rem; font-weight: 700; }}
    p {{ margin: 0 0 18px; line-height: 1.5; color: #4b5563; font-family: system-ui, sans-serif; }}
    a.btn {{
      display: inline-block; text-decoration: none; background: #1b2433; color: #fff;
      padding: 14px 18px; border-radius: 14px; font-weight: 600;
      font-family: system-ui, sans-serif;
    }}
    .muted {{ margin-top: 16px; font-size: .9rem; color: #6b7280; font-family: system-ui, sans-serif; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Открываем Happ…</h1>
    <p>Если приложение не открылось само — нажмите кнопку. Подписка добавится автоматически.</p>
    <a class="btn" id="open" href="{deep}">Открыть в Happ</a>
    <p class="muted">Нет Happ? Установите приложение и вернитесь по этой ссылке.</p>
  </div>
  <script>
    (function () {{
      var primary = {deep!r};
      var alt = {deep_alt!r};
      try {{ window.location.href = primary; }} catch (e) {{}}
      setTimeout(function () {{
        try {{ window.location.href = alt; }} catch (e) {{}}
      }}, 700);
    }})();
  </script>
</body>
</html>
"""


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


def announce_header(text: str) -> str:
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return f"base64:{encoded}"


def days_left(ends_at: datetime) -> int:
    now = datetime.now(timezone.utc)
    end = ends_at if ends_at.tzinfo else ends_at.replace(tzinfo=timezone.utc)
    delta = end - now
    seconds = int(delta.total_seconds())
    if seconds <= 0:
        return 0
    return max(1, (seconds + 86399) // 86400)


def build_sub_status_text(
    subscription: Subscription,
    *,
    devices_used: int | None = None,
) -> str:
    left = days_left(subscription.ends_at)
    if left == 0:
        days_part = "истекла"
    elif left == 1:
        days_part = "остался 1 день"
    elif left in {2, 3, 4}:
        days_part = f"осталось {left} дня"
    else:
        days_part = f"осталось {left} дней"

    used = 0 if devices_used is None else max(0, int(devices_used))
    limit = subscription.device_limit or 0
    if limit > 0:
        devices_part = f"устройств {used}/{limit}"
    else:
        devices_part = f"устройств {used}"
    return f"{days_part} · {devices_part}"


def enrich_links_for_happ(links: list[str]) -> list[str]:
    """Ensure server names keep country flags for Happ UI."""
    return links


def build_subscription_response(
    subscription: Subscription,
    links: list[str],
    settings: Settings | None = None,
    *,
    devices_used: int | None = None,
) -> tuple[str, dict[str, str]]:
    settings = settings or get_settings()
    body = links_to_subscription_body(enrich_links_for_happ(links))
    used = float(subscription.traffic_used_gb or Decimal("0"))
    used_bytes = int(used * 1024**3)
    status_text = build_sub_status_text(subscription, devices_used=devices_used)
    # Keep under Happ sub-info-text limit (200).
    info_text = status_text[:200]
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
        "announce": announce_header(status_text),
        "sub-info-text": info_text,
        "sub-info-color": "blue",
        "sub-expire": "1",
        "subscription-always-hwid-enable": "1",
    }
    if settings.happ_provider_id:
        headers["provider-id"] = settings.happ_provider_id
    return body, headers
