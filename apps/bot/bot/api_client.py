from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from bot.config import get_settings


class ApiClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base = self.settings.api_internal_url.rstrip("/")
        self.headers = {"X-Bot-Token": self.settings.bot_api_token}

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, f"{self.base}{path}", headers=self.headers, **kwargs)
            if resp.status_code >= 400:
                detail = resp.text
                raise RuntimeError(f"API {resp.status_code}: {detail}")
            if resp.status_code == 204:
                return None
            return resp.json()

    async def auth(self, telegram_id: int, username: str | None) -> dict:
        return await self._request(
            "POST",
            "/api/v1/auth/telegram",
            json={"telegram_id": telegram_id, "username": username},
        )

    async def plans(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self.base}/api/v1/plans")
            resp.raise_for_status()
            return resp.json()

    async def trial(self, telegram_id: int, username: str | None) -> dict:
        return await self._request(
            "POST",
            "/api/v1/trial",
            json={"telegram_id": telegram_id, "username": username},
        )

    async def create_order(self, telegram_id: int, plan_id: str | UUID) -> dict:
        return await self._request(
            "POST",
            "/api/v1/orders",
            json={"telegram_id": telegram_id, "plan_id": str(plan_id)},
        )

    async def me(self, access_token: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base}/api/v1/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def admin_stats(self) -> dict:
        return await self._request("GET", "/admin/stats")

    async def admin_user(self, telegram_id: int) -> dict:
        return await self._request("GET", f"/admin/users/{telegram_id}")

    async def admin_extend(self, telegram_id: int, days: int) -> dict:
        return await self._request("POST", f"/admin/users/{telegram_id}/extend", json={"days": days})
