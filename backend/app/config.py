import os
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = ""
    webapp_url: str = "http://localhost:5173"

    tg_api_id: int | None = None
    tg_api_hash: str = ""
    tg_session_string: str = ""

    @field_validator("tg_api_id", mode="before")
    @classmethod
    def empty_api_id(cls, value: Any) -> Any:
        if _blank(value):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @field_validator(
        "bot_token",
        "webapp_url",
        "tg_api_hash",
        "tg_session_string",
        "mrkt_token",
        "portals_token",
        "tonnel_auth",
        mode="before",
    )
    @classmethod
    def blank_placeholder(cls, value: Any) -> Any:
        if _blank(value):
            return ""
        return value

    mrkt_token: str = ""
    portals_token: str = ""
    tonnel_auth: str = ""

    demo_mode: bool = True

    max_seller_level: int = 1
    max_seller_nfts: int = 2
    max_price_ton: float | None = None

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "*"


def _blank(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip().lower()
    return text in {"", "значение", "none", "null", "undefined"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def public_base_url() -> str:
    """HTTPS-адрес мини-апки. На Bothost берётся из DOMAIN / WEBHOOK_URL."""
    explicit = os.getenv("WEBAPP_URL", "").strip() or get_settings().webapp_url
    domain = os.getenv("DOMAIN", "").strip()
    webhook = os.getenv("WEBHOOK_URL", "").strip()

    if _blank(domain):
        domain = ""
    if _blank(webhook):
        webhook = ""
    if _blank(explicit) or explicit.startswith("http://localhost") or explicit.startswith("http://127.0.0.1"):
        explicit = ""

    if domain:
        base = domain if domain.startswith("http") else f"https://{domain}"
        return base.rstrip("/")
    if webhook:
        return webhook.split("/webhook")[0].rstrip("/")
    return explicit.rstrip("/")
