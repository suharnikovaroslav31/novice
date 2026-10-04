"""
Telegram-бот, который открывает Mini App NOVICE.

Запуск:
  python bot.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("novice-bot")


async def main() -> None:
    token = os.getenv("BOT_TOKEN", "").strip()
    webapp_url = os.getenv("WEBAPP_URL", "").strip()

    if not token:
        logger.error("Укажи BOT_TOKEN в .env")
        sys.exit(1)
    if not webapp_url:
        logger.error("Укажи WEBAPP_URL в .env (HTTPS URL фронтенда)")
        sys.exit(1)

    bot = Bot(token=token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message) -> None:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Открыть NOVICE",
                        web_app=WebAppInfo(url=webapp_url),
                    )
                ]
            ]
        )
        await message.answer(
            "NOVICE ищет самые дешёвые Telegram NFT у новичков:\n"
            "• уровень аккаунта ≤ 1\n"
            "• не больше 2 NFT у продавца\n"
            "• без перекупов\n\n"
            "Жми кнопку ниже 👇",
            reply_markup=kb,
        )

    @dp.message(F.text)
    async def any_text(message: Message) -> None:
        await start(message)

    logger.info("Bot started. WebApp: %s", webapp_url)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
