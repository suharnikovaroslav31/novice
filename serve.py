"""Локальный запуск Python-версии: python serve.py"""

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
