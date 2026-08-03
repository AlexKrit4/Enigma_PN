from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.api_client import ApiClient
from bot.config import get_settings
from bot.keyboards.common import main_menu, pay_keyboard, plans_keyboard, subscription_keyboard

router = Router()
api = ApiClient()


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in get_settings().admin_telegram_ids


def _fmt_sub(sub: dict | None) -> str:
    if not sub:
        return "Активной подписки нет."
    limit = sub.get("traffic_limit_gb")
    used = sub.get("traffic_used_gb")
    return (
        f"Статус: <b>{sub['status']}</b>\n"
        f"До: <b>{sub['ends_at']}</b>\n"
        f"Трафик: {used} / {limit if limit is not None else '∞'} GB\n"
        f"Устройств: {sub.get('device_limit')}\n"
        f"Ссылка подписки:\n<code>{sub.get('sub_url')}</code>"
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    settings = get_settings()
    user = message.from_user
    assert user
    data = await api.auth(user.id, user.username)
    sub = data.get("user", {}).get("subscription")
    text = (
        f"Привет! Это <b>{settings.brand_name}</b> — VPN для Happ.\n\n"
        f"Бот: @{settings.telegram_bot_username}\n"
        f"Сайт: https://{settings.domain}\n\n"
    )
    if not sub:
        try:
            trial = await api.trial(user.id, user.username)
            sub = trial.get("subscription")
            text += "✅ Выдан пробный период на 1 день (5 GB).\n\n"
        except Exception:
            text += "Пробный период недоступен (уже использован или выключен).\n\n"
    text += _fmt_sub(sub)
    kb = main_menu()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    if sub and sub.get("happ_deep_link"):
        await message.answer(
            "Подключитесь в Happ:",
            reply_markup=subscription_keyboard(sub["sub_url"], sub["happ_deep_link"]),
        )


@router.message(Command("plans"))
@router.message(F.text == "🛒 Тарифы")
async def cmd_plans(message: Message) -> None:
    plans = await api.plans()
    await message.answer("Выберите тариф:", reply_markup=plans_keyboard(plans))


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def buy_plan(callback: CallbackQuery) -> None:
    assert callback.from_user and callback.data
    plan_id = callback.data.split(":", 1)[1]
    order = await api.create_order(callback.from_user.id, plan_id)
    await callback.message.answer(  # type: ignore[union-attr]
        f"Заказ создан на <b>{order['amount']} ₽</b>.\n"
        f"Метка платежа: <code>{order['payment_label']}</code>\n\n"
        "Оплатите через ЮMoney. После поступления средств подписка активируется автоматически.",
        reply_markup=pay_keyboard(order["payment_url"]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("mysub"))
@router.message(F.text == "📱 Моя подписка")
async def cmd_mysub(message: Message) -> None:
    user = message.from_user
    assert user
    data = await api.auth(user.id, user.username)
    token = data["access_token"]
    me = await api.me(token)
    sub = me.get("subscription")
    await message.answer(_fmt_sub(sub), parse_mode="HTML")
    if sub and sub.get("happ_deep_link"):
        await message.answer(
            "Быстрое подключение:",
            reply_markup=subscription_keyboard(sub["sub_url"], sub["happ_deep_link"]),
        )


@router.callback_query(F.data == "show_sub_url")
async def show_sub_url(callback: CallbackQuery) -> None:
    user = callback.from_user
    assert user
    data = await api.auth(user.id, user.username)
    me = await api.me(data["access_token"])
    sub = me.get("subscription")
    if not sub:
        await callback.answer("Нет подписки", show_alert=True)
        return
    await callback.message.answer(f"<code>{sub['sub_url']}</code>", parse_mode="HTML")  # type: ignore[union-attr]
    await callback.answer()


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    text = (
        "Как подключиться:\n"
        "1. Скачайте Happ (iOS / Android / Desktop)\n"
        "2. Нажмите «Добавить в Happ» в боте\n"
        "3. Или: Happ → + → Импорт из URL → вставьте ссылку подписки\n"
        "4. Обновите подписку и подключитесь к серверу\n\n"
        f"Сайт: https://{get_settings().domain}"
    )
    await message.answer(text)


@router.message(Command("support"))
@router.message(F.text == "💬 Поддержка")
async def cmd_support(message: Message) -> None:
    settings = get_settings()
    await message.answer(
        f"Напишите в поддержку: {settings.support_telegram}\n"
        "Или просто отправьте сообщение сюда — админ получит его, если ID настроен."
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, command: CommandObject) -> None:
    user = message.from_user
    assert user
    if not _is_admin(user.id):
        # Fallback: if ADMIN_TELEGRAM_IDS empty, allow first message after warning
        if get_settings().admin_telegram_ids:
            await message.answer("Нет доступа")
            return
        await message.answer(
            "ADMIN_TELEGRAM_IDS не задан.\n"
            f"Ваш numeric ID: <code>{user.id}</code>\n"
            "Добавьте его в .env как ADMIN_TELEGRAM_IDS и перезапустите бота.",
            parse_mode="HTML",
        )
        return

    args = (command.args or "").split()
    if not args or args[0] == "stats":
        stats = await api.admin_stats()
        await message.answer(
            "📊 Статистика\n"
            f"Пользователи: {stats['users_total']}\n"
            f"Активные: {stats['subscriptions_active']}\n"
            f"Триал: {stats['subscriptions_trial']}\n"
            f"Оплаченных заказов: {stats['orders_paid']}\n"
            f"MRR ≈ {stats['mrr_rub']} ₽"
        )
        return

    if args[0] == "user" and len(args) >= 2:
        info = await api.admin_user(int(args[1]))
        await message.answer(str(info))
        return

    if args[0] == "extend" and len(args) >= 3:
        result = await api.admin_extend(int(args[1]), int(args[2]))
        await message.answer(f"Продлено до {result['ends_at']}")
        return

    if args[0] == "grant" and len(args) >= 3:
        # /admin grant TELEGRAM_ID DAYS [GB]
        tg_id = int(args[1])
        days = int(args[2])
        traffic_gb = int(args[3]) if len(args) >= 4 else None
        result = await api.admin_grant(tg_id, days, traffic_gb=traffic_gb)
        sub = result.get("subscription") or {}
        await message.answer(
            f"✅ Выдано на {days} дн.\n"
            f"До: {result.get('ends_at')}\n"
            f"URL: <code>{sub.get('sub_url')}</code>",
            parse_mode="HTML",
        )
        return

    if args[0] == "confirm" and len(args) >= 2:
        # /admin confirm PAYMENT_LABEL
        result = await api.admin_confirm_order(args[1])
        await message.answer(f"Заказ подтверждён: {result}")
        return

    await message.answer(
        "Команды админа:\n"
        "/admin stats\n"
        "/admin user ID\n"
        "/admin extend ID DAYS\n"
        "/admin grant ID DAYS [GB] — выдать бесплатную подписку\n"
        "/admin confirm LABEL — вручную подтвердить оплату"
    )


@router.message(F.text & ~F.text.startswith("/"))
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
