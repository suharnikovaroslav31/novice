from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# pending phone logins: login_id -> state
_PENDING: dict[str, dict[str, Any]] = {}


async def start_phone_login(api_id: int, api_hash: str, phone: str) -> dict[str, Any]:
    try:
        from pyrogram import Client
    except ImportError as exc:
        raise RuntimeError(
            "Для автопривязки установи: pip install pyrogram curl_cffi"
        ) from exc

    login_id = uuid.uuid4().hex
    session_name = f"novice_login_{login_id[:10]}"
    client = Client(session_name, api_id=api_id, api_hash=api_hash, in_memory=True)
    await client.connect()
    try:
        sent = await client.send_code(phone)
    except Exception:
        await client.disconnect()
        raise

    _PENDING[login_id] = {
        "client": client,
        "phone": phone,
        "phone_code_hash": sent.phone_code_hash,
        "api_id": api_id,
        "api_hash": api_hash,
        "session_name": session_name,
    }
    return {
        "login_id": login_id,
        "message": "Код отправлен в Telegram. Введи его ниже.",
    }


async def confirm_phone_login(login_id: str, code: str, password: str | None = None) -> dict[str, str]:
    state = _PENDING.get(login_id)
    if not state:
        raise ValueError("Сессия входа не найдена. Начни привязку заново.")

    client = state["client"]
    try:
        try:
            await client.sign_in(
                phone_number=state["phone"],
                phone_code_hash=state["phone_code_hash"],
                phone_code=code.strip(),
            )
        except Exception as exc:
            # 2FA
            if "SESSION_PASSWORD_NEEDED" in str(exc) or "password" in str(exc).lower():
                if not password:
                    raise ValueError("Нужен пароль 2FA облака Telegram") from exc
                await client.check_password(password)
            else:
                raise

        tokens = await fetch_all_market_tokens(client)
        return tokens
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
        _PENDING.pop(login_id, None)


async def fetch_all_market_tokens(client) -> dict[str, str]:
    """Достаёт токены MRKT / Portals / Tonnel через WebApp initData."""
    from pyrogram.raw.functions.messages import RequestAppWebView
    from pyrogram.raw.types import InputBotAppShortName, InputUser

    try:
        from curl_cffi import requests as crequests
    except ImportError:
        import requests as crequests  # type: ignore

    markets = {
        "mrkt": ("mrkt", "app"),
        "portals": ("portals", "market"),
        "tonnel": ("tonnel_network_bot", "auction"),
    }

    tokens: dict[str, str] = {}

    for key, (bot_username, short_name) in markets.items():
        try:
            init_data = await _get_init_data(client, bot_username, short_name, RequestAppWebView, InputBotAppShortName, InputUser)
            token = await asyncio.to_thread(_exchange_token, key, init_data, crequests)
            if token:
                tokens[key] = token
        except Exception as exc:
            logger.warning("Failed to auth %s: %s", key, exc)

    if not tokens:
        raise RuntimeError("Не удалось получить ни одного токена. Проверь, что маркет-боты открываются у тебя в Telegram.")
    return tokens


async def _get_init_data(client, bot_username, short_name, RequestAppWebView, InputBotAppShortName, InputUser) -> str:
    bot_entity = await client.get_users(bot_username)
    peer = await client.resolve_peer(bot_username)
    bot = InputUser(user_id=bot_entity.id, access_hash=bot_entity.raw.access_hash)
    bot_app = InputBotAppShortName(bot_id=bot, short_name=short_name)
    web_view = await client.invoke(
        RequestAppWebView(peer=peer, app=bot_app, platform="android")
    )
    return unquote(web_view.url.split("tgWebAppData=", 1)[1].split("&tgWebAppVersion", 1)[0])


def _exchange_token(market: str, init_data: str, requests_mod) -> str | None:
    if market == "mrkt":
        r = requests_mod.post(
            "https://api.tgmrkt.io/api/v1/auth",
            json={"data": init_data},
            timeout=30,
        )
        data = r.json()
        return data.get("token")

    if market == "portals":
        # Portals часто принимает tma <initData>
        return f"tma {init_data}"

    if market == "tonnel":
        # Tonnel authData = initData (как есть)
        return init_data

    return None
