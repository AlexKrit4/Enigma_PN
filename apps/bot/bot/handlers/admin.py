from __future__ import annotations

import html
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.api_client import ApiClient
from bot.config import get_settings
from bot.keyboards.admin import (
    admin_back_keyboard,
    admin_cancel_keyboard,
    admin_menu_keyboard,
    broadcast_audience_keyboard,
    confirm_action_keyboard,
    days_keyboard,
    devices_keyboard,
    orders_keyboard,
    plans_admin_keyboard,
    promos_keyboard,
    traffic_keyboard,
    user_card_keyboard,
    users_list_keyboard,
)

router = Router(name="admin")
api = ApiClient()


class AdminFSM(StatesGroup):
    wait_search = State()
    wait_extend_id = State()
    wait_extend_days_custom = State()
    wait_grant_id = State()
    wait_grant_days_custom = State()
    wait_grant_gb_custom = State()
    wait_revoke_id = State()
    wait_limits_id = State()
    wait_limits_gb_custom = State()
    wait_broadcast_text = State()
    wait_confirm_label = State()
    wait_promo_code = State()
    wait_promo_days = State()
    wait_plan_slug = State()
    wait_plan_name = State()
    wait_plan_price = State()
    wait_plan_days = State()


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
        "Все действия <b>без уведомлений</b> пользователям.\n"
        "Рассылка — только если нажмёте её сами."
    )


def _fmt_user_payload(payload: dict) -> str:
    user = (payload.get("user") or payload) if isinstance(payload, dict) else {}
    if "user" in payload:
        user = payload["user"]
    sub = user.get("subscription")
    vpn = user.get("vpn")
    lines = [
        "👤 <b>Пользователь</b>",
        f"Telegram ID: <code>{user.get('telegram_id')}</code>",
        f"Username: @{html.escape(str(user.get('username') or '—'))}",
        f"Admin: {'да' if user.get('is_admin') else 'нет'}",
        f"Создан: {user.get('created_at')}",
    ]
    if sub:
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
    else:
        lines.append("\nПодписка: нет")

    if vpn:
        lines.extend(
            [
                "",
                "🛰 <b>VPN (Marzban)</b>",
                f"User: <code>{html.escape(str(vpn.get('username') or ''))}</code>",
                f"Status: <b>{html.escape(str(vpn.get('status') or vpn.get('found')))}</b>",
                f"Online/last: <b>{html.escape(str(vpn.get('online_at') or 'н/д'))}</b>",
                f"Traffic: {vpn.get('used_traffic_gb')} GB",
            ]
        )
        if vpn.get("error"):
            lines.append(f"Ошибка: {html.escape(str(vpn['error']))}")
    return "\n".join(lines)


async def _show_menu(message: Message, user, edit: bool = False) -> None:
    text = _menu_text(user)
    kb = admin_menu_keyboard()
    if edit:
        try:
            await message.edit_text(text, reply_markup=kb)
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=kb)


async def _open_user(message: Message, telegram_id: int, *, edit: bool = False) -> None:
    info = await api.admin_user(telegram_id)
    text = _fmt_user_payload(info)
    kb = user_card_keyboard(telegram_id)
    if edit:
        try:
            await message.edit_text(text, reply_markup=kb)
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=kb)


async def _run_text_command(message: Message, args: list[str]) -> bool:
    if not args:
        return False
    cmd = args[0]
    try:
        if cmd == "stats":
            stats = await api.admin_stats()
            await message.answer(_fmt_stats(stats), reply_markup=admin_back_keyboard())
            return True
        if cmd in {"user", "find"} and len(args) >= 2:
            info = await api.admin_lookup(args[1])
            tid = info.get("user", {}).get("telegram_id")
            await message.answer(_fmt_user_payload(info), reply_markup=user_card_keyboard(int(tid)) if tid else admin_back_keyboard())
            return True
        if cmd == "extend" and len(args) >= 3:
            result = await api.admin_extend(int(args[1]), int(args[2]))
            await message.answer(f"✅ Продлено до {result['ends_at']} (без уведа юзеру)")
            return True
        if cmd == "grant" and len(args) >= 3:
            traffic_gb = int(args[3]) if len(args) >= 4 else None
            result = await api.admin_grant(int(args[1]), int(args[2]), traffic_gb=traffic_gb)
            sub = result.get("subscription") or {}
            await message.answer(
                f"✅ Выдано (без уведа).\nДо: {result.get('ends_at')}\n"
                f"URL: <code>{html.escape(str(sub.get('sub_url') or ''))}</code>"
            )
            return True
        if cmd == "revoke" and len(args) >= 2:
            result = await api.admin_revoke(int(args[1]))
            await message.answer(f"🚫 Отключено: {result}")
            return True
        if cmd == "confirm" and len(args) >= 2:
            result = await api.admin_confirm_order(args[1])
            await message.answer(f"✅ Заказ подтверждён (без уведа): {html.escape(str(result))}")
            return True
    except Exception as exc:
        await message.answer(f"Ошибка: {html.escape(str(exc))}")
        return True
    return False


def _fmt_stats(stats: dict) -> str:
    return (
        "📊 <b>Статистика</b>\n\n"
        f"Пользователи: <b>{stats.get('users_total')}</b>\n"
        f"Активные: <b>{stats.get('subscriptions_active')}</b>\n"
        f"Триал: <b>{stats.get('subscriptions_trial')}</b>\n"
        f"Оплаченных заказов: <b>{stats.get('orders_paid')}</b>\n"
        f"Ожидают оплаты: <b>{stats.get('pending_orders')}</b>\n"
        f"Выручка сегодня: <b>{stats.get('revenue_today_rub')}</b> ₽\n"
        f"Выручка 7 дней: <b>{stats.get('revenue_7d_rub')}</b> ₽\n"
        f"MRR ≈ <b>{stats.get('mrr_rub')}</b> ₽"
    )


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
            f"Ваш numeric ID: <code>{user.id}</code>"
        )
        return

    args = (command.args or "").split()
    if args:
        handled = await _run_text_command(message, args)
        if handled:
            return
        await message.answer("Неизвестная команда. Откройте /admin")
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
        text = _fmt_stats(stats) + f"\n\nЗапросил: {_who(callback.from_user)}"
        await callback.message.edit_text(text, reply_markup=admin_back_keyboard())
    except Exception as exc:
        await callback.message.edit_text(f"Ошибка: {html.escape(str(exc))}", reply_markup=admin_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:health")
async def cb_health(callback: CallbackQuery) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.message
    try:
        h = await api.admin_health()
        mem = h.get("memory") or {}
        disk = h.get("disk") or {}
        reality = h.get("reality") or {}
        text = (
            "💚 <b>Здоровье сервера</b>\n\n"
            f"DB: {'✅' if h.get('db') else '❌'}\n"
            f"Marzban: {'✅' if h.get('marzban') else '❌'}\n"
            f"Reality {reality.get('host')}:{reality.get('port')}: "
            f"{'✅ open' if reality.get('open') else '❌ closed'}\n"
            f"RAM avail: {mem.get('available_mb')} / {mem.get('total_mb')} MB\n"
            f"Disk free: {disk.get('free_gb')} / {disk.get('total_gb')} GB\n"
            f"Loadavg: {h.get('loadavg')}"
        )
        await callback.message.edit_text(text, reply_markup=admin_back_keyboard())
    except Exception as exc:
        await callback.message.edit_text(f"Ошибка: {html.escape(str(exc))}", reply_markup=admin_back_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:list:"))
async def cb_list(callback: CallbackQuery) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    status = callback.data.rsplit(":", 1)[-1]
    try:
        data = await api.admin_users(status=status, limit=20)
        items = data.get("items") or []
        if not items:
            await callback.message.edit_text("Список пуст.", reply_markup=admin_back_keyboard())
        else:
            await callback.message.edit_text(
                f"👥 Список (<code>{html.escape(status)}</code>), нажмите чтобы открыть:",
                reply_markup=users_list_keyboard(items),
            )
    except Exception as exc:
        await callback.message.edit_text(f"Ошибка: {html.escape(str(exc))}", reply_markup=admin_back_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:open:"))
async def cb_open_user(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    tid = int(callback.data.rsplit(":", 1)[-1])
    await state.clear()
    try:
        await _open_user(callback.message, tid, edit=True)
    except Exception as exc:
        await callback.message.edit_text(f"Ошибка: {html.escape(str(exc))}", reply_markup=admin_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:search")
async def cb_search(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_search)
    assert callback.message
    await callback.message.edit_text(
        "🔎 Введите Telegram ID или @username:",
        reply_markup=admin_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminFSM.wait_search)
async def fsm_search(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    q = (message.text or "").strip()
    try:
        info = await api.admin_lookup(q)
        tid = info.get("user", {}).get("telegram_id")
        await state.clear()
        if tid:
            await message.answer(_fmt_user_payload(info), reply_markup=user_card_keyboard(int(tid)))
        else:
            await message.answer(_fmt_user_payload(info), reply_markup=admin_back_keyboard())
    except Exception as exc:
        await message.answer(f"Не найден: {html.escape(str(exc))}", reply_markup=admin_cancel_keyboard())


@router.callback_query(F.data == "adm:orders")
async def cb_orders(callback: CallbackQuery) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.message
    try:
        data = await api.admin_orders("pending", 20)
        items = data.get("items") or []
        if not items:
            await callback.message.edit_text("Нет ожидающих оплат.", reply_markup=admin_back_keyboard())
        else:
            await callback.message.edit_text(
                "⏳ Ожидают оплаты — нажмите чтобы подтвердить (без уведа юзеру):",
                reply_markup=orders_keyboard(items),
            )
    except Exception as exc:
        await callback.message.edit_text(f"Ошибка: {html.escape(str(exc))}", reply_markup=admin_back_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:pay:"))
async def cb_pay_confirm(callback: CallbackQuery) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    label = callback.data.split(":", 2)[-1]
    try:
        result = await api.admin_confirm_order(label)
        await callback.message.edit_text(
            f"✅ Оплата <code>{html.escape(label)}</code> подтверждена.\n"
            f"Статус: {html.escape(str(result.get('order_status')))}\n"
            f"Увед юзеру: нет\nКто: {_who(callback.from_user)}",
            reply_markup=admin_back_keyboard(),
        )
        await callback.answer("Готово")
    except Exception as exc:
        await callback.answer(str(exc)[:180], show_alert=True)


# ---- grant / extend / revoke / limits ----

@router.callback_query(F.data == "adm:grant")
async def cb_grant_start(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_grant_id)
    assert callback.message
    await callback.message.edit_text("🎁 Telegram ID или @username:", reply_markup=admin_cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:u_grant:"))
async def cb_u_grant(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    tid = int(callback.data.rsplit(":", 1)[-1])
    await state.update_data(tg_id=tid, action="grant")
    await state.set_state(None)
    await callback.message.edit_text(
        f"На сколько дней выдать <code>{tid}</code>?",
        reply_markup=days_keyboard("grant_days"),
    )
    await callback.answer()


@router.message(AdminFSM.wait_grant_id)
async def fsm_grant_id(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    tid = await _resolve_to_tid(message.text or "")
    if not tid:
        await message.answer("Не понял ID/@username. Ещё раз:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(tg_id=tid)
    await state.set_state(None)
    await message.answer(f"На сколько дней выдать <code>{tid}</code>?", reply_markup=days_keyboard("grant_days"))


@router.callback_query(F.data.startswith("adm:grant_days:"))
async def cb_grant_days(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    value = callback.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    if not data.get("tg_id"):
        await callback.answer("Сначала укажите пользователя", show_alert=True)
        return
    if value == "custom":
        await state.set_state(AdminFSM.wait_grant_days_custom)
        await callback.message.edit_text("Введите число дней:", reply_markup=admin_cancel_keyboard())
        await callback.answer()
        return
    await state.update_data(days=int(value))
    await callback.message.edit_text("Лимит трафика:", reply_markup=traffic_keyboard("grant_gb"))
    await callback.answer()


@router.message(AdminFSM.wait_grant_days_custom)
async def fsm_grant_days_custom(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        await message.answer("Число дней ≥ 1:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(days=int(raw))
    await state.set_state(None)
    await message.answer("Лимит трафика:", reply_markup=traffic_keyboard("grant_gb"))


@router.callback_query(F.data.startswith("adm:grant_gb:"))
async def cb_grant_gb(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    value = callback.data.rsplit(":", 1)[-1]
    if value == "custom":
        await state.set_state(AdminFSM.wait_grant_gb_custom)
        await callback.message.edit_text("GB (0 = ∞):", reply_markup=admin_cancel_keyboard())
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
        await message.answer("Число GB:", reply_markup=admin_cancel_keyboard())
        return
    gb = int(raw)
    await state.update_data(traffic_gb=None if gb == 0 else gb)
    await state.set_state(None)
    data = await state.get_data()
    await _ask_grant_confirm(message, message.from_user, data, edit=False)


async def _ask_grant_confirm(message: Message, user, data: dict[str, Any], *, edit: bool) -> None:
    traffic_label = "∞" if data.get("traffic_gb") is None else f"{data.get('traffic_gb')} GB"
    text = (
        "🎁 Подтвердите выдачу (без уведа юзеру):\n"
        f"Кому: <code>{data.get('tg_id')}</code>\n"
        f"Срок: <b>{data.get('days')}</b> дн.\n"
        f"Трафик: <b>{traffic_label}</b>\n"
        f"Инициатор: {_who(user)}"
    )
    kb = confirm_action_keyboard("grant")
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "adm:extend")
async def cb_extend_start(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_extend_id)
    assert callback.message
    await callback.message.edit_text("⏱ Telegram ID или @username:", reply_markup=admin_cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:u_extend:"))
async def cb_u_extend(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    tid = int(callback.data.rsplit(":", 1)[-1])
    await state.update_data(tg_id=tid, action="extend")
    await callback.message.edit_text(
        f"На сколько дней продлить <code>{tid}</code>?",
        reply_markup=days_keyboard("extend_days"),
    )
    await callback.answer()


@router.message(AdminFSM.wait_extend_id)
async def fsm_extend_id(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    tid = await _resolve_to_tid(message.text or "")
    if not tid:
        await message.answer("Не понял ID/@username:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(tg_id=tid)
    await state.set_state(None)
    await message.answer(f"На сколько дней продлить <code>{tid}</code>?", reply_markup=days_keyboard("extend_days"))


@router.callback_query(F.data.startswith("adm:extend_days:"))
async def cb_extend_days(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    value = callback.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    if not data.get("tg_id"):
        await callback.answer("Нет ID", show_alert=True)
        return
    if value == "custom":
        await state.set_state(AdminFSM.wait_extend_days_custom)
        await callback.message.edit_text("Число дней:", reply_markup=admin_cancel_keyboard())
        await callback.answer()
        return
    days = int(value)
    await state.update_data(days=days)
    await callback.message.edit_text(
        f"Продлить <code>{data['tg_id']}</code> на <b>{days}</b> дн.?\nБез уведа юзеру.\nИнициатор: {_who(callback.from_user)}",
        reply_markup=confirm_action_keyboard("extend"),
    )
    await callback.answer()


@router.message(AdminFSM.wait_extend_days_custom)
async def fsm_extend_days_custom(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        await message.answer("Число дней ≥ 1:", reply_markup=admin_cancel_keyboard())
        return
    days = int(raw)
    data = await state.get_data()
    await state.update_data(days=days)
    await state.set_state(None)
    await message.answer(
        f"Продлить <code>{data.get('tg_id')}</code> на <b>{days}</b> дн.?\nБез уведа юзеру.\nИнициатор: {_who(message.from_user)}",
        reply_markup=confirm_action_keyboard("extend"),
    )


@router.callback_query(F.data == "adm:revoke")
async def cb_revoke_start(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_revoke_id)
    assert callback.message
    await callback.message.edit_text("🚫 Кого отключить? ID или @username:", reply_markup=admin_cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:u_revoke:"))
async def cb_u_revoke(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    tid = int(callback.data.rsplit(":", 1)[-1])
    await state.update_data(tg_id=tid)
    await callback.message.edit_text(
        f"Отключить VPN у <code>{tid}</code>?\nMarzban cut-off, без уведа.\nИнициатор: {_who(callback.from_user)}",
        reply_markup=confirm_action_keyboard("revoke"),
    )
    await callback.answer()


@router.message(AdminFSM.wait_revoke_id)
async def fsm_revoke_id(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    tid = await _resolve_to_tid(message.text or "")
    if not tid:
        await message.answer("Не понял ID/@username:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(tg_id=tid)
    await state.set_state(None)
    await message.answer(
        f"Отключить VPN у <code>{tid}</code>?\nБез уведа.\nИнициатор: {_who(message.from_user)}",
        reply_markup=confirm_action_keyboard("revoke"),
    )


@router.callback_query(F.data == "adm:limits")
async def cb_limits_start(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_limits_id)
    assert callback.message
    await callback.message.edit_text("⚙️ Кому лимиты? ID или @username:", reply_markup=admin_cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:u_limits:"))
async def cb_u_limits(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    tid = int(callback.data.rsplit(":", 1)[-1])
    await state.update_data(tg_id=tid, action="limits")
    await callback.message.edit_text(
        f"Трафик для <code>{tid}</code>:",
        reply_markup=traffic_keyboard("limit_gb"),
    )
    await callback.answer()


@router.message(AdminFSM.wait_limits_id)
async def fsm_limits_id(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    tid = await _resolve_to_tid(message.text or "")
    if not tid:
        await message.answer("Не понял ID/@username:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(tg_id=tid)
    await state.set_state(None)
    await message.answer(f"Трафик для <code>{tid}</code>:", reply_markup=traffic_keyboard("limit_gb"))


@router.callback_query(F.data.startswith("adm:limit_gb:"))
async def cb_limit_gb(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    value = callback.data.rsplit(":", 1)[-1]
    if value == "custom":
        await state.set_state(AdminFSM.wait_limits_gb_custom)
        await callback.message.edit_text("GB (0 = ∞):", reply_markup=admin_cancel_keyboard())
        await callback.answer()
        return
    gb = int(value)
    await state.update_data(traffic_gb=None if gb == 0 else gb, clear_traffic_limit=(gb == 0))
    await callback.message.edit_text("Лимит устройств:", reply_markup=devices_keyboard())
    await callback.answer()


@router.message(AdminFSM.wait_limits_gb_custom)
async def fsm_limits_gb_custom(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Число GB:", reply_markup=admin_cancel_keyboard())
        return
    gb = int(raw)
    await state.update_data(traffic_gb=None if gb == 0 else gb, clear_traffic_limit=(gb == 0))
    await state.set_state(None)
    await message.answer("Лимит устройств:", reply_markup=devices_keyboard())


@router.callback_query(F.data.startswith("adm:limit_dev:"))
async def cb_limit_dev(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    value = callback.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    device_limit = None if value == "keep" else int(value)
    await state.update_data(device_limit=device_limit)
    traffic_label = "∞" if data.get("clear_traffic_limit") or data.get("traffic_gb") is None else f"{data.get('traffic_gb')} GB"
    await callback.message.edit_text(
        "⚙️ Подтвердите лимиты (без уведа):\n"
        f"ID: <code>{data.get('tg_id')}</code>\n"
        f"Трафик: <b>{traffic_label}</b>\n"
        f"Устройства: <b>{device_limit if device_limit is not None else 'без изменений'}</b>\n"
        f"Инициатор: {_who(callback.from_user)}",
        reply_markup=confirm_action_keyboard("limits"),
    )
    await callback.answer()


# ---- broadcast ----

@router.callback_query(F.data == "adm:broadcast")
async def cb_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_broadcast_text)
    assert callback.message
    await callback.message.edit_text(
        "📣 Введите текст рассылки.\nЭто единственное действие, которое пишет пользователям.",
        reply_markup=admin_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminFSM.wait_broadcast_text)
async def fsm_broadcast_text(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Слишком короткий текст:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(broadcast_text=text)
    await state.set_state(None)
    await message.answer("Кому отправить?", reply_markup=broadcast_audience_keyboard())


@router.callback_query(F.data.startswith("adm:bcast_aud:"))
async def cb_bcast_aud(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    audience = callback.data.rsplit(":", 1)[-1]
    await state.update_data(audience=audience)
    data = await state.get_data()
    preview = html.escape(str(data.get("broadcast_text") or "")[:500])
    await callback.message.edit_text(
        f"Отправить рассылку ({audience})?\n\n<pre>{preview}</pre>\n\nИнициатор: {_who(callback.from_user)}",
        reply_markup=confirm_action_keyboard("broadcast"),
    )
    await callback.answer()


# ---- plans / promos / export ----

@router.callback_query(F.data == "adm:plans")
async def cb_plans(callback: CallbackQuery) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.message
    try:
        plans = await api.admin_plans()
        await callback.message.edit_text(
            "🏷 Тарифы — нажмите чтобы вкл/выкл:",
            reply_markup=plans_admin_keyboard(plans),
        )
    except Exception as exc:
        await callback.message.edit_text(f"Ошибка: {html.escape(str(exc))}", reply_markup=admin_back_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:plan_toggle:"))
async def cb_plan_toggle(callback: CallbackQuery) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    plan_id = callback.data.split(":", 2)[-1]
    try:
        plans = await api.admin_plans()
        plan = next((p for p in plans if str(p.get("id")) == plan_id), None)
        if not plan:
            await callback.answer("Не найден", show_alert=True)
            return
        new_active = not bool(plan.get("is_active"))
        await api.admin_plan_patch(plan_id, {"is_active": new_active})
        plans = await api.admin_plans()
        await callback.message.edit_text(
            "🏷 Тарифы — нажмите чтобы вкл/выкл:",
            reply_markup=plans_admin_keyboard(plans),
        )
        await callback.answer("Обновлено")
    except Exception as exc:
        await callback.answer(str(exc)[:180], show_alert=True)


@router.callback_query(F.data == "adm:plan_new")
async def cb_plan_new(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_plan_slug)
    assert callback.message
    await callback.message.edit_text("Slug тарифа (латиница, например month1):", reply_markup=admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminFSM.wait_plan_slug)
async def fsm_plan_slug(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    slug = (message.text or "").strip().lower()
    if not slug.isalnum():
        await message.answer("Только латиница/цифры:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(plan_slug=slug)
    await state.set_state(AdminFSM.wait_plan_name)
    await message.answer("Название тарифа:", reply_markup=admin_cancel_keyboard())


@router.message(AdminFSM.wait_plan_name)
async def fsm_plan_name(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Слишком коротко:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(plan_name=name)
    await state.set_state(AdminFSM.wait_plan_days)
    await message.answer("Длительность в днях:", reply_markup=admin_cancel_keyboard())


@router.message(AdminFSM.wait_plan_days)
async def fsm_plan_days(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        await message.answer("Число дней:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(plan_days=int(raw))
    await state.set_state(AdminFSM.wait_plan_price)
    await message.answer("Цена в ₽:", reply_markup=admin_cancel_keyboard())


@router.message(AdminFSM.wait_plan_price)
async def fsm_plan_price(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip().replace(",", ".")
    try:
        price = float(raw)
    except ValueError:
        await message.answer("Число, например 299:", reply_markup=admin_cancel_keyboard())
        return
    data = await state.get_data()
    try:
        plan = await api.admin_plan_create(
            {
                "slug": data["plan_slug"],
                "name": data["plan_name"],
                "duration_days": data["plan_days"],
                "price_rub": price,
                "is_active": True,
            }
        )
        await state.clear()
        await message.answer(
            f"✅ Тариф создан: <b>{html.escape(plan.get('name', ''))}</b> — {plan.get('price_rub')} ₽",
            reply_markup=admin_back_keyboard(),
        )
    except Exception as exc:
        await message.answer(f"Ошибка: {html.escape(str(exc))}", reply_markup=admin_cancel_keyboard())


@router.callback_query(F.data == "adm:promos")
async def cb_promos(callback: CallbackQuery) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.message
    try:
        data = await api.admin_promos()
        items = data.get("items") or []
        text = "🎟 Промокоды — нажмите чтобы отключить:" if items else "Промокодов пока нет."
        await callback.message.edit_text(text, reply_markup=promos_keyboard(items))
    except Exception as exc:
        await callback.message.edit_text(f"Ошибка: {html.escape(str(exc))}", reply_markup=admin_back_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:promo_off:"))
async def cb_promo_off(callback: CallbackQuery) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.data and callback.message
    code = callback.data.split(":", 2)[-1]
    try:
        await api.admin_promo_disable(code)
        data = await api.admin_promos()
        await callback.message.edit_text(
            "🎟 Промокоды:",
            reply_markup=promos_keyboard(data.get("items") or []),
        )
        await callback.answer("Отключён")
    except Exception as exc:
        await callback.answer(str(exc)[:180], show_alert=True)


@router.callback_query(F.data == "adm:promo_new")
async def cb_promo_new(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_promo_code)
    assert callback.message
    await callback.message.edit_text("Код промо (например WIN30):", reply_markup=admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminFSM.wait_promo_code)
async def fsm_promo_code(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    code = (message.text or "").strip().upper()
    if len(code) < 2:
        await message.answer("Слишком короткий код:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(promo_code=code)
    await state.set_state(AdminFSM.wait_promo_days)
    await message.answer("На сколько дней даёт промо?", reply_markup=admin_cancel_keyboard())


@router.message(AdminFSM.wait_promo_days)
async def fsm_promo_days(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        await message.answer("Число дней:", reply_markup=admin_cancel_keyboard())
        return
    data = await state.get_data()
    try:
        result = await api.admin_promo_create({"code": data["promo_code"], "days": int(raw)})
        await state.clear()
        await message.answer(
            f"✅ Промо <code>{html.escape(result.get('code', ''))}</code> создан.",
            reply_markup=admin_back_keyboard(),
        )
    except Exception as exc:
        await message.answer(f"Ошибка: {html.escape(str(exc))}", reply_markup=admin_cancel_keyboard())


@router.callback_query(F.data == "adm:export")
async def cb_export(callback: CallbackQuery) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert callback.message
    await callback.answer("Готовлю CSV…")
    try:
        raw = await api.admin_export_csv()
        doc = BufferedInputFile(raw, filename="enigma_users.csv")
        await callback.message.answer_document(doc, caption="📥 Экспорт пользователей")
        await callback.message.answer("Готово.", reply_markup=admin_back_keyboard())
    except Exception as exc:
        await callback.message.answer(f"Ошибка: {html.escape(str(exc))}", reply_markup=admin_back_keyboard())


@router.callback_query(F.data == "adm:confirm")
async def cb_confirm_start(callback: CallbackQuery, state: FSMContext) -> None:
    if _admin_denied(callback.from_user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.wait_confirm_label)
    assert callback.message
    await callback.message.edit_text("Метка платежа:", reply_markup=admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminFSM.wait_confirm_label)
async def fsm_confirm_label(message: Message, state: FSMContext) -> None:
    if _admin_denied(message.from_user):
        return
    label = (message.text or "").strip()
    if not label:
        await message.answer("Введите метку:", reply_markup=admin_cancel_keyboard())
        return
    await state.update_data(payment_label=label)
    await state.set_state(None)
    await message.answer(
        f"Подтвердить оплату <code>{html.escape(label)}</code> без уведа юзеру?\nИнициатор: {_who(message.from_user)}",
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
            result = await api.admin_extend(int(data["tg_id"]), int(data["days"]))
            text = f"✅ Продлено до <b>{result['ends_at']}</b>\nУвед юзеру: нет\nКто: {_who(callback.from_user)}"
        elif action == "grant":
            result = await api.admin_grant(
                int(data["tg_id"]),
                int(data["days"]),
                traffic_gb=data.get("traffic_gb"),
            )
            sub = result.get("subscription") or {}
            text = (
                f"✅ Выдано до <b>{result.get('ends_at')}</b>\n"
                f"URL:\n<code>{html.escape(str(sub.get('sub_url') or ''))}</code>\n"
                f"Увед юзеру: нет\nКто: {_who(callback.from_user)}"
            )
        elif action == "revoke":
            result = await api.admin_revoke(int(data["tg_id"]))
            text = f"🚫 Отключено ({html.escape(str(result.get('status')))})\nУвед юзеру: нет\nКто: {_who(callback.from_user)}"
        elif action == "limits":
            result = await api.admin_limits(
                int(data["tg_id"]),
                traffic_gb=data.get("traffic_gb"),
                clear_traffic_limit=bool(data.get("clear_traffic_limit")),
                device_limit=data.get("device_limit"),
            )
            text = f"⚙️ Лимиты обновлены.\nУвед юзеру: нет\nКто: {_who(callback.from_user)}\n{html.escape(str(result.get('subscription')))}"
        elif action == "confirm":
            result = await api.admin_confirm_order(str(data["payment_label"]))
            text = (
                f"✅ Оплата подтверждена.\n"
                f"Статус: {html.escape(str(result.get('order_status')))}\n"
                f"Увед юзеру: нет\nКто: {_who(callback.from_user)}"
            )
        elif action == "broadcast":
            result = await api.admin_broadcast(
                str(data.get("broadcast_text") or ""),
                audience=str(data.get("audience") or "active"),
            )
            text = (
                f"📣 Рассылка отправлена.\n"
                f"Аудитория: {html.escape(str(result.get('audience')))}\n"
                f"Целей: {result.get('targets')} · отправлено: {result.get('sent')} · ошибок: {result.get('failed')}\n"
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


async def _resolve_to_tid(raw: str) -> int | None:
    raw = raw.strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    try:
        info = await api.admin_lookup(raw)
        tid = info.get("user", {}).get("telegram_id")
        return int(tid) if tid else None
    except Exception:
        return None


@router.message(StateFilter(AdminFSM), F.text)
async def fsm_fallback(message: Message) -> None:
    if _admin_denied(message.from_user):
        return
    await message.answer(
        "Жду данные для админ-действия. Отмена или /admin.",
        reply_markup=admin_cancel_keyboard(),
    )
