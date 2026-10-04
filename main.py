"""Точка входа для Bothost: веб + webhook бота на 0.0.0.0:$PORT."""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        app_dir=os.path.join(os.path.dirname(__file__), "backend"),
    )