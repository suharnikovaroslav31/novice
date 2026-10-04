from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceName(str, Enum):
    MRKT = "mrkt"
    PORTALS = "portals"
    TONNEL = "tonnel"
    DEMO = "demo"


class SellerProfile(BaseModel):
    id: str
    username: str | None = None
    display_name: str | None = None
    level: int | None = None
    nft_count: int | None = None
    sales_count: int | None = None
    is_reseller: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)


class NftListing(BaseModel):
    id: str
    source: SourceName
    title: str
    collection: str
    model: str | None = None
    backdrop: str | None = None
    symbol: str | None = None
    number: int | None = None
    price_ton: float
    currency: str = "TON"
    image_url: str | None = None
    url: str | None = None
    seller: SellerProfile
    listed_at: str | None = None
    novice_score: float = 0.0
    reasons: list[str] = Field(default_factory=list)


class SearchFilters(BaseModel):
    max_seller_level: int = 1
    max_seller_nfts: int = 2
    max_price_ton: float | None = None
    min_price_ton: float | None = None
    collections: list[str] = Field(default_factory=list)
    sources: list[SourceName] = Field(default_factory=list)
    only_novice: bool = True
    exclude_resellers: bool = True
    query: str | None = None
    limit: int = 60


class UserTokens(BaseModel):
    mrkt: str | None = None
    portals: str | None = None
    tonnel: str | None = None


class SearchRequest(BaseModel):
    filters: SearchFilters = Field(default_factory=SearchFilters)
    tokens: UserTokens | None = None
    init_data: str | None = None


class SearchResponse(BaseModel):
    items: list[NftListing]
    total: int
    demo: bool
    sources_used: list[str]
    sources_failed: list[str] = Field(default_factory=list)
    applied_filters: SearchFilters


class HealthResponse(BaseModel):
    ok: bool
    demo_mode: bool
    configured_sources: list[str]


class SaveTokensRequest(BaseModel):
    init_data: str | None = None
    user_id: str | None = None
    tokens: UserTokens


class DisconnectRequest(BaseModel):
    init_data: str | None = None
    user_id: str | None = None
    source: str


class AutoLoginStartRequest(BaseModel):
    init_data: str | None = None
    user_id: str | None = None
    phone: str
    api_id: int | None = None
    api_hash: str | None = None


class AutoLoginConfirmRequest(BaseModel):
    init_data: str | None = None
    user_id: str | None = None
    login_id: str
    code: str
    password: str | None = None


class SaveTelegramApiRequest(BaseModel):
    api_id: int
    api_hash: str
