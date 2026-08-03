from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.api_client import ApiClient
from bot.config import get_settings
from bot.keyboards.common import (
    format_subscription_card,
    main_menu,
    pay_keyboard,
    plans_keyboard,
    subscription_keyboard,
)

router = Router()
api = ApiClient()


def _sub_keyboard(sub: dict):
    return subscription_keyboard(sub.get("sub_url") or "", sub.get("happ_open_url") or "")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
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
        f"Заказ на <b>{order['amount']} ₽</b> создан.\n\n"
        "Оплатите через ЮMoney — после оплаты подписка активируется сама.\n"
        f"Если понадобится поддержка, метка платежа: <code>{order['payment_label']}</code>",
        reply_markup=pay_keyboard(order["payment_url"]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("mysub"))
@router.message(F.text == "📱 Моя подписка")
async def cmd_mysub(message: Message) -> None:
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


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    text = (
        "Как подключиться:\n"
        "1. Установите Happ (iOS / Android / Windows / macOS)\n"
        "2. В боте откройте «📱 Моя подписка»\n"
        "3. Нажмите «🚀 Открыть в Happ» — подписка добавится сама\n"
        "4. В Happ обновите подписку и включите сервер Finland\n\n"
        f"Сайт: https://{get_settings().domain}"
    )
    await message.answer(text)


@router.message(Command("support"))
@router.message(F.text == "💬 Поддержка")
async def cmd_support(message: Message) -> None:
    settings = get_settings()
    await message.answer(
        f"Напишите в поддержку: {settings.support_telegram}\n"
        "Или просто отправьте сообщение сюда — мы увидим его."
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
