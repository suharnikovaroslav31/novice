from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from ..config import Settings
from ..models import NftListing, SearchFilters, SellerProfile, SourceName
from .base import SourceAdapter


class PortalsSource(SourceAdapter):
    name = "portals"
    API = "https://portal-market.com/api"

    def __init__(self, settings: Settings, token: str | None = None):
        self.settings = settings
        self.token = (token or settings.portals_token or "").strip()

    def is_configured(self) -> bool:
        return bool(self.token)

    async def fetch(self, filters: SearchFilters) -> list[NftListing]:
        if not self.is_configured():
            return []

        headers = {
            "Authorization": self.token,
            "Accept": "application/json",
        }
        params: dict[str, Any] = {
            "offset": 0,
            "limit": min(100, filters.limit),
            "sort_by": "price asc",
            "status": "listed",
        }
        if filters.min_price_ton is not None:
            params["min_price"] = filters.min_price_ton
        if filters.max_price_ton is not None:
            params["max_price"] = filters.max_price_ton

        items: list[NftListing] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for offset in range(0, 300, 100):
                params["offset"] = offset
                url = f"{self.API}/nfts/search?{urlencode(params)}"
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results") or data.get("nfts") or []
                if not results:
                    break
                for row in results:
                    listing = self._map(row)
                    if listing:
                        items.append(listing)
                if len(results) < 100 or len(items) >= filters.limit:
                    break

        return items

    def _map(self, g: dict[str, Any]) -> NftListing | None:
        try:
            price = float(g.get("price") or g.get("floor_price") or 0)
            seller_raw = g.get("owner") or g.get("seller") or g.get("user") or {}
            if isinstance(seller_raw, str):
                seller_raw = {"id": seller_raw}

            collection = g.get("collection") or {}
            if isinstance(collection, dict):
                collection_name = collection.get("name") or collection.get("title") or "Unknown"
            else:
                collection_name = str(collection or g.get("name") or "Unknown")

            number = g.get("external_collection_number") or g.get("number")
            try:
                number_i = int(number) if number is not None else None
            except (TypeError, ValueError):
                number_i = None

            attributes = g.get("attributes") or {}
            model = _attr(attributes, g, "model")
            backdrop = _attr(attributes, g, "backdrop")
            symbol = _attr(attributes, g, "symbol")

            return NftListing(
                id=str(g.get("id") or g.get("nft_id") or f"{collection_name}-{number}"),
                source=SourceName.PORTALS,
                title=f"{collection_name}" + (f" #{number_i}" if number_i else ""),
                collection=collection_name,
                model=model,
                backdrop=backdrop,
                symbol=symbol,
                number=number_i,
                price_ton=round(price, 4),
                image_url=_as_str(g.get("photo_url") or g.get("image") or g.get("animation_url")),
                url=_as_str(g.get("url")) or "https://t.me/portals/market",
                seller=SellerProfile(
                    id=str(seller_raw.get("id") or seller_raw.get("user_id") or "unknown"),
                    username=_as_str(seller_raw.get("username")),
                    display_name=_as_str(seller_raw.get("name") or seller_raw.get("display_name")),
                    level=_to_int(seller_raw.get("level") or seller_raw.get("lvl")),
                    nft_count=_to_int(
                        seller_raw.get("nfts_count")
                        or seller_raw.get("listed_count")
                        or seller_raw.get("items_count")
                    ),
                    sales_count=_to_int(seller_raw.get("sales_count") or seller_raw.get("sold")),
                    is_reseller=bool(seller_raw.get("is_reseller") or seller_raw.get("is_pro")),
                    raw=seller_raw if isinstance(seller_raw, dict) else {},
                ),
                listed_at=_as_str(g.get("listed_at") or g.get("updated_at")),
            )
        except Exception:
            return None


def _attr(attributes: Any, g: dict[str, Any], key: str) -> str | None:
    if isinstance(attributes, dict) and attributes.get(key):
        return str(attributes[key])
    val = g.get(key) or g.get(f"{key}_name") or g.get(f"filter_by_{key}s")
    return str(val) if val else None


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
