from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def validate_init_data(init_data: str, bot_token: str, max_age_sec: int = 86400) -> dict:
    """
    Проверка Telegram Mini App initData.
    Если bot_token пустой — в dev-режиме принимаем без подписи (только для локалки).
    """
    if not init_data:
        raise ValueError("Нет initData. Открой приложение из Telegram.")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash and not bot_token:
        # локальный браузер без Telegram
        return {"id": "local-dev", "username": "local", "first_name": "Local"}

    if not bot_token:
        raise ValueError("BOT_TOKEN не задан на сервере")

    if not received_hash:
        raise ValueError("Некорректный initData")

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, received_hash):
        raise ValueError("Подпись initData невалидна")

    auth_date = int(parsed.get("auth_date") or 0)
    if auth_date and time.time() - auth_date > max_age_sec:
        raise ValueError("initData устарел — переоткрой Mini App")

    user_raw = parsed.get("user")
    if not user_raw:
        raise ValueError("В initData нет user")
    user = json.loads(user_raw)
    return user


def user_id_from_init(init_data: str, bot_token: str) -> str:
    user = validate_init_data(init_data, bot_token)
    return str(user.get("id") or "local-dev")
