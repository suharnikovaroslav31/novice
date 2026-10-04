import { useEffect, useState } from "react";
import { searchNfts } from "./api";
import type { NftListing, SearchFilters, SearchResponse, SourceName } from "./types";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        setHeaderColor?: (color: string) => void;
        setBackgroundColor?: (color: string) => void;
        openTelegramLink?: (url: string) => void;
        openLink?: (url: string) => void;
        HapticFeedback?: { impactOccurred: (style: string) => void };
        themeParams?: Record<string, string>;
      };
    };
  }
}

const DEFAULT_FILTERS: SearchFilters = {
  max_seller_level: 1,
  max_seller_nfts: 2,
  max_price_ton: null,
  min_price_ton: null,
  collections: [],
  sources: [],
  only_novice: true,
  exclude_resellers: true,
  query: "",
  limit: 60,
};

const SOURCE_OPTIONS: { id: SourceName; label: string }[] = [
  { id: "mrkt", label: "MRKT" },
  { id: "portals", label: "Portals" },
  { id: "tonnel", label: "Tonnel" },
  { id: "demo", label: "Demo" },
];

export default function App() {
  const [filters, setFilters] = useState<SearchFilters>(DEFAULT_FILTERS);
  const [draftQuery, setDraftQuery] = useState("");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    tg?.ready();
    tg?.expand();
    tg?.setHeaderColor?.("#f3f7f2");
    tg?.setBackgroundColor?.("#f3f7f2");
  }, []);

  useEffect(() => {
    void runSearch(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runSearch(next: SearchFilters) {
    setLoading(true);
    setError(null);
    try {
      const res = await searchNfts(next);
      setData(res);
      window.Telegram?.WebApp?.HapticFeedback?.impactOccurred("light");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить");
    } finally {
      setLoading(false);
    }
  }

  function toggleSource(id: SourceName) {
    setFilters((prev) => {
      const has = prev.sources.includes(id);
      return {
        ...prev,
        sources: has ? prev.sources.filter((s) => s !== id) : [...prev.sources, id],
      };
    });
  }

  function openListing(item: NftListing) {
    const url = item.url || "https://t.me/";
    const tg = window.Telegram?.WebApp;
    if (url.startsWith("https://t.me/") && tg?.openTelegramLink) {
      tg.openTelegramLink(url);
    } else if (tg?.openLink) {
      tg.openLink(url);
    } else {
      window.open(url, "_blank");
    }
  }

  const items = data?.items ?? [];

  return (
    <div className="app">
      <header className="hero">
        <h1 className="brand">
          <span>NOVICE</span>
        </h1>
        <p className="tagline">
          Самые дешёвые Telegram NFT от обычных людей — не от перекупов.
        </p>
        <div className="pill-row">
          <span className="pill lime">ур. ≤ {filters.max_seller_level}</span>
          <span className="pill">≤ {filters.max_seller_nfts} NFT</span>
          <span className="pill">без перекупов</span>
          {data?.demo ? <span className="pill warn">demo-режим</span> : null}
        </div>
      </header>

      <section className="controls">
        <div className="search-row">
          <input
            value={draftQuery}
            onChange={(e) => setDraftQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const next = { ...filters, query: draftQuery };
                setFilters(next);
                void runSearch(next);
              }
            }}
            placeholder="Коллекция, модель, юзер…"
          />
          <button
            className="btn btn-primary"
            onClick={() => {
              const next = { ...filters, query: draftQuery };
              setFilters(next);
              void runSearch(next);
            }}
          >
            Найти
          </button>
        </div>

        <div className="filters-grid">
          <div className="field">
            <label>Макс. уровень</label>
            <input
              type="number"
              min={0}
              max={20}
              value={filters.max_seller_level}
              onChange={(e) =>
                setFilters((p) => ({
                  ...p,
                  max_seller_level: Number(e.target.value) || 0,
                }))
              }
            />
          </div>
          <div className="field">
            <label>Макс. NFT у продавца</label>
            <input
              type="number"
              min={1}
              max={50}
              value={filters.max_seller_nfts}
              onChange={(e) =>
                setFilters((p) => ({
                  ...p,
                  max_seller_nfts: Number(e.target.value) || 1,
                }))
              }
            />
          </div>
          <div className="field">
            <label>Цена до (TON)</label>
            <input
              type="number"
              min={0}
              step="0.1"
              placeholder="без лимита"
              value={filters.max_price_ton ?? ""}
              onChange={(e) =>
                setFilters((p) => ({
                  ...p,
                  max_price_ton: e.target.value === "" ? null : Number(e.target.value),
                }))
              }
            />
          </div>
          <div className="field">
            <label>Цена от (TON)</label>
            <input
              type="number"
              min={0}
              step="0.1"
              placeholder="0"
              value={filters.min_price_ton ?? ""}
              onChange={(e) =>
                setFilters((p) => ({
                  ...p,
                  min_price_ton: e.target.value === "" ? null : Number(e.target.value),
                }))
              }
            />
          </div>
        </div>

        <div className="toggle-row">
          {SOURCE_OPTIONS.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`chip ${filters.sources.includes(s.id) ? "on" : ""}`}
              onClick={() => toggleSource(s.id)}
            >
              {s.label}
            </button>
          ))}
          <button
            type="button"
            className={`chip ${filters.only_novice ? "on" : ""}`}
            onClick={() => setFilters((p) => ({ ...p, only_novice: !p.only_novice }))}
          >
            только новички
          </button>
          <button
            type="button"
            className={`chip ${filters.exclude_resellers ? "on" : ""}`}
            onClick={() =>
              setFilters((p) => ({ ...p, exclude_resellers: !p.exclude_resellers }))
            }
          >
            без перекупов
          </button>
        </div>

        <div className="toggle-row">
          <button className="btn btn-ghost" onClick={() => void runSearch(filters)}>
            Применить фильтры
          </button>
        </div>
      </section>

      <div className="meta">
        <div>
          <strong>{loading ? "…" : items.length}</strong> лотов
        </div>
        <div>
          {data?.sources_used?.length
            ? `источники: ${data.sources_used.join(", ")}`
            : "ожидание…"}
        </div>
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner" />
          Ищем дешёвые лоты у новичков…
        </div>
      ) : null}

      {error ? <div className="error">{error}</div> : null}

      {!loading && !error && items.length === 0 ? (
        <div className="empty">
          Ничего не нашли. Ослабь фильтры или подключи токены маркетов в `.env`.
        </div>
      ) : null}

      <div className="list">
        {items.map((item, index) => (
          <article
            key={`${item.source}-${item.id}`}
            className="card"
            style={{ animationDelay: `${Math.min(index, 12) * 0.03}s` }}
          >
            <div className="thumb">
              {item.image_url ? (
                <img src={item.image_url} alt={item.title} loading="lazy" />
              ) : (
                <div className="thumb-fallback">{item.collection.slice(0, 1)}</div>
              )}
            </div>
            <div className="card-body">
              <div className="card-top">
                <h2 className="title">{item.title}</h2>
                <div className="price">
                  {item.price_ton} {item.currency}
                </div>
              </div>
              <p className="sub">
                {[item.model, item.backdrop, item.symbol].filter(Boolean).join(" · ") ||
                  "без трейтов"}
                {" · "}
                {item.seller.display_name || item.seller.username || "продавец"}
              </p>
              <div className="badges">
                <span className="badge source">{item.source}</span>
                {item.seller.level != null ? (
                  <span className="badge">lvl {item.seller.level}</span>
                ) : null}
                {item.seller.nft_count != null ? (
                  <span className="badge">{item.seller.nft_count} NFT</span>
                ) : null}
                <span className="badge score">score {Math.round(item.novice_score)}</span>
              </div>
              <div className="card-actions">
                <button className="btn btn-primary" onClick={() => openListing(item)}>
                  Открыть
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
