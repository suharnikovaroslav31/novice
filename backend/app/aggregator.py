from __future__ import annotations

import asyncio
import logging

from .config import Settings
from .filters import apply_filters
from .models import SearchFilters, SearchResponse, SourceName
from .sources import DemoSource, MrktSource, PortalsSource, TonnelSource

logger = logging.getLogger(__name__)


class Aggregator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.demo = DemoSource()

    def configured_sources(self, tokens: dict[str, str] | None = None) -> list[str]:
        tokens = tokens or {}
        names = []
        if tokens.get("mrkt") or self.settings.mrkt_token:
            names.append("mrkt")
        if tokens.get("portals") or self.settings.portals_token:
            names.append("portals")
        if tokens.get("tonnel") or self.settings.tonnel_auth:
            names.append("tonnel")
        if self.settings.demo_mode or not names:
            names.append("demo")
        return names

    def _build_sources(self, tokens: dict[str, str] | None = None):
        tokens = tokens or {}
        return [
            MrktSource(self.settings, tokens.get("mrkt")),
            PortalsSource(self.settings, tokens.get("portals")),
            TonnelSource(self.settings, tokens.get("tonnel")),
        ]

    async def search(
        self,
        filters: SearchFilters,
        tokens: dict[str, str] | None = None,
        force_demo: bool | None = None,
    ) -> SearchResponse:
        if filters.max_seller_level == 1 and self.settings.max_seller_level != 1:
            filters.max_seller_level = self.settings.max_seller_level
        if filters.max_seller_nfts == 2 and self.settings.max_seller_nfts != 2:
            filters.max_seller_nfts = self.settings.max_seller_nfts
        if filters.max_price_ton is None and self.settings.max_price_ton is not None:
            filters.max_price_ton = self.settings.max_price_ton

        wanted = set(filters.sources) if filters.sources else None
        tasks = []
        source_names: list[str] = []

        for source in self._build_sources(tokens):
            if not source.is_configured():
                continue
            if wanted and SourceName(source.name) not in wanted:
                continue
            tasks.append(self._safe_fetch(source, filters))
            source_names.append(source.name)

        demo_flag = self.settings.demo_mode if force_demo is None else force_demo
        use_demo = demo_flag or not tasks
        # Если пользователь явно подключил маркеты — demo только по запросу
        if tokens and any(tokens.values()) and force_demo is None:
            use_demo = SourceName.DEMO in (wanted or set()) and not tasks
            if not tasks and (not wanted or SourceName.DEMO in wanted):
                use_demo = True

        if use_demo and (not wanted or SourceName.DEMO in wanted or not tasks):
            if "demo" not in source_names:
                tasks.append(self._safe_fetch(self.demo, filters))
                source_names.append("demo")

        results = await asyncio.gather(*tasks) if tasks else []
        items = []
        failed: list[str] = []
        used: list[str] = []

        for name, (ok, rows) in zip(source_names, results):
            if ok:
                used.append(name)
                items.extend(rows)
            else:
                failed.append(name)

        filtered = apply_filters(items, filters)
        return SearchResponse(
            items=filtered,
            total=len(filtered),
            demo="demo" in used and not any(s in used for s in ("mrkt", "portals", "tonnel")),
            sources_used=used,
            sources_failed=failed,
            applied_filters=filters,
        )

    async def _safe_fetch(self, source, filters: SearchFilters):
        try:
            rows = await source.fetch(filters)
            return True, rows
        except Exception as exc:
            logger.exception("Source %s failed: %s", source.name, exc)
            return False, []
