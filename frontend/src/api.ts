import type { SearchFilters, SearchResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export async function searchNfts(filters: SearchFilters): Promise<SearchResponse> {
  const params = new URLSearchParams();
  params.set("max_seller_level", String(filters.max_seller_level));
  params.set("max_seller_nfts", String(filters.max_seller_nfts));
  params.set("only_novice", String(filters.only_novice));
  params.set("exclude_resellers", String(filters.exclude_resellers));
  params.set("limit", String(filters.limit));

  if (filters.max_price_ton != null) params.set("max_price_ton", String(filters.max_price_ton));
  if (filters.min_price_ton != null) params.set("min_price_ton", String(filters.min_price_ton));
  if (filters.query.trim()) params.set("query", filters.query.trim());
  if (filters.collections.length) params.set("collections", filters.collections.join(","));
  if (filters.sources.length) params.set("sources", filters.sources.join(","));

  const res = await fetch(`${API_BASE}/api/search?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Ошибка поиска: ${res.status}`);
  }
  return res.json();
}
