from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.api_client import ApiClient
from bot.config import get_settings
from bot.keyboards.common import (
    custom_cancel_keyboard,
    custom_confirm_keyboard,
    custom_days_keyboard,
    custom_devices_keyboard,
    custom_gb_keyboard,
    devices_keyboard,
    format_subscription_card,
    main_menu,
    pay_keyboard,
    plans_keyboard,
    subscription_keyboard,
    tariff_type_keyboard,
)

router = Router()
api = ApiClient()


class BuyFSM(StatesGroup):
    wait_custom_gb = State()
    wait_custom_days = State()
    wait_custom_devices = State()


def _sub_keyboard(sub: dict | None):
    if not sub:
        return None
    return subscription_keyboard(sub.get("sub_url") or "", sub.get("happ_open_url") or "")


def _devices_text(payload: dict) -> str:
    used = payload.get("devices_used") or 0
    limit = payload.get("device_limit") or "—"
    devices = payload.get("devices") or []
    lines = [
        "📱 <b>Устройства подписки</b>",
        "",
        f"Занято: <b>{used}</b> / <b>{limit}</b>",
        "",
    ]
    if not devices:
        lines.append("Пока нет активных устройств.\nОткройте подписку в Happ — устройство появится здесь.")
    else:
        lines.append("Нажмите устройство, чтобы отключить его и освободить слот:")
        for idx, device in enumerate(devices, start=1):
            label = device.get("label") or "устройство"
            last = device.get("last_seen_at") or ""
            lines.append(f"{idx}. {label}")
            if last:
                lines.append(f"   последний раз: <code>{last}</code>")
    return "\n".join(lines)


def _tariff_home_text() -> str:
    return (
        "🛒 <b>Какой трафик желаете приобрести?</b>\n\n"
        "<b>Ограниченный</b> — пакет ГБ на месяц, 3 устройства. "
        "Отключается, когда кончится трафик или срок.\n\n"
        "<b>Вечный</b> — без лимита трафика, только срок. 3 устройства.\n\n"
        "<b>Свой тариф</b> — сами выбираете ГБ, дни и устройства.\n"
        "Цена: 2 ₽/ГБ + 1 ₽/день + 25 ₽/устройство.\n"
        "Вечный трафик в своём тарифе недоступен."
    )


def _format_custom_quote(q: dict) -> str:
    return (
        "🛠 <b>Свой тариф — проверка</b>\n\n"
        f"Трафик: <b>{q['traffic_gb']} ГБ</b> × 2 ₽ = <b>{q['gb_cost']} ₽</b>\n"
        f"Срок: <b>{q['days']} дн.</b> × 1 ₽ = <b>{q['days_cost']} ₽</b>\n"
        f"Устройства: <b>{q['device_limit']}</b> × 25 ₽ = <b>{q['devices_cost']} ₽</b>\n\n"
        f"Итого: <b>{q['total']} ₽</b>\n\n"
        "После оплаты сформируется ваша ссылка подписки."
    )


async def _plans_by_group(group: str) -> list[dict]:
    plans = await api.plans()
    return [p for p in plans if (p.get("group_name") or "").lower() == group]


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    settings = get_settings()
    user = message.from_user
    assert user
    data = await api.auth(user.id, user.username)
    sub = data.get("user", {}).get("subscription")
    intro = (
        f"Привет! Это <b>{settings.brand_name}</b> — VPN для Happ.\n\n"
        f"Сайт: https://{settings.domain}\n"
        f"Поддержка: {settings.support_telegram}\n"
    )
    trial_note = ""
    if not sub:
        try:
            trial = await api.trial(user.id, user.username)
            sub = trial.get("subscription")
            trial_note = "🎁 Выдан пробный день — попробуйте прямо сейчас.\n\n"
        except Exception:
            trial_note = "Пробный период уже использован или недоступен.\n\n"

    text = intro + "\n" + trial_note + format_subscription_card(sub, brand=settings.brand_name)
    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")
    if sub and (sub.get("happ_open_url") or sub.get("sub_url")):
        await message.answer(
            "Готово к подключению:",
            reply_markup=_sub_keyboard(sub),
            parse_mode="HTML",
        )


@router.message(Command("plans"))
@router.message(F.text == "🛒 Тарифы")
async def cmd_plans(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(_tariff_home_text(), reply_markup=tariff_type_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "tarif:home")
async def cb_tarif_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    assert callback.message
    await callback.message.edit_text(_tariff_home_text(), reply_markup=tariff_type_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "tarif:limited")
async def cb_tarif_limited(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    assert callback.message
    plans = await _plans_by_group("ограниченный")
    text = (
        "📦 <b>Ограниченный трафик</b>\n\n"
        "Все пакеты на <b>1 месяц</b>, <b>3 устройства</b>.\n"
        "Подписка отключается, когда закончится трафик или истечёт срок."
    )
    await callback.message.edit_text(text, reply_markup=plans_keyboard(plans), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "tarif:eternal")
async def cb_tarif_eternal(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    assert callback.message
    plans = await _plans_by_group("вечный")
    text = (
        "♾️ <b>Вечный трафик</b>\n\n"
        "Без лимита гигабайт. Подписка действует, пока не истечёт срок.\n"
        "Устройств: <b>3</b>."
    )
    await callback.message.edit_text(text, reply_markup=plans_keyboard(plans), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "tarif:custom")
async def cb_tarif_custom(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    assert callback.message
    await state.set_state(None)
    text = (
        "🛠 <b>Свой тариф</b>\n\n"
        "Соберите подписку сами.\n"
        "• 1 ГБ = 2 ₽\n"
        "• 1 день = 1 ₽\n"
        "• 1 устройство = 25 ₽\n\n"
        "Вечный трафик здесь купить нельзя — укажите нужный объём ГБ.\n\n"
        "Сколько ГБ нужно?"
    )
    await callback.message.edit_text(text, reply_markup=custom_gb_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("custom:gb:"))
async def cb_custom_gb(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.data and callback.message
    value = callback.data.rsplit(":", 1)[-1]
    if value == "ask":
        await state.set_state(BuyFSM.wait_custom_gb)
        await callback.message.edit_text(
            "Введите число ГБ (от 1). Вечный трафик недоступен:",
            reply_markup=custom_cancel_keyboard(),
        )
        await callback.answer()
        return
    await state.update_data(traffic_gb=int(value))
    await state.set_state(None)
    await callback.message.edit_text(
        f"Выбрано: <b>{value} ГБ</b>\n\nНа сколько дней нужна подписка?",
        reply_markup=custom_days_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BuyFSM.wait_custom_gb)
async def fsm_custom_gb(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        await message.answer("Введите целое число ГБ ≥ 1:", reply_markup=custom_cancel_keyboard())
        return
    await state.update_data(traffic_gb=int(raw))
    await state.set_state(None)
    await message.answer(
        f"Выбрано: <b>{int(raw)} ГБ</b>\n\nНа сколько дней нужна подписка?",
        reply_markup=custom_days_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("custom:days:"))
async def cb_custom_days(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.data and callback.message
    value = callback.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    if not data.get("traffic_gb"):
        await callback.answer("Сначала выберите ГБ", show_alert=True)
        return
    if value == "ask":
        await state.set_state(BuyFSM.wait_custom_days)
        await callback.message.edit_text(
            "Введите число дней (от 1):",
            reply_markup=custom_cancel_keyboard(),
        )
        await callback.answer()
        return
    await state.update_data(days=int(value))
    await state.set_state(None)
    await callback.message.edit_text(
        f"ГБ: <b>{data['traffic_gb']}</b>\nСрок: <b>{value} дн.</b>\n\nСколько устройств?",
        reply_markup=custom_devices_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BuyFSM.wait_custom_days)
async def fsm_custom_days(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        await message.answer("Введите целое число дней ≥ 1:", reply_markup=custom_cancel_keyboard())
        return
    data = await state.get_data()
    await state.update_data(days=int(raw))
    await state.set_state(None)
    await message.answer(
        f"ГБ: <b>{data.get('traffic_gb')}</b>\nСрок: <b>{int(raw)} дн.</b>\n\nСколько устройств?",
        reply_markup=custom_devices_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("custom:dev:"))
async def cb_custom_dev(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.data and callback.message and callback.from_user
    value = callback.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    if not data.get("traffic_gb") or not data.get("days"):
        await callback.answer("Сначала выберите ГБ и срок", show_alert=True)
        return
    if value == "ask":
        await state.set_state(BuyFSM.wait_custom_devices)
        await callback.message.edit_text(
            "Введите число устройств (1–20):",
            reply_markup=custom_cancel_keyboard(),
        )
        await callback.answer()
        return
    await state.update_data(device_limit=int(value))
    await state.set_state(None)
    try:
        quote = await api.quote_custom_order(
            traffic_gb=int(data["traffic_gb"]),
            days=int(data["days"]),
            device_limit=int(value),
        )
    except Exception as exc:
        await callback.answer(f"Ошибка: {exc}", show_alert=True)
        return
    await callback.message.edit_text(
        _format_custom_quote(quote),
        reply_markup=custom_confirm_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BuyFSM.wait_custom_devices)
async def fsm_custom_devices(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= 20):
        await message.answer("Введите число устройств от 1 до 20:", reply_markup=custom_cancel_keyboard())
        return
    data = await state.get_data()
    await state.update_data(device_limit=int(raw))
    await state.set_state(None)
    try:
        quote = await api.quote_custom_order(
            traffic_gb=int(data["traffic_gb"]),
            days=int(data["days"]),
            device_limit=int(raw),
        )
    except Exception as exc:
        await message.answer(f"Ошибка расчёта: {escape(str(exc))}")
        return
    await message.answer(
        _format_custom_quote(quote),
        reply_markup=custom_confirm_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "custom:pay")
async def cb_custom_pay(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user and callback.message
    data = await state.get_data()
    gb = data.get("traffic_gb")
    days = data.get("days")
    devices = data.get("device_limit")
    if not gb or not days or not devices:
        await callback.answer("Соберите тариф заново", show_alert=True)
        return
    try:
        order = await api.create_custom_order(
            callback.from_user.id,
            traffic_gb=int(gb),
            days=int(days),
            device_limit=int(devices),
        )
    except Exception as exc:
        await callback.answer(f"Ошибка: {exc}", show_alert=True)
        return
    await state.clear()
    title = escape(str(order.get("title") or "Свой тариф"))
    await callback.message.edit_text(
        f"✅ Заказ создан: <b>{title}</b>\n"
        f"Сумма: <b>{escape(str(order['amount']))} ₽</b>\n\n"
        "Оплатите через ЮMoney — после оплаты подписка активируется сама "
        "и появится ваша ссылка в «Моя подписка».\n"
        f"Метка платежа: <code>{escape(str(order['payment_label']))}</code>",
        parse_mode="HTML",
    )
    await callback.message.answer(  # type: ignore[union-attr]
        "Ссылка на оплату:",
        reply_markup=pay_keyboard(order["payment_url"]),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def buy_plan(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    assert callback.from_user and callback.data and callback.message
    plan_id = callback.data.split(":", 1)[1]
    try:
        order = await api.create_order(callback.from_user.id, plan_id)
    except Exception as exc:
        await callback.answer(f"Ошибка: {exc}", show_alert=True)
        return
    title = escape(str((order.get("meta") or {}).get("title") or order.get("title") or "Тариф"))
    await callback.message.answer(  # type: ignore[union-attr]
        f"Заказ: <b>{title}</b>\n"
        f"Сумма: <b>{escape(str(order['amount']))} ₽</b>\n\n"
        "Оплатите через ЮMoney — после оплаты подписка активируется сама.\n"
        f"Метка платежа: <code>{escape(str(order['payment_label']))}</code>",
        reply_markup=pay_keyboard(order["payment_url"]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("mysub"))
@router.message(F.text == "📱 Моя подписка")
async def cmd_mysub(message: Message, state: FSMContext) -> None:
    await state.clear()
    settings = get_settings()
    user = message.from_user
    assert user
    data = await api.auth(user.id, user.username)
    token = data["access_token"]
    me = await api.me(token)
    sub = me.get("subscription")
    await message.answer(
        format_subscription_card(sub, brand=settings.brand_name),
        parse_mode="HTML",
        reply_markup=_sub_keyboard(sub) if sub else None,
    )


@router.callback_query(F.data == "show_sub_url")
async def show_sub_url(callback: CallbackQuery) -> None:
    user = callback.from_user
    assert user
    data = await api.auth(user.id, user.username)
    me = await api.me(data["access_token"])
    sub = me.get("subscription")
    if not sub or not sub.get("sub_url"):
        await callback.answer("Нет подписки", show_alert=True)
        return
    await callback.message.answer(  # type: ignore[union-attr]
        "Ссылка подписки (если нужно добавить вручную):\n"
        f"<code>{sub['sub_url']}</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "devices:list")
async def devices_list(callback: CallbackQuery) -> None:
    user = callback.from_user
    assert user and callback.message
    data = await api.auth(user.id, user.username)
    try:
        payload = await api.list_devices(data["access_token"])
    except Exception as exc:
        await callback.answer(f"Ошибка: {exc}", show_alert=True)
        return
    await callback.message.edit_text(  # type: ignore[union-attr]
        _devices_text(payload),
        parse_mode="HTML",
        reply_markup=devices_keyboard(payload.get("devices") or []),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("devices:kick:"))
async def devices_kick(callback: CallbackQuery) -> None:
    user = callback.from_user
    assert user and callback.data and callback.message
    device_id = callback.data.rsplit(":", 1)[-1]
    data = await api.auth(user.id, user.username)
    token = data["access_token"]
    try:
        await api.kick_device(token, device_id)
        payload = await api.list_devices(token)
    except Exception as exc:
        await callback.answer(f"Не удалось отключить: {exc}", show_alert=True)
        return
    await callback.message.edit_text(  # type: ignore[union-attr]
        "✅ Устройство отключено.\n\n" + _devices_text(payload),
        parse_mode="HTML",
        reply_markup=devices_keyboard(payload.get("devices") or []),
    )
    await callback.answer("Устройство отключено")


@router.callback_query(F.data == "devices:back")
async def devices_back(callback: CallbackQuery) -> None:
    settings = get_settings()
    user = callback.from_user
    assert user and callback.message
    data = await api.auth(user.id, user.username)
    me = await api.me(data["access_token"])
    sub = me.get("subscription")
    await callback.message.edit_text(  # type: ignore[union-attr]
        format_subscription_card(sub, brand=settings.brand_name),
        parse_mode="HTML",
        reply_markup=_sub_keyboard(sub),
    )
    await callback.answer()


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = (
        "Как подключиться:\n"
        "1. Установите Happ (iOS / Android / Windows / macOS)\n"
        "2. В боте откройте «📱 Моя подписка»\n"
        "3. Нажмите «🚀 Открыть в Happ» — подписка добавится сама\n"
        "4. В Happ обновите подписку и включите сервер Finland\n\n"
        "Тарифы: ограниченный / вечный / свой.\n"
        f"Сайт: https://{get_settings().domain}"
    )
    await message.answer(text)


@router.message(Command("support"))
@router.message(F.text == "💬 Поддержка")
async def cmd_support(message: Message, state: FSMContext) -> None:
    await state.clear()
    settings = get_settings()
    await message.answer(
        f"Напишите в поддержку: {settings.support_telegram}\n"
        "Или просто отправьте сообщение сюда — мы увидим его."
    )


@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def forward_support(message: Message) -> None:
    """Forward free-text to admins if configured."""
    settings = get_settings()
    if not settings.admin_telegram_ids:
        return
    if message.text in {"🛒 Тарифы", "📱 Моя подписка", "❓ Помощь", "💬 Поддержка"}:
        return
    user = message.from_user
    assert user
    if user.id in settings.admin_telegram_ids:
        return
    for admin_id in settings.admin_telegram_ids:
        try:
            await message.bot.send_message(
                admin_id,
                f"📩 Support from {user.id} @{user.username}:\n{message.text}",
            )
        except Exception:
            pass
    await message.answer("Сообщение отправлено в поддержку.")
