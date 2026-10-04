from __future__ import annotations

from typing import Any

import httpx

from ..config import Settings
from ..models import NftListing, SearchFilters, SellerProfile, SourceName
from .base import SourceAdapter


class MrktSource(SourceAdapter):
    name = "mrkt"
    API = "https://api.tgmrkt.io/api/v1"

    def __init__(self, settings: Settings, token: str | None = None):
        self.settings = settings
        self.token = (token or settings.mrkt_token or "").strip()

    def is_configured(self) -> bool:
        return bool(self.token)

    async def fetch(self, filters: SearchFilters) -> list[NftListing]:
        if not self.is_configured():
            return []

        headers = {
            "Authorization": self.token,
            "Referer": "https://cdn.tgmrkt.io/",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "collectionNames": filters.collections or [],
            "modelNames": [],
            "backdropNames": [],
            "symbolNames": [],
            "ordering": "Price",
            "lowToHigh": True,
            "maxPrice": filters.max_price_ton,
            "minPrice": filters.min_price_ton,
            "mintable": None,
            "number": None,
            "count": 20,
            "cursor": "",
            "query": filters.query,
            "promotedFirst": False,
        }

        items: list[NftListing] = []
        cursor = ""
        pages = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            while pages < 5 and len(items) < filters.limit:
                payload["cursor"] = cursor
                resp = await client.post(
                    f"{self.API}/gifts/saling",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                gifts = data.get("gifts") or data.get("items") or []
                if not gifts:
                    break
                for g in gifts:
                    listing = self._map(g)
                    if listing:
                        items.append(listing)
                cursor = data.get("cursor") or ""
                pages += 1
                if not cursor:
                    break

        return items

    def _map(self, g: dict[str, Any]) -> NftListing | None:
        try:
            price_raw = g.get("price") or g.get("salePrice") or g.get("amount") or 0
            price = float(price_raw) / (1e9 if float(price_raw) > 1000 else 1)
            if price > 10000:
                price = float(price_raw)

            seller_raw = g.get("seller") or g.get("owner") or g.get("user") or {}
            if isinstance(seller_raw, str):
                seller_raw = {"id": seller_raw}

            level = _pick_int(seller_raw, "level", "lvl", "accountLevel", "rank")
            nft_count = _pick_int(
                seller_raw,
                "nftCount",
                "giftsCount",
                "itemsCount",
                "listingsCount",
                "inventoryCount",
            )
            sales = _pick_int(seller_raw, "salesCount", "soldCount", "totalSales")

            collection = (
                g.get("collectionName")
                or g.get("collection")
                or g.get("name")
                or "Unknown"
            )
            if isinstance(collection, dict):
                collection = collection.get("name") or "Unknown"

            number = _pick_int(g, "number", "num", "externalCollectionNumber")
            title = f"{collection}" + (f" #{number}" if number else "")

            return NftListing(
                id=str(g.get("id") or g.get("giftId") or g.get("slug") or title),
                source=SourceName.MRKT,
                title=title,
                collection=str(collection),
                model=_as_str(g.get("modelName") or g.get("model")),
                backdrop=_as_str(g.get("backdropName") or g.get("backdrop")),
                symbol=_as_str(g.get("symbolName") or g.get("symbol")),
                number=number,
                price_ton=round(price, 4),
                image_url=_as_str(g.get("photoUrl") or g.get("image") or g.get("thumbnail")),
                url=_as_str(g.get("url") or g.get("link"))
                or f"https://t.me/mrkt?startapp={g.get('id', '')}",
                seller=SellerProfile(
                    id=str(seller_raw.get("id") or seller_raw.get("userId") or "unknown"),
                    username=_as_str(seller_raw.get("username")),
                    display_name=_as_str(
                        seller_raw.get("name") or seller_raw.get("displayName")
                    ),
                    level=level,
                    nft_count=nft_count,
                    sales_count=sales,
                    is_reseller=bool(seller_raw.get("isReseller") or seller_raw.get("isPro")),
                    raw=seller_raw if isinstance(seller_raw, dict) else {},
                ),
                listed_at=_as_str(g.get("listedAt") or g.get("createdAt")),
            )
        except Exception:
            return None


def _pick_int(data: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key in data and data[key] is not None:
            try:
                return int(data[key])
            except (TypeError, ValueError):
                continue
    return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get("name") or value.get("title")
    return str(value)
