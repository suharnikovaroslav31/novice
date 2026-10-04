from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .aggregator import Aggregator
from .app_config import get_telegram_api, save_config
from .config import get_settings, public_base_url
from .market_auth import confirm_phone_login, start_phone_login
from .models import (
    AutoLoginConfirmRequest,
    AutoLoginStartRequest,
    DisconnectRequest,
    HealthResponse,
    SaveTelegramApiRequest,
    SaveTokensRequest,
    SearchFilters,
    SearchRequest,
    SearchResponse,
    SourceName,
    UserTokens,
)
from .telegram_bot import bot_token, build_dispatcher
from .tg_webapp import user_id_from_init
from .user_store import account_status, clear_token, load_user, upsert_tokens

logger = logging.getLogger("novice")

settings = get_settings()
aggregator = Aggregator(settings)

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    token = bot_token() or settings.bot_token
    app.state.bot = None
    app.state.dp = None
    if token:
        from aiogram import Bot

        bot = Bot(token=token)
        dp = build_dispatcher()
        app.state.bot = bot
        app.state.dp = dp
        base = public_base_url()
        webhook = os.getenv("WEBHOOK_URL", "").strip()
        if not webhook and base.startswith("https://"):
            webhook = base.rstrip("/") + "/webhook"
        if webhook.startswith("https://"):
            await bot.set_webhook(webhook, drop_pending_updates=True)
            from aiogram.types import MenuButtonWebApp, WebAppInfo

            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="NOVICE",
                    web_app=WebAppInfo(url=base),
                )
            )
            logger.info("Webhook and mini app set: %s", base)
        else:
            logger.info("Mini app skipped, base url is %s", base)
    yield
    bot = getattr(app.state, "bot", None)
    if bot is not None:
        await bot.session.close()


app = FastAPI(
    title="NOVICE",
    description="Парсер самых дешёвых Telegram NFT от новичков (не перекупов).",
    version="1.1.0",
    lifespan=lifespan,
)

origins = (
    ["*"]
    if settings.cors_origins.strip() == "*"
    else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_user_id(init_data: str | None, user_id: str | None, x_user_id: str | None = None) -> str:
    if init_data:
        try:
            return user_id_from_init(init_data, settings.bot_token)
        except ValueError as exc:
            # в локалке без валидной подписи падаем на явный user_id
            if user_id or x_user_id:
                return str(user_id or x_user_id)
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    return str(user_id or x_user_id or "local-dev")


def _merge_tokens(user_id: str, override: UserTokens | None = None) -> dict[str, str]:
    stored = (load_user(user_id).get("tokens") or {}) if user_id else {}
    merged = {
        "mrkt": stored.get("mrkt") or settings.mrkt_token or "",
        "portals": stored.get("portals") or settings.portals_token or "",
        "tonnel": stored.get("tonnel") or settings.tonnel_auth or "",
    }
    if override:
        if override.mrkt:
            merged["mrkt"] = override.mrkt
        if override.portals:
            merged["portals"] = override.portals
        if override.tonnel:
            merged["tonnel"] = override.tonnel
    return {k: v for k, v in merged.items() if v}


@app.get("/health")
async def health_probe():
    return {"ok": True}


@app.post("/webhook")
async def telegram_webhook(request: Request):
    bot = getattr(request.app.state, "bot", None)
    dp = getattr(request.app.state, "dp", None)
    if bot is None or dp is None:
        raise HTTPException(status_code=503, detail="Бот не запущен: нет BOT_TOKEN")
    payload = await request.json()
    update = Update.model_validate(payload, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        demo_mode=settings.demo_mode,
        configured_sources=aggregator.configured_sources(),
    )


@app.get("/api/accounts")
async def get_accounts(
    init_data: str | None = None,
    user_id: str | None = None,
    x_telegram_init_data: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
):
    uid = _resolve_user_id(init_data or x_telegram_init_data, user_id, x_user_id)
    return account_status(
        uid,
        {
            "mrkt": settings.mrkt_token,
            "portals": settings.portals_token,
            "tonnel": settings.tonnel_auth,
        },
    )


@app.post("/api/accounts/save")
async def save_accounts(body: SaveTokensRequest):
    uid = _resolve_user_id(body.init_data, body.user_id)
    data = upsert_tokens(
        uid,
        {
            "mrkt": body.tokens.mrkt,
            "portals": body.tokens.portals,
            "tonnel": body.tokens.tonnel,
        },
    )
    return {
        "ok": True,
        "user_id": uid,
        "status": account_status(
            uid,
            {
                "mrkt": settings.mrkt_token,
                "portals": settings.portals_token,
                "tonnel": settings.tonnel_auth,
            },
        ),
        "saved": list((data.get("tokens") or {}).keys()),
    }


@app.post("/api/accounts/disconnect")
async def disconnect_account(body: DisconnectRequest):
    uid = _resolve_user_id(body.init_data, body.user_id)
    source = body.source.strip().lower()
    if source not in {"mrkt", "portals", "tonnel"}:
        raise HTTPException(status_code=400, detail="Неизвестный источник")
    clear_token(uid, source)
    return {
        "ok": True,
        "status": account_status(
            uid,
            {
                "mrkt": settings.mrkt_token,
                "portals": settings.portals_token,
                "tonnel": settings.tonnel_auth,
            },
        ),
    }


@app.get("/api/accounts/auto/config")
async def auto_config():
    api_id, api_hash = get_telegram_api(settings.tg_api_id, settings.tg_api_hash)
    ready = bool(api_id and api_hash)
    return {
        "phone_only": ready,
        "needs_api_setup": not ready,
        "hint": "Вход по номеру и коду. my.telegram.org не нужен.",
    }


@app.post("/api/setup/telegram-api")
async def setup_telegram_api(body: SaveTelegramApiRequest):
    """Один раз сохраняем api_id/hash — пользователям потом нужен только телефон."""
    save_config({"tg_api_id": body.api_id, "tg_api_hash": body.api_hash.strip()})
    return {"ok": True, "phone_only": True}


@app.post("/api/accounts/auto/start")
async def auto_start(body: AutoLoginStartRequest):
    uid = _resolve_user_id(body.init_data, body.user_id)
    api_id, api_hash = get_telegram_api(settings.tg_api_id, settings.tg_api_hash)
    if body.api_id and body.api_hash:
        api_id, api_hash = body.api_id, body.api_hash.strip()
        save_config({"tg_api_id": api_id, "tg_api_hash": api_hash})
    if not api_id or not api_hash:
        raise HTTPException(
            status_code=400,
            detail="Сначала один раз укажи api_id и api_hash (кнопка ниже). Потом вход будет только по телефону.",
        )
    try:
        result = await start_phone_login(api_id, api_hash, body.phone.strip())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "user_id": uid, **result}


@app.post("/api/accounts/auto/confirm")
async def auto_confirm(body: AutoLoginConfirmRequest):
    uid = _resolve_user_id(body.init_data, body.user_id)
    try:
        tokens = await confirm_phone_login(body.login_id, body.code, body.password)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    upsert_tokens(uid, tokens)
    return {
        "ok": True,
        "connected": list(tokens.keys()),
        "tokens": tokens,
        "status": account_status(
            uid,
            {
                "mrkt": settings.mrkt_token,
                "portals": settings.portals_token,
                "tonnel": settings.tonnel_auth,
            },
        ),
    }


@app.get("/api/search", response_model=SearchResponse)
async def search(
    max_seller_level: int = Query(1, ge=0, le=20),
    max_seller_nfts: int = Query(2, ge=1, le=50),
    max_price_ton: float | None = Query(None, ge=0),
    min_price_ton: float | None = Query(None, ge=0),
    collections: str | None = Query(None, description="Через запятую"),
    sources: str | None = Query(None, description="mrkt,portals,tonnel,demo"),
    only_novice: bool = True,
    exclude_resellers: bool = True,
    query: str | None = None,
    limit: int = Query(60, ge=1, le=200),
    init_data: str | None = None,
    user_id: str | None = None,
    x_telegram_init_data: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_mrkt_token: str | None = Header(default=None),
    x_portals_token: str | None = Header(default=None),
    x_tonnel_token: str | None = Header(default=None),
) -> SearchResponse:
    source_list: list[SourceName] = []
    if sources:
        for part in sources.split(","):
            part = part.strip().lower()
            if part:
                source_list.append(SourceName(part))

    filters = SearchFilters(
        max_seller_level=max_seller_level,
        max_seller_nfts=max_seller_nfts,
        max_price_ton=max_price_ton,
        min_price_ton=min_price_ton,
        collections=[c.strip() for c in (collections or "").split(",") if c.strip()],
        sources=source_list,
        only_novice=only_novice,
        exclude_resellers=exclude_resellers,
        query=query,
        limit=limit,
    )
    uid = _resolve_user_id(init_data or x_telegram_init_data, user_id, x_user_id)
    tokens = _merge_tokens(
        uid,
        UserTokens(mrkt=x_mrkt_token, portals=x_portals_token, tonnel=x_tonnel_token),
    )
    return await aggregator.search(filters, tokens=tokens)


@app.post("/api/search", response_model=SearchResponse)
async def search_post(body: SearchRequest) -> SearchResponse:
    uid = _resolve_user_id(body.init_data, None)
    tokens = _merge_tokens(uid, body.tokens)
    return await aggregator.search(body.filters, tokens=tokens)


@app.get("/")
async def miniapp_index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/styles.css")
async def miniapp_css():
    return FileResponse(WEB_DIR / "styles.css", media_type="text/css")


@app.get("/app.js")
async def miniapp_js():
    return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")
