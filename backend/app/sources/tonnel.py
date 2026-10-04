from __future__ import annotations

from typing import Any

import httpx

from ..config import Settings
from ..models import NftListing, SearchFilters, SellerProfile, SourceName
from .base import SourceAdapter


class TonnelSource(SourceAdapter):
    """Tonnel marketplace listings (auth_data required)."""

    name = "tonnel"
    API = "https://gifts2.tonnel.network/api"

    def __init__(self, settings: Settings, token: str | None = None):
        self.settings = settings
        self.token = (token or settings.tonnel_auth or "").strip()

    def is_configured(self) -> bool:
        return bool(self.token)

    async def fetch(self, filters: SearchFilters) -> list[NftListing]:
        if not self.is_configured():
            return []

        payload: dict[str, Any] = {
            "page": 1,
            "limit": min(50, filters.limit),
            "sort": "price_asc",
            "filter": {},
            "ref": 0,
            "price_range": None,
            "authData": self.token,
        }
        if filters.query:
            payload["filter"]["gift_name"] = filters.query
        if filters.collections:
            payload["filter"]["gift_name"] = filters.collections[0]
        if filters.min_price_ton is not None or filters.max_price_ton is not None:
            payload["price_range"] = {
                "min": filters.min_price_ton,
                "max": filters.max_price_ton,
            }

        items: list[NftListing] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for page in range(1, 4):
                payload["page"] = page
                resp = await client.post(f"{self.API}/pageGifts", json=payload)
                if resp.status_code >= 400:
                    # fallback endpoint name used by some clients
                    resp = await client.post(f"{self.API}/gift/list", json=payload)
                resp.raise_for_status()
                data = resp.json()
                rows = data.get("gifts") or data.get("data") or data.get("results") or []
                if isinstance(rows, dict):
                    rows = rows.get("gifts") or []
                if not rows:
                    break
                for row in rows:
                    listing = self._map(row)
                    if listing:
                        items.append(listing)
                if len(rows) < payload["limit"]:
                    break

        return items

    def _map(self, g: dict[str, Any]) -> NftListing | None:
        try:
            price = float(g.get("price") or g.get("amount") or 0)
            seller_raw = g.get("seller") or g.get("owner") or {}
            if isinstance(seller_raw, str):
                seller_raw = {"id": seller_raw}

            name = g.get("name") or g.get("gift_name") or g.get("title") or "Gift"
            number = g.get("gift_num") or g.get("number")
            try:
                number_i = int(number) if number is not None else None
            except (TypeError, ValueError):
                number_i = None

            return NftListing(
                id=str(g.get("gift_id") or g.get("id") or f"{name}-{number}"),
                source=SourceName.TONNEL,
                title=f"{name}" + (f" #{number_i}" if number_i else ""),
                collection=str(name),
                model=_as_str(g.get("model")),
                backdrop=_as_str(g.get("backdrop")),
                symbol=_as_str(g.get("symbol")),
                number=number_i,
                price_ton=round(price, 4),
                image_url=_as_str(g.get("customEmoji") or g.get("photo") or g.get("image")),
                url=_as_str(g.get("url")) or "https://t.me/tonnel_network_bot",
                seller=SellerProfile(
                    id=str(seller_raw.get("id") or seller_raw.get("user_id") or "unknown"),
                    username=_as_str(seller_raw.get("username")),
                    display_name=_as_str(seller_raw.get("name")),
                    level=_to_int(seller_raw.get("level")),
                    nft_count=_to_int(seller_raw.get("nfts") or seller_raw.get("gifts_count")),
                    sales_count=_to_int(seller_raw.get("sales")),
                    is_reseller=bool(seller_raw.get("is_reseller")),
                    raw=seller_raw if isinstance(seller_raw, dict) else {},
                ),
                listed_at=_as_str(g.get("export_at") or g.get("listed_at")),
            )
        except Exception:
            return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
