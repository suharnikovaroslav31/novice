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


DATA_DIR = _data_root() / "users"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()


def _path(user_id: str) -> Path:
    safe = "".join(ch for ch in str(user_id) if ch.isalnum() or ch in "-_")
    return DATA_DIR / f"{safe or 'anon'}.json"


def load_user(user_id: str) -> dict[str, Any]:
    path = _path(user_id)
    if not path.exists():
        return {"user_id": str(user_id), "tokens": {}}
    with _lock:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"user_id": str(user_id), "tokens": {}}


def save_user(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    path = _path(user_id)
    data = {**data, "user_id": str(user_id)}
    with _lock:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def upsert_tokens(user_id: str, tokens: dict[str, str | None]) -> dict[str, Any]:
    data = load_user(user_id)
    current = dict(data.get("tokens") or {})
    for key, value in tokens.items():
        if value is None:
            current.pop(key, None)
        elif value.strip() == "":
            current.pop(key, None)
        else:
            current[key] = value.strip()
    data["tokens"] = current
    return save_user(user_id, data)


def clear_token(user_id: str, source: str) -> dict[str, Any]:
    return upsert_tokens(user_id, {source: None})


def account_status(user_id: str, env_tokens: dict[str, str] | None = None) -> dict[str, Any]:
    data = load_user(user_id)
    tokens = dict(data.get("tokens") or {})
    env_tokens = env_tokens or {}
    sources = ["mrkt", "portals", "tonnel"]
    items = []
    for source in sources:
        user_token = bool(tokens.get(source))
        env_token = bool(env_tokens.get(source))
        items.append(
            {
                "source": source,
                "connected": user_token or env_token,
                "from_user": user_token,
                "from_env": env_token and not user_token,
            }
        )
    return {
        "user_id": str(user_id),
        "accounts": items,
        "connected_count": sum(1 for i in items if i["connected"]),
    }
