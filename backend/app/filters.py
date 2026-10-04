from __future__ import annotations

from .models import NftListing, SearchFilters, SellerProfile


def is_reseller(seller: SellerProfile, max_nfts: int) -> bool:
    """Эвристика перекупа: много NFT, много продаж или явный флаг."""
    if seller.is_reseller:
        return True
    if seller.nft_count is not None and seller.nft_count > max_nfts:
        return True
    if seller.sales_count is not None and seller.sales_count >= 10:
        return True
    if seller.level is not None and seller.level > 1:
        return True
    return False


def is_novice_seller(
    seller: SellerProfile,
    *,
    max_level: int,
    max_nfts: int,
    exclude_resellers: bool,
) -> tuple[bool, list[str], float]:
    """
    Новичок:
    - уровень аккаунта <= max_level (по умолчанию 1)
    - не больше max_nfts NFT (по умолчанию 2)
    - не перекуп
    """
    reasons: list[str] = []
    score = 100.0

    if seller.level is None:
        reasons.append("уровень неизвестен — понижаем доверие")
        score -= 25
    elif seller.level > max_level:
        return False, [f"уровень {seller.level} > {max_level}"], 0
    else:
        reasons.append(f"уровень {seller.level}")
        score += max(0, (max_level - seller.level) * 5)

    if seller.nft_count is None:
        reasons.append("кол-во NFT неизвестно — понижаем доверие")
        score -= 20
    elif seller.nft_count > max_nfts:
        return False, [f"у продавца {seller.nft_count} NFT (лимит {max_nfts})"], 0
    else:
        reasons.append(f"{seller.nft_count} NFT у продавца")
        score += (max_nfts - seller.nft_count) * 8

    if exclude_resellers and is_reseller(seller, max_nfts):
        return False, ["похоже на перекупа"], 0

    if seller.sales_count is not None:
        if seller.sales_count == 0:
            reasons.append("продаж ещё не было")
            score += 10
        elif seller.sales_count <= 3:
            reasons.append(f"мало продаж ({seller.sales_count})")
            score += 5
        else:
            reasons.append(f"продаж: {seller.sales_count}")
            score -= min(30, seller.sales_count)

    return True, reasons, max(0.0, min(100.0, score))


def apply_filters(items: list[NftListing], filters: SearchFilters) -> list[NftListing]:
    result: list[NftListing] = []
    q = (filters.query or "").strip().lower()

    for item in items:
        if filters.sources and item.source not in filters.sources:
            continue
        if filters.collections:
            col = item.collection.lower()
            if not any(c.lower() in col or col in c.lower() for c in filters.collections):
                continue
        if filters.min_price_ton is not None and item.price_ton < filters.min_price_ton:
            continue
        if filters.max_price_ton is not None and item.price_ton > filters.max_price_ton:
            continue
        if q:
            hay = " ".join(
                filter(
                    None,
                    [
                        item.title,
                        item.collection,
                        item.model,
                        item.backdrop,
                        item.symbol,
                        item.seller.username,
                        item.seller.display_name,
                    ],
                )
            ).lower()
            if q not in hay:
                continue

        ok, reasons, score = is_novice_seller(
            item.seller,
            max_level=filters.max_seller_level,
            max_nfts=filters.max_seller_nfts,
            exclude_resellers=filters.exclude_resellers,
        )
        if filters.only_novice and not ok:
            continue

        item.reasons = reasons
        item.novice_score = score
        result.append(item)

    result.sort(key=lambda x: (x.price_ton, -x.novice_score))
    return result[: filters.limit]
