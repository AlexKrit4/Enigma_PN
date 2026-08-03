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
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.request(method, f"{self.base}{path}", headers=self.headers, **kwargs)
            if resp.status_code >= 400:
                detail = resp.text
                raise RuntimeError(f"API {resp.status_code}: {detail}")
            if resp.status_code == 204:
                return None
            ctype = resp.headers.get("content-type", "")
            if "application/json" in ctype:
                return resp.json()
            return resp.content

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

    async def admin_health(self) -> dict:
        return await self._request("GET", "/admin/health")

    async def admin_users(self, status: str = "active", limit: int = 20) -> dict:
        return await self._request("GET", "/admin/users", params={"status": status, "limit": limit})

    async def admin_lookup(self, q: str) -> dict:
        return await self._request("GET", "/admin/users/lookup", params={"q": q})

    async def admin_user(self, telegram_id: int) -> dict:
        return await self._request("GET", f"/admin/users/{telegram_id}")

    async def admin_extend(self, telegram_id: int, days: int) -> dict:
        return await self._request("POST", f"/admin/users/{telegram_id}/extend", json={"days": days})

    async def admin_grant(
        self,
        telegram_id: int,
        days: int,
        traffic_gb: int | None = None,
        device_limit: int | None = None,
        username: str | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"days": days}
        if traffic_gb is not None:
            payload["traffic_gb"] = traffic_gb
        if device_limit is not None:
            payload["device_limit"] = device_limit
        if username:
            payload["username"] = username
        return await self._request("POST", f"/admin/users/{telegram_id}/grant", json=payload)

    async def admin_revoke(self, telegram_id: int) -> dict:
        return await self._request("POST", f"/admin/users/{telegram_id}/revoke")

    async def admin_limits(
        self,
        telegram_id: int,
        *,
        traffic_gb: int | None = None,
        clear_traffic_limit: bool = False,
        device_limit: int | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"clear_traffic_limit": clear_traffic_limit}
        if traffic_gb is not None:
            payload["traffic_gb"] = traffic_gb
        if device_limit is not None:
            payload["device_limit"] = device_limit
        return await self._request("POST", f"/admin/users/{telegram_id}/limits", json=payload)

    async def admin_orders(self, status: str = "pending", limit: int = 20) -> dict:
        return await self._request("GET", "/admin/orders", params={"status": status, "limit": limit})

    async def admin_confirm_order(self, payment_label: str) -> dict:
        return await self._request("POST", f"/admin/orders/{payment_label}/confirm")

    async def admin_broadcast(self, text: str, audience: str = "active") -> dict:
        return await self._request("POST", "/admin/broadcast", json={"text": text, "audience": audience})

    async def admin_plans(self) -> list[dict]:
        return await self._request("GET", "/admin/plans")

    async def admin_plan_create(self, payload: dict) -> dict:
        return await self._request("POST", "/admin/plans", json=payload)

    async def admin_plan_patch(self, plan_id: str, payload: dict) -> dict:
        return await self._request("PATCH", f"/admin/plans/{plan_id}", json=payload)

    async def admin_promos(self) -> dict:
        return await self._request("GET", "/admin/promos")

    async def admin_promo_create(self, payload: dict) -> dict:
        return await self._request("POST", "/admin/promos", json=payload)

    async def admin_promo_disable(self, code: str) -> dict:
        return await self._request("POST", f"/admin/promos/{code}/disable")

    async def admin_export_csv(self) -> bytes:
        data = await self._request("GET", "/admin/export.csv")
        if isinstance(data, bytes):
            return data
        return str(data).encode("utf-8")
