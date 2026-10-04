from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any


def _data_root() -> Path:
    env = os.getenv("DATA_DIR", "").strip()
    root = Path(env) if env else Path(__file__).resolve().parents[2] / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root


CONFIG_PATH = _data_root() / "app_config.json"
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with _lock:
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}


def save_config(update: dict[str, Any]) -> dict[str, Any]:
    data = load_config()
    data.update({k: v for k, v in update.items() if v is not None and v != ""})
    with _lock:
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


# Публичные ключи официального Telegram Desktop.
# my.telegram.org из РФ часто недоступен — с ними вход сразу по телефону и коду.
BUILTIN_API_ID = 2040
BUILTIN_API_HASH = "b18441a1ff607e10a989891a5462e627"


def get_telegram_api(env_api_id: int | None, env_api_hash: str) -> tuple[int | None, str]:
    cfg = load_config()
    api_id = env_api_id or cfg.get("tg_api_id") or BUILTIN_API_ID
    api_hash = env_api_hash or cfg.get("tg_api_hash") or BUILTIN_API_HASH
    try:
        api_id_i = int(api_id) if api_id not in (None, "") else None
    except (TypeError, ValueError):
        api_id_i = BUILTIN_API_ID
    return api_id_i, str(api_hash)
