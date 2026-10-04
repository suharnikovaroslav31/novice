from __future__ import annotations

import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from .config import public_base_url

logger = logging.getLogger("novice-bot")


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message) -> None:
        url = public_base_url()
        kb = None
        if url.startswith("https://"):
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Открыть NOVICE",
                            web_app=WebAppInfo(url=url),
                        )
                    ]
                ]
            )
        await message.answer(
            "NOVICE ищет самые дешёвые Telegram NFT у новичков:\n"
            "• уровень аккаунта ≤ 1\n"
            "• не больше 2 NFT у продавца\n"
            "• без перекупов\n\n"
            + (
                "Жми кнопку ниже 👇"
                if kb
                else "Мини-апп откроется, когда у бота будет HTTPS-домен."
            ),
            reply_markup=kb,
        )

    @dp.message(F.text)
    async def any_text(message: Message) -> None:
        await start(message)

    return dp


def bot_token() -> str:
    for key in ("BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "API_TOKEN"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""
