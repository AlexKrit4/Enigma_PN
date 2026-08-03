from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
from bot.handlers import admin as admin_handlers
from bot.handlers import start as start_handlers


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    # Admin router first so FSM states win over support forward.
    dp.include_router(admin_handlers.router)
    dp.include_router(start_handlers.router)

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot starting as @%s", settings.telegram_bot_username)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
