"""
Получает auth-токены маркетов через Telegram WebApp initData.

Нужно:
  TG_API_ID, TG_API_HASH из https://my.telegram.org
  Первый запуск попросит код из Telegram (создаст session файл).

Запуск из backend/:
  python tools/fetch_market_tokens.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from urllib.parse import unquote

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

try:
    from pyrogram import Client
    from pyrogram.raw.functions.messages import RequestAppWebView
    from pyrogram.raw.types import InputBotAppShortName, InputUser
    from curl_cffi import requests
except ImportError:
    print("Установи зависимости: pip install -r requirements.txt")
    sys.exit(1)


MARKETS = {
    "mrkt": {
        "bot": "mrkt",
        "short_name": "app",
        "auth_url": "https://api.tgmrkt.io/api/v1/auth",
        "env_key": "MRKT_TOKEN",
        "token_path": ("token",),
    },
    "portals": {
        "bot": "portals",
        "short_name": "market",
        "auth_url": None,  # часто используют raw initData как Bearer
        "env_key": "PORTALS_TOKEN",
        "token_path": None,
    },
}


async def get_init_data(client: Client, bot_username: str, short_name: str) -> str:
    bot_entity = await client.get_users(bot_username)
    peer = await client.resolve_peer(bot_username)
    bot = InputUser(user_id=bot_entity.id, access_hash=bot_entity.raw.access_hash)
    bot_app = InputBotAppShortName(bot_id=bot, short_name=short_name)
    web_view = await client.invoke(
        RequestAppWebView(peer=peer, app=bot_app, platform="android")
    )
    return unquote(web_view.url.split("tgWebAppData=", 1)[1].split("&tgWebAppVersion", 1)[0])


async def main() -> None:
    api_id = os.getenv("TG_API_ID")
    api_hash = os.getenv("TG_API_HASH")
    if not api_id or not api_hash:
        print("Заполни TG_API_ID и TG_API_HASH в .env")
        sys.exit(1)

    client = Client("novice_session", api_id=int(api_id), api_hash=api_hash)
    async with client:
        for name, cfg in MARKETS.items():
            try:
                init_data = await get_init_data(client, cfg["bot"], cfg["short_name"])
                if cfg["auth_url"]:
                    r = requests.post(cfg["auth_url"], json={"data": init_data})
                    data = r.json()
                    token = data.get("token")
                else:
                    token = f"tma {init_data}"
                print(f"\n{cfg['env_key']}=")
                print(token)
            except Exception as exc:
                print(f"\n[{name}] ошибка: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
