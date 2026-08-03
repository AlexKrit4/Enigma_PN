from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats")],
            [InlineKeyboardButton(text="👤 Найти пользователя", callback_data="adm:user")],
            [InlineKeyboardButton(text="🎁 Выдать подписку", callback_data="adm:grant")],
            [InlineKeyboardButton(text="⏱ Продлить", callback_data="adm:extend")],
            [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data="adm:confirm")],
            [InlineKeyboardButton(text="✖️ Закрыть", callback_data="adm:close")],
        ]
    )


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="adm:menu")]]
    )


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="adm:cancel")],
        ]
    )


def days_keyboard(prefix: str) -> InlineKeyboardMarkup:
    """prefix: grant_days | extend_days"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 дн", callback_data=f"adm:{prefix}:1"),
                InlineKeyboardButton(text="7 дн", callback_data=f"adm:{prefix}:7"),
                InlineKeyboardButton(text="30 дн", callback_data=f"adm:{prefix}:30"),
            ],
            [
                InlineKeyboardButton(text="90 дн", callback_data=f"adm:{prefix}:90"),
                InlineKeyboardButton(text="365 дн", callback_data=f"adm:{prefix}:365"),
                InlineKeyboardButton(text="Свой…", callback_data=f"adm:{prefix}:custom"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="adm:cancel")],
        ]
    )


def traffic_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="∞ без лимита", callback_data="adm:grant_gb:0"),
                InlineKeyboardButton(text="5 GB", callback_data="adm:grant_gb:5"),
            ],
            [
                InlineKeyboardButton(text="50 GB", callback_data="adm:grant_gb:50"),
                InlineKeyboardButton(text="100 GB", callback_data="adm:grant_gb:100"),
                InlineKeyboardButton(text="Свой…", callback_data="adm:grant_gb:custom"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="adm:cancel")],
        ]
    )


def confirm_action_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm:do:{action}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="adm:cancel"),
            ]
        ]
    )
