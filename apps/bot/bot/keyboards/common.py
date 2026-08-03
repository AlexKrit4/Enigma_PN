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


def tariff_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Ограниченный", callback_data="tarif:limited")],
            [InlineKeyboardButton(text="♾️ Вечный", callback_data="tarif:eternal")],
            [InlineKeyboardButton(text="🛠 Свой тариф", callback_data="tarif:custom")],
        ]
    )


def plans_keyboard(plans: list[dict], *, back: bool = True) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for plan in plans:
        traffic = plan.get("traffic_gb")
        traffic_label = "∞ ГБ" if traffic is None else f"{traffic} ГБ"
        label = f"{plan['name']} — {plan['price_rub']} ₽"
        # Prefer short labels for limited/eternal shop buttons.
        if plan.get("group_name") == "ограниченный":
            label = f"{traffic_label} — {plan['price_rub']} ₽"
        elif plan.get("group_name") == "вечный":
            days = int(plan.get("duration_days") or 0)
            if days >= 30 and days % 30 == 0:
                months = days // 30
                period = f"{months} мес." if months != 1 else "1 месяц"
            else:
                period = f"{days} дн."
            label = f"{period} — {plan['price_rub']} ₽"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"buy:{plan['id']}")])
    if back:
        rows.append([InlineKeyboardButton(text="« Назад", callback_data="tarif:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def custom_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="tarif:home")]]
    )


def custom_gb_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 ГБ", callback_data="custom:gb:10"),
                InlineKeyboardButton(text="30 ГБ", callback_data="custom:gb:30"),
                InlineKeyboardButton(text="50 ГБ", callback_data="custom:gb:50"),
            ],
            [
                InlineKeyboardButton(text="100 ГБ", callback_data="custom:gb:100"),
                InlineKeyboardButton(text="250 ГБ", callback_data="custom:gb:250"),
            ],
            [InlineKeyboardButton(text="Другое число…", callback_data="custom:gb:ask")],
            [InlineKeyboardButton(text="« Назад", callback_data="tarif:home")],
        ]
    )


def custom_days_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="7 дн.", callback_data="custom:days:7"),
                InlineKeyboardButton(text="14 дн.", callback_data="custom:days:14"),
                InlineKeyboardButton(text="30 дн.", callback_data="custom:days:30"),
            ],
            [
                InlineKeyboardButton(text="90 дн.", callback_data="custom:days:90"),
                InlineKeyboardButton(text="180 дн.", callback_data="custom:days:180"),
            ],
            [InlineKeyboardButton(text="Другое число…", callback_data="custom:days:ask")],
            [InlineKeyboardButton(text="« Назад", callback_data="tarif:custom")],
        ]
    )


def custom_devices_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="custom:dev:1"),
                InlineKeyboardButton(text="2", callback_data="custom:dev:2"),
                InlineKeyboardButton(text="3", callback_data="custom:dev:3"),
            ],
            [
                InlineKeyboardButton(text="4", callback_data="custom:dev:4"),
                InlineKeyboardButton(text="5", callback_data="custom:dev:5"),
            ],
            [InlineKeyboardButton(text="Другое число…", callback_data="custom:dev:ask")],
            [InlineKeyboardButton(text="« Назад", callback_data="tarif:custom")],
        ]
    )


def custom_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", callback_data="custom:pay")],
            [InlineKeyboardButton(text="« Назад", callback_data="tarif:custom")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tarif:home")],
        ]
    )


def subscription_keyboard(
    sub_url: str,
    happ_open_url: str = "",
    *,
    show_devices: bool = True,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    # HTTPS open URL redirects into Happ — Telegram allows only http(s) buttons.
    open_url = happ_open_url if happ_open_url.startswith("http") else sub_url
    if open_url.startswith("http"):
        rows.append([InlineKeyboardButton(text="🚀 Открыть в Happ", url=open_url)])
    if show_devices and sub_url:
        rows.append([InlineKeyboardButton(text="📱 Устройства", callback_data="devices:list")])
    if sub_url.startswith("http"):
        rows.append([InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="show_sub_url")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def devices_keyboard(devices: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for device in devices:
        label = str(device.get("label") or "устройство")[:40]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"⏏ {label}",
                    callback_data=f"devices:kick:{device['id']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="« Назад к подписке", callback_data="devices:back")])
    if not devices:
        rows = [[InlineKeyboardButton(text="« Назад к подписке", callback_data="devices:back")]]
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


def format_subscription_card(
    sub: dict | None,
    *,
    brand: str = "Enigma_PN",
) -> str:
    if not sub:
        return (
            f"📱 <b>Подписка {escape(brand)}</b>\n\n"
            "Пока нет активной подписки.\n"
            "Выберите тариф в меню «🛒 Тарифы» — и всё заработает."
        )

    plan = sub.get("plan") or {}
    plan_name = sub.get("title") or plan.get("name")
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
    device_limit = sub.get("device_limit")
    devices_used = sub.get("devices_used")
    if devices_used is None:
        devices_label = str(device_limit or "—")
    elif device_limit:
        devices_label = f"{devices_used} / {device_limit}"
    else:
        devices_label = str(devices_used)

    days_left = sub.get("days_left")
    days_line = ""
    if days_left is not None:
        days_line = f"Осталось дней: <b>{escape(str(days_left))}</b>\n"
    else:
        ends = sub.get("ends_at")
        if ends:
            try:
                end_dt = datetime.fromisoformat(str(ends).replace("Z", "+00:00"))
                from datetime import timezone

                now = datetime.now(timezone.utc)
                secs = int((end_dt - now).total_seconds())
                left = 0 if secs <= 0 else max(1, (secs + 86399) // 86400)
                days_line = f"Осталось дней: <b>{left}</b>\n"
            except ValueError:
                pass

    return (
        f"📱 <b>Ваша подписка</b>\n\n"
        f"Тариф: <b>{escape(str(plan_name))}</b>\n"
        f"Статус: <b>{escape(format_status(sub.get('status')))}</b>\n"
        f"Действует до: <b>{format_ru_date(sub.get('ends_at'))}</b>\n"
        f"{days_line}"
        f"Трафик: <b>{escape(traffic)}</b>\n"
        f"Устройств: <b>{escape(devices_label)}</b>\n\n"
        "Нажмите «Открыть в Happ» — приложение само добавит подписку.\n"
        "Лишние устройства можно отключить кнопкой «Устройства»."
    )
