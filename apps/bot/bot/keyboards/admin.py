from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats")],
            [InlineKeyboardButton(text="💚 Здоровье сервера", callback_data="adm:health")],
            [
                InlineKeyboardButton(text="👥 Активные", callback_data="adm:list:active"),
                InlineKeyboardButton(text="🆕 Недавние", callback_data="adm:list:recent"),
            ],
            [InlineKeyboardButton(text="🔎 Поиск ID/@user", callback_data="adm:search")],
            [InlineKeyboardButton(text="⏳ Ожидают оплаты", callback_data="adm:orders")],
            [
                InlineKeyboardButton(text="🎁 Выдать", callback_data="adm:grant"),
                InlineKeyboardButton(text="⏱ Продлить", callback_data="adm:extend"),
            ],
            [
                InlineKeyboardButton(text="🚫 Отключить", callback_data="adm:revoke"),
                InlineKeyboardButton(text="⚙️ Лимиты", callback_data="adm:limits"),
            ],
            [InlineKeyboardButton(text="📣 Рассылка", callback_data="adm:broadcast")],
            [
                InlineKeyboardButton(text="🏷 Тарифы", callback_data="adm:plans"),
                InlineKeyboardButton(text="🎟 Промокоды", callback_data="adm:promos"),
            ],
            [InlineKeyboardButton(text="📥 Экспорт CSV", callback_data="adm:export")],
            [InlineKeyboardButton(text="✖️ Закрыть", callback_data="adm:close")],
        ]
    )


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="adm:menu")]]
    )


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="adm:cancel")]]
    )


def days_keyboard(prefix: str) -> InlineKeyboardMarkup:
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


def traffic_keyboard(prefix: str = "grant_gb") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="∞ без лимита", callback_data=f"adm:{prefix}:0"),
                InlineKeyboardButton(text="5 GB", callback_data=f"adm:{prefix}:5"),
            ],
            [
                InlineKeyboardButton(text="50 GB", callback_data=f"adm:{prefix}:50"),
                InlineKeyboardButton(text="100 GB", callback_data=f"adm:{prefix}:100"),
                InlineKeyboardButton(text="Свой…", callback_data=f"adm:{prefix}:custom"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="adm:cancel")],
        ]
    )


def devices_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="adm:limit_dev:1"),
                InlineKeyboardButton(text="2", callback_data="adm:limit_dev:2"),
                InlineKeyboardButton(text="3", callback_data="adm:limit_dev:3"),
                InlineKeyboardButton(text="5", callback_data="adm:limit_dev:5"),
            ],
            [InlineKeyboardButton(text="Не менять устройства", callback_data="adm:limit_dev:keep")],
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


def users_list_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item in items[:20]:
        tid = item.get("telegram_id")
        if not tid:
            continue
        uname = item.get("username") or "—"
        status = item.get("status") or "?"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"@{uname} · {tid} · {status}",
                    callback_data=f"adm:open:{tid}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def user_card_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏱ Продлить", callback_data=f"adm:u_extend:{telegram_id}"),
                InlineKeyboardButton(text="🎁 Выдать", callback_data=f"adm:u_grant:{telegram_id}"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Лимиты", callback_data=f"adm:u_limits:{telegram_id}"),
                InlineKeyboardButton(text="🚫 Отключить", callback_data=f"adm:u_revoke:{telegram_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="adm:menu")],
        ]
    )


def orders_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item in items[:15]:
        label = item.get("payment_label") or ""
        amount = item.get("amount") or "?"
        uname = item.get("username") or item.get("telegram_id") or "?"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✅ {amount}₽ · @{uname} · {label[:10]}",
                    callback_data=f"adm:pay:{label}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def broadcast_audience_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Только активные", callback_data="adm:bcast_aud:active"),
                InlineKeyboardButton(text="Все пользователи", callback_data="adm:bcast_aud:all"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="adm:cancel")],
        ]
    )


def plans_admin_keyboard(plans: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for plan in plans[:20]:
        active = "✅" if plan.get("is_active") else "⏸"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{active} {plan.get('name')} — {plan.get('price_rub')}₽",
                    callback_data=f"adm:plan_toggle:{plan.get('id')}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ Новый тариф", callback_data="adm:plan_new")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def promos_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for p in items[:20]:
        active = "✅" if p.get("is_active") else "⏸"
        code = p.get("code") or ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{active} {code} · {p.get('days')}д · {p.get('used_count')}/{p.get('max_uses') or '∞'}",
                    callback_data=f"adm:promo_off:{code}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ Создать промо", callback_data="adm:promo_new")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
