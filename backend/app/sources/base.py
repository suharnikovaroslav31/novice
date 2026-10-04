from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import NftListing, SearchFilters


class SourceAdapter(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, filters: SearchFilters) -> list[NftListing]:
        raise NotImplementedError
