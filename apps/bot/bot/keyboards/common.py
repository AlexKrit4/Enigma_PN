from __future__ import annotations

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


def subscription_keyboard(sub_url: str, happ_link: str) -> InlineKeyboardMarkup:
    # Telegram URL buttons allow only http/https — happ:// goes in message text.
    rows: list[list[InlineKeyboardButton]] = []
    if sub_url.startswith("http"):
        rows.append([InlineKeyboardButton(text="🔗 Открыть subscription URL", url=sub_url)])
    rows.append([InlineKeyboardButton(text="📋 Показать ссылку", callback_data="show_sub_url")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pay_keyboard(payment_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💳 Оплатить через ЮMoney", url=payment_url)]]
    )
