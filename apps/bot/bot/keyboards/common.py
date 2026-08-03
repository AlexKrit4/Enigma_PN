from __future__ import annotations

from datetime import datetime
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Тарифы"), KeyboardButton(text="📱 Моя подписка")],
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="💬 Поддержка")],
        ],
        resize_keyboard=True,
    )


def plans_keyboard(plans: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    current_group = None
    for plan in plans:
        group = plan.get("group_name") or ""
        if group != current_group:
            current_group = group
            rows.append([InlineKeyboardButton(text=f"— {group.upper()} —", callback_data="noop")])
        label = f"{plan['name']} — {plan['price_rub']} ₽"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"buy:{plan['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscription_keyboard(sub_url: str, happ_open_url: str = "") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    # HTTPS open URL redirects into Happ — Telegram allows only http(s) buttons.
    open_url = happ_open_url if happ_open_url.startswith("http") else sub_url
    if open_url.startswith("http"):
        rows.append([InlineKeyboardButton(text="🚀 Открыть в Happ", url=open_url)])
    if sub_url.startswith("http"):
        rows.append([InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="show_sub_url")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pay_keyboard(payment_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💳 Оплатить через ЮMoney", url=payment_url)]]
    )


_MONTHS_RU = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def format_ru_date(value: str | datetime | None) -> str:
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return escape(value)
    return f"{value.day} {_MONTHS_RU[value.month]} {value.year}"


def format_status(status: str | None) -> str:
    mapping = {
        "active": "Активна",
        "trial": "Пробный период",
        "expired": "Истекла",
        "disabled": "Отключена",
    }
    return mapping.get((status or "").lower(), status or "—")


def format_subscription_card(sub: dict | None, *, brand: str = "Enigma_PN") -> str:
    if not sub:
        return (
            f"📱 <b>Подписка {escape(brand)}</b>\n\n"
            "Пока нет активной подписки.\n"
            "Выберите тариф в меню «🛒 Тарифы» — и всё заработает."
        )

    plan = sub.get("plan") or {}
    plan_name = plan.get("name")
    if not plan_name:
        plan_name = "Пробный период" if (sub.get("status") or "").lower() == "trial" else "VPN-доступ"

    limit = sub.get("traffic_limit_gb")
    used_raw = sub.get("traffic_used_gb")
    try:
        used = float(used_raw or 0)
        used_label = f"{used:.1f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        used_label = str(used_raw or "0")
    traffic = f"{used_label} / {'∞' if limit is None else limit} ГБ"
    devices = sub.get("device_limit") or "—"

    return (
        f"📱 <b>Ваша подписка</b>\n\n"
        f"Тариф: <b>{escape(str(plan_name))}</b>\n"
        f"Статус: <b>{escape(format_status(sub.get('status')))}</b>\n"
        f"Действует до: <b>{format_ru_date(sub.get('ends_at'))}</b>\n"
        f"Трафик: <b>{escape(traffic)}</b>\n"
        f"Устройств: <b>{escape(str(devices))}</b>\n\n"
        "Нажмите «Открыть в Happ» — приложение само добавит подписку.\n"
        "Если Happ ещё нет: установите его, затем вернитесь и нажмите кнопку снова."
    )
