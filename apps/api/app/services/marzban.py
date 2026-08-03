from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from app.config import Settings, get_settings

log = structlog.get_logger(__name__)


@dataclass
class ProvisionedClient:
    username: str
    uuid: uuid.UUID
    node_id: str
    links: list[str]
    raw: dict[str, Any]


class MarzbanClient:
    """Client for Marzban REST API with mock mode for local development."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._token: str | None = None
        self._mock_store: dict[str, dict[str, Any]] = {}

    async def _login(self) -> str:
        if self._token:
            return self._token
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.settings.marzban_url.rstrip('/')}/api/admin/token",
                data={
                    "username": self.settings.marzban_username,
                    "password": self.settings.marzban_password,
                },
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
            return self._token

    async def create_user(
        self,
        *,
        username: str,
        expire_ts: int,
        data_limit_bytes: int | None,
        note: str = "",
    ) -> ProvisionedClient:
        if self.settings.marzban_mock:
            return self._mock_create(username=username, expire_ts=expire_ts, data_limit_bytes=data_limit_bytes)

        token = await self._login()
        payload: dict[str, Any] = {
            "username": username,
            "proxies": {"vless": {"flow": "xtls-rprx-vision"}},
            "inbounds": {"vless": ["VLESS TCP REALITY"]},
            "expire": expire_ts,
            "data_limit": data_limit_bytes or 0,
            "data_limit_reset_strategy": "no_reset",
            "status": "active",
            "note": note,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.settings.marzban_url.rstrip('/')}/api/user",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            if resp.status_code >= 400:
                log.error("marzban_create_failed", status=resp.status_code, body=resp.text)
                resp.raise_for_status()
            data = resp.json()

        links = data.get("links") or []
        user_uuid = uuid.UUID(data.get("proxies", {}).get("vless", {}).get("id") or str(uuid.uuid4()))
        node_id = self.settings.vpn_nodes[0]["id"] if self.settings.vpn_nodes else "nl-1"
        return ProvisionedClient(username=username, uuid=user_uuid, node_id=node_id, links=links, raw=data)

    async def modify_user(
        self,
        username: str,
        *,
        expire_ts: int | None = None,
        status: str | None = None,
        data_limit_bytes: int | None = None,
    ) -> None:
        if self.settings.marzban_mock:
            entry = self._mock_store.get(username)
            if not entry:
                return
            if expire_ts is not None:
                entry["expire"] = expire_ts
            if status is not None:
                entry["status"] = status
            if data_limit_bytes is not None:
                entry["data_limit"] = data_limit_bytes
            return

        token = await self._login()
        payload: dict[str, Any] = {}
        if expire_ts is not None:
            payload["expire"] = expire_ts
        if status is not None:
            payload["status"] = status
        if data_limit_bytes is not None:
            payload["data_limit"] = data_limit_bytes
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"{self.settings.marzban_url.rstrip('/')}/api/user/{username}",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            resp.raise_for_status()

    async def get_subscription_links(self, username: str) -> list[str]:
        if self.settings.marzban_mock:
            entry = self._mock_store.get(username)
            return list(entry.get("links", [])) if entry else []

        token = await self._login()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.settings.marzban_url.rstrip('/')}/api/user/{username}",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return list(resp.json().get("links") or [])

    async def health(self) -> bool:
        if self.settings.marzban_mock:
            return True
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.settings.marzban_url.rstrip('/')}/api/system")
                return resp.status_code < 500
        except Exception:
            return False

    def _mock_create(
        self,
        *,
        username: str,
        expire_ts: int,
        data_limit_bytes: int | None,
    ) -> ProvisionedClient:
        user_uuid = uuid.uuid4()
        node = self.settings.vpn_nodes[0] if self.settings.vpn_nodes else {"id": "nl-1", "name": "🇳🇱 Netherlands"}
        # Mock VLESS link — works for Happ import format testing only
        link = (
            f"vless://{user_uuid}@127.0.0.1:443"
            f"?encryption=none&flow=xtls-rprx-vision&security=reality"
            f"&sni=www.cloudflare.com&fp=chrome&pbk=MOCK_PUBLIC_KEY"
            f"&sid=0123456789abcdef&type=tcp#{node['name']}"
        )
        raw = {
            "username": username,
            "status": "active",
            "expire": expire_ts,
            "data_limit": data_limit_bytes or 0,
            "links": [link],
            "used_traffic": 0,
        }
        self._mock_store[username] = raw
        log.info("marzban_mock_create", username=username, expire=expire_ts)
        return ProvisionedClient(
            username=username,
            uuid=user_uuid,
            node_id=str(node["id"]),
            links=[link],
            raw=raw,
        )


def links_to_subscription_body(links: list[str]) -> str:
    payload = "\n".join(links)
    return base64.b64encode(payload.encode("utf-8")).decode("ascii")


def to_unix(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())
