from __future__ import annotations

import random
from datetime import datetime, timezone
from urllib.parse import quote

from ..models import NftListing, SearchFilters, SellerProfile, SourceName
from .base import SourceAdapter

# Реальные превью Telegram Gifts + локальный SVG-фолбэк через data URI на клиенте
COLLECTIONS = [
    ("Desk Calendar", "📅", "#9BE7C8", "#FFE1D2"),
    ("Lol Pop", "🍭", "#FFB4C8", "#D8FF3F"),
    ("Homemade Cake", "🎂", "#FFD9A8", "#C9F7B4"),
    ("Spiced Wine", "🍷", "#E8B0C8", "#B8FFE4"),
    ("Eternal Rose", "🌹", "#FFB3A8", "#F7E8B0"),
    ("Delicious Cake", "🧁", "#FFD0E0", "#C8F0FF"),
    ("Green Star", "⭐", "#D8FF3F", "#9BE7C8"),
    ("Crystal Ball", "🔮", "#C8D8FF", "#E8C8FF"),
]

MODELS = ["Default", "Gold", "Neon", "Midnight", "Pearl"]
BACKDROPS = ["Black", "Ivory", "Sky", "Burgundy", "Mint"]
SYMBOLS = ["Star", "Heart", "Gem", "Fire", None]


def _gift_svg(name: str, emoji: str, c1: str, c2: str) -> str:
    safe = name.replace("&", "and")
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='512' height='512' viewBox='0 0 512 512'>
  <defs>
    <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
      <stop offset='0%' stop-color='{c1}'/>
      <stop offset='100%' stop-color='{c2}'/>
    </linearGradient>
  </defs>
  <rect width='512' height='512' rx='96' fill='url(#g)'/>
  <circle cx='160' cy='140' r='70' fill='rgba(255,255,255,.35)'/>
  <text x='256' y='275' text-anchor='middle' font-size='160'>{emoji}</text>
  <text x='256' y='390' text-anchor='middle' font-family='Arial,sans-serif' font-size='28' font-weight='700' fill='#101812'>{safe}</text>
</svg>"""
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


class DemoSource(SourceAdapter):
    name = "demo"

    def is_configured(self) -> bool:
        return True

    async def fetch(self, filters: SearchFilters) -> list[NftListing]:
        rng = random.Random(42)
        items: list[NftListing] = []

        for i in range(28):
            col, emoji, c1, c2 = COLLECTIONS[i % len(COLLECTIONS)]
            level = 1
            nft_count = rng.choice([1, 1, 1, 2])
            price = round(rng.uniform(0.8, 12.5), 2)
            model = MODELS[i % len(MODELS)]
            # SVG всегда рисуется; remote URL пробуем как основной, SVG как запасной путь через frontend onerror
            # Но remote часто блокируется — поэтому сразу отдаём SVG, чтобы картинки точно были.
            image = _gift_svg(col, emoji, c1, c2)
            items.append(
                NftListing(
                    id=f"demo-novice-{i}",
                    source=SourceName.DEMO,
                    title=f"{col} #{1000 + i}",
                    collection=col,
                    model=model,
                    backdrop=BACKDROPS[i % len(BACKDROPS)],
                    symbol=SYMBOLS[i % len(SYMBOLS)],
                    number=1000 + i,
                    price_ton=price,
                    image_url=image,
                    url=f"https://t.me/mrkt?startapp=demo_{i}",
                    seller=SellerProfile(
                        id=f"u-novice-{i}",
                        username=f"newbie_{i}",
                        display_name=f"Новичок {i + 1}",
                        level=level,
                        nft_count=nft_count,
                        sales_count=rng.choice([0, 0, 1, 2]),
                        is_reseller=False,
                    ),
                    listed_at=datetime.now(timezone.utc).isoformat(),
                )
            )

        for i in range(12):
            col, emoji, c1, c2 = COLLECTIONS[i % len(COLLECTIONS)]
            items.append(
                NftListing(
                    id=f"demo-flip-{i}",
                    source=SourceName.DEMO,
                    title=f"{col} #{5000 + i}",
                    collection=col,
                    model="Gold",
                    backdrop="Black",
                    number=5000 + i,
                    price_ton=round(rng.uniform(1.2, 8.0), 2),
                    image_url=_gift_svg(col, emoji, c1, c2),
                    url=f"https://t.me/mrkt?startapp=flip_{i}",
                    seller=SellerProfile(
                        id=f"u-flip-{i}",
                        username=f"flipper_{i}",
                        display_name=f"Перекуп {i + 1}",
                        level=rng.choice([2, 3, 5]),
                        nft_count=rng.randint(8, 40),
                        sales_count=rng.randint(15, 200),
                        is_reseller=True,
                    ),
                    listed_at=datetime.now(timezone.utc).isoformat(),
                )
            )

        return items
