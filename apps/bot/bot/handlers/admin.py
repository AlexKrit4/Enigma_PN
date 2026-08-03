from __future__ import annotations

import html
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.api_client import ApiClient
from bot.config import get_settings
from bot.keyboards.admin import (
    admin_back_keyboard,
    admin_cancel_keyboard,
    admin_menu_keyboard,
    confirm_action_keyboard,
    days_keyboard,
    traffic_keyboard,
)

router = Router(name="admin")
api = ApiClient()


class AdminFSM(StatesGroup):
    wait_user_id = State()
    wait_extend_id = State()
    wait_extend_days_custom = State()
    wait_grant_id = State()
    wait_grant_days_custom = State()
    wait_grant_gb_custom = State()
    wait_confirm_label = State()


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in get_settings().admin_telegram_ids


def _admin_denied(user) -> str | None:
    if not user or not _is_admin(user.id):
        return "Нет доступа"
    return None


def _who(user) -> str:
    uname = f"@{user.username}" if user and user.username else "без username"
    return f"{uname} · ID <code>{user.id}</code>"


def _menu_text(user) -> str:
    return (
        "🔐 <b>Админ-панель Enigma_PN</b>\n\n"
        f"Доступ подтверждён: {_who(user)}\n"
        "Действия ниже выполняются от вашего имени."
    )


def _fmt_user_payload(payload: dict) -> str:
    user = payload.get("user") or {}
    sub = user.get("subscription")
    lines = [
        "👤 <b>Пользователь</b>",
        f"Telegram ID: <code>{user.get('telegram_id')}</code>",
        f"Username: @{html.escape(user.get('username') or '—')}",
        f"Admin: {'да' if user.get('is_admin') else 'нет'}",
        f"Создан: {user.get('created_at')}",
    ]
    if not sub:
        lines.append("\nПодписка: нет")
        return "\n".join(lines)
    limit = sub.get("traffic_limit_gb")
    used = sub.get("traffic_used_gb")
    lines.extend(
        [
            "",
            "📱 <b>Подписка</b>",
            f"Статус: <b>{html.escape(str(sub.get('status')))}</b>",
            f"До: <b>{html.escape(str(sub.get('ends_at')))}</b>",
            f"Трафик: {used} / {limit if limit is not None else '∞'} GB",
            f"Устройств: {sub.get('device_limit')}",
            f"URL:\n<code>{html.escape(str(sub.get('sub_url') or ''))}</code>",
        ]
    )
    return "\n".join(lines)


async def _show_menu(message: Message, user, edit: bool = False) -> None:
    text = _menu_text(user)
    kb = admin_menu_keyboard()
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


async def _run_text_command(message: Message, args: list[str]) -> bool:
    """Keep legacy slash commands. Returns True if handled."""
    if not args:
        return False
    cmd = args[0]
    try:
        if cmd == "stats":
            stats = await api.admin_stats()
            await message.answer(
                "📊 <b>Статистика</b>\n"
                f"Пользователи: {stats['users_total']}\n"
                f"Активные: {stats['subscriptions_active']}\n"
                f"Триал: {stats['subscriptions_trial']}\n"
                f"Оплаченных заказов: {stats['orders_paid']}\n"
                f"MRR ≈ {stats['mrr_rub']} ₽"
            )
            return True
        if cmd == "user" and len(args) >= 2:
            info = await api.admin_user(int(args[1]))
            await message.answer(_fmt_user_payload(info), reply_markup=admin_back_keyboard())
            return True
        if cmd == "extend" and len(args) >= 3:
            result = await api.admin_extend(int(args[1]), int(args[2]))
            await message.answer(f"✅ Продлено до {result['ends_at']}")
            return True
        if cmd == "grant" and len(args) >= 3:
            tg_id = int(args[1])
            days = int(args[2])
            traffic_gb = int(args[3]) if len(args) >= 4 else None
            result = await api.admin_grant(tg_id, days, traffic_gb=traffic_gb)
            sub = result.get("subscription") or {}
            await message.answer(
                f"✅ Выдано на {days} дн.\n"
                f"До: {result.get('ends_at')}\n"
                f"URL: <code>{html.escape(str(sub.get('sub_url') or ''))}</code>"
            )
            return True
        if cmd == "confirm" and len(args) >= 2:
            result = await api.admin_confirm_order(args[1])
            await message.answer(f"✅ Заказ подтверждён: {html.escape(str(result))}")
            return True
    except Exception as exc:
        await message.answer(f"Ошибка: {html.escape(str(exc))}")
        return True
    return False


@router.message(Command("admin"))
async def cmd_admin(message: Message, command: CommandObject, state: FSMContext) -> None:
    user = message.from_user
    assert user
    denied = _admin_denied(user)
    if denied:
        if get_settings().admin_telegram_ids:
            await message.answer(denied)
            return
        await message.answer(
            "ADMIN_TELEGRAM_IDS не задан.\n"
            f"Ваш numeric ID: <code>{user.id}</code>\n"
            "Добавьте его в .env как ADMIN_TELEGRAM_IDS и перезапустите бота."
        )
        return

    args = (command.args or "").split()
    if args:
        handled = await _run_text_command(message, args)
        if handled:
            return
        await message.answer(
            "Неизвестная команда. Откройте меню /admin или:\n"
            "/admin stats\n"
            "/admin user ID\n"
            "/admin extend ID DAYS\n"
            "/admin grant ID DAYS [GB]\n"
            "/admin confirm LABEL"
        )
        return

    await state.clear()
    await _show_menu(message, user)


@router.callback_query(F.data == "adm:menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    assert callback.message
    await _show_menu(callback.message, callback.from_user, edit=True)
    await callback.answer()


@router.callback_query(F.data == "adm:close")
async def cb_close(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    assert callback.message
    await callback.message.edit_text("Админ-панель закрыта.")
    await callback.answer()


@router.callback_query(F.data == "adm:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    assert callback.message
    await _show_menu(callback.message, callback.from_user, edit=True)
    await callback.answer("Отменено")


@router.callback_query(F.data == "adm:stats")
async def cb_stats(callback: CallbackQuery) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.message
    try:
        stats = await api.admin_stats()
        text = (
            "📊 <b>Статистика</b>\n\n"
            f"Пользователи: <b>{stats['users_total']}</b>\n"
            f"Активные: <b>{stats['subscriptions_active']}</b>\n"
            f"Триал: <b>{stats['subscriptions_trial']}</b>\n"
            f"Оплаченных заказов: <b>{stats['orders_paid']}</b>\n"
            f"MRR ≈ <b>{stats['mrr_rub']}</b> ₽\n\n"
            f"Запросил: {_who(callback.from_user)}"
        )
        await callback.message.edit_text(text, reply_markup=admin_back_keyboard())
    except Exception as exc:
        await callback.message.edit_text(
            f"Ошибка статистики: {html.escape(str(exc))}",
            reply_markup=admin_back_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "adm:user")
async def cb_user_start(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_user_id)
    assert callback.message
    await callback.message.edit_text(
        "👤 Введите Telegram ID пользователя:",
        reply_markup=admin_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminFSM.wait_user_id)
async def fsm_user_id(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Нужен числовой Telegram ID. Попробуйте ещё раз:", reply_markup=admin_cancel_keyboard())
        return
    try:
        info = await api.admin_user(int(raw))
        await state.clear()
        await message.answer(_fmt_user_payload(info), reply_markup=admin_back_keyboard())
    except Exception as exc:
        await message.answer(f"Ошибка: {html.escape(str(exc))}", reply_markup=admin_cancel_keyboard())


@router.callback_query(F.data == "adm:extend")
async def cb_extend_start(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_extend_id)
    await state.update_data(action="extend")
    assert callback.message
    await callback.message.edit_text(
        "⏱ Введите Telegram ID для продления:",
        reply_markup=admin_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminFSM.wait_extend_id)
async def fsm_extend_id(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Нужен числовой Telegram ID:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(tg_id=int(raw))
    await state.set_state(None)
    await message.answer(
        f"На сколько дней продлить <code>{raw}</code>?",
        reply_markup=days_keyboard("extend_days"),
    )


@router.callback_query(F.data.startswith("adm:extend_days:"))
async def cb_extend_days(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    value = callback.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    tg_id = data.get("tg_id")
    if not tg_id:
        await callback.answer("Сначала укажите ID", show_alert=True)
        await _show_menu(callback.message, callback.from_user, edit=True)
        return
    if value == "custom":
        await state.set_state(AdminFSM.wait_extend_days_custom)
        await callback.message.edit_text(
            "Введите число дней:",
            reply_markup=admin_cancel_keyboard(),
        )
        await callback.answer()
        return
    days = int(value)
    await state.update_data(days=days)
    await callback.message.edit_text(
        f"Продлить <code>{tg_id}</code> на <b>{days}</b> дн.?\n"
        f"Инициатор: {_who(callback.from_user)}",
        reply_markup=confirm_action_keyboard("extend"),
    )
    await callback.answer()


@router.message(AdminFSM.wait_extend_days_custom)
async def fsm_extend_days_custom(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        await message.answer("Введите целое число дней ≥ 1:", reply_markup=admin_cancel_keyboard())
        return
    days = int(raw)
    data = await state.get_data()
    await state.update_data(days=days)
    await state.set_state(None)
    await message.answer(
        f"Продлить <code>{data.get('tg_id')}</code> на <b>{days}</b> дн.?\n"
        f"Инициатор: {_who(message.from_user)}",
        reply_markup=confirm_action_keyboard("extend"),
    )


@router.callback_query(F.data == "adm:grant")
async def cb_grant_start(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_grant_id)
    await state.update_data(action="grant")
    assert callback.message
    await callback.message.edit_text(
        "🎁 Введите Telegram ID — кому выдать подписку:",
        reply_markup=admin_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminFSM.wait_grant_id)
async def fsm_grant_id(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Нужен числовой Telegram ID:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(tg_id=int(raw))
    await state.set_state(None)
    await message.answer(
        f"На сколько дней выдать подписку <code>{raw}</code>?",
        reply_markup=days_keyboard("grant_days"),
    )


@router.callback_query(F.data.startswith("adm:grant_days:"))
async def cb_grant_days(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    value = callback.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    if not data.get("tg_id"):
        await callback.answer("Сначала укажите ID", show_alert=True)
        return
    if value == "custom":
        await state.set_state(AdminFSM.wait_grant_days_custom)
        await callback.message.edit_text("Введите число дней:", reply_markup=admin_cancel_keyboard())
        await callback.answer()
        return
    await state.update_data(days=int(value))
    await callback.message.edit_text(
        "Лимит трафика:",
        reply_markup=traffic_keyboard(),
    )
    await callback.answer()


@router.message(AdminFSM.wait_grant_days_custom)
async def fsm_grant_days_custom(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        await message.answer("Введите целое число дней ≥ 1:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(days=int(raw))
    await state.set_state(None)
    await message.answer("Лимит трафика:", reply_markup=traffic_keyboard())


@router.callback_query(F.data.startswith("adm:grant_gb:"))
async def cb_grant_gb(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    value = callback.data.rsplit(":", 1)[-1]
    if value == "custom":
        await state.set_state(AdminFSM.wait_grant_gb_custom)
        await callback.message.edit_text(
            "Введите лимит GB (число). 0 = без лимита:",
            reply_markup=admin_cancel_keyboard(),
        )
        await callback.answer()
        return
    gb = int(value)
    await state.update_data(traffic_gb=None if gb == 0 else gb)
    data = await state.get_data()
    await _ask_grant_confirm(callback.message, callback.from_user, data, edit=True)
    await callback.answer()


@router.message(AdminFSM.wait_grant_gb_custom)
async def fsm_grant_gb_custom(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Введите число GB (0 = без лимита):", reply_markup=admin_cancel_keyboard())
        return
    gb = int(raw)
    await state.update_data(traffic_gb=None if gb == 0 else gb)
    await state.set_state(None)
    data = await state.get_data()
    await _ask_grant_confirm(message, message.from_user, data, edit=False)


async def _ask_grant_confirm(message: Message, user, data: dict[str, Any], *, edit: bool) -> None:
    tg_id = data.get("tg_id")
    days = data.get("days")
    traffic_gb = data.get("traffic_gb")
    traffic_label = "∞" if traffic_gb is None else f"{traffic_gb} GB"
    text = (
        "🎁 Подтвердите выдачу:\n"
        f"Кому: <code>{tg_id}</code>\n"
        f"Срок: <b>{days}</b> дн.\n"
        f"Трафик: <b>{traffic_label}</b>\n"
        f"Инициатор: {_who(user)}"
    )
    kb = confirm_action_keyboard("grant")
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "adm:confirm")
async def cb_confirm_start(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_confirm_label)
    assert callback.message
    await callback.message.edit_text(
        "✅ Введите метку платежа (payment label), например <code>rRyaDukZ94TXeaDI</code>:",
        reply_markup=admin_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminFSM.wait_confirm_label)
async def fsm_confirm_label(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    label = (message.text or "").strip()
    if not label or " " in label:
        await message.answer("Введите метку одной строкой без пробелов:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(payment_label=label)
    await state.set_state(None)
    await message.answer(
        f"Подтвердить оплату <code>{html.escape(label)}</code>?\n"
        f"Инициатор: {_who(message.from_user)}",
        reply_markup=confirm_action_keyboard("confirm"),
    )


@router.callback_query(F.data.startswith("adm:do:"))
async def cb_do_action(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    action = callback.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    try:
        if action == "extend":
            tg_id = int(data["tg_id"])
            days = int(data["days"])
            result = await api.admin_extend(tg_id, days)
            text = (
                f"✅ Продлено.\n"
                f"ID: <code>{tg_id}</code>\n"
                f"До: <b>{result['ends_at']}</b>\n"
                f"Кто: {_who(callback.from_user)}"
            )
        elif action == "grant":
            tg_id = int(data["tg_id"])
            days = int(data["days"])
            traffic_gb = data.get("traffic_gb")
            result = await api.admin_grant(tg_id, days, traffic_gb=traffic_gb)
            sub = result.get("subscription") or {}
            text = (
                f"✅ Подписка выдана.\n"
                f"ID: <code>{tg_id}</code>\n"
                f"До: <b>{result.get('ends_at')}</b>\n"
                f"URL:\n<code>{html.escape(str(sub.get('sub_url') or ''))}</code>\n"
                f"Кто: {_who(callback.from_user)}"
            )
        elif action == "confirm":
            label = str(data["payment_label"])
            result = await api.admin_confirm_order(label)
            text = (
                f"✅ Оплата подтверждена.\n"
                f"Label: <code>{html.escape(label)}</code>\n"
                f"Статус: {html.escape(str(result.get('order_status')))}\n"
                f"Кто: {_who(callback.from_user)}"
            )
        else:
            text = "Неизвестное действие"
        await state.clear()
        await callback.message.edit_text(text, reply_markup=admin_back_keyboard())
        await callback.answer("Готово")
    except Exception as exc:
        await callback.message.edit_text(
            f"Ошибка: {html.escape(str(exc))}",
            reply_markup=admin_back_keyboard(),
        )
        await callback.answer("Ошибка", show_alert=True)


@router.message(StateFilter(AdminFSM), F.text)
async def fsm_fallback(message: Message) -> None:
    """Catch stray text while in admin FSM if no specific handler matched."""
    if _admin_denied(message.from_user):
        return
    await message.answer(
        "Сейчас ждём данные для админ-действия. Нажмите «Отмена» или /admin.",
        reply_markup=admin_cancel_keyboard(),
    )
