"use strict";

async function pull(url, options) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 3000);
  try {
    return await fetch(url, { ...options, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

function pickInt(data, keys) {
  if (!data || typeof data !== "object") return null;
  for (const key of keys) {
    if (data[key] == null) continue;
    const value = Number(data[key]);
    if (Number.isFinite(value)) return Math.trunc(value);
  }
  return null;
}

function asStr(value) {
  if (value == null) return null;
  if (typeof value === "object") return value.name || value.title || null;
  return String(value);
}

function sellerOf(raw) {
  const seller = typeof raw === "string" ? { id: raw } : raw || {};
  return {
    id: String(seller.id || seller.userId || seller.user_id || "unknown"),
    username: asStr(seller.username),
    display_name: asStr(seller.name || seller.displayName || seller.display_name),
    level: pickInt(seller, ["level", "lvl", "accountLevel", "rank"]),
    nft_count: pickInt(seller, [
      "nftCount",
      "giftsCount",
      "itemsCount",
      "listingsCount",
      "inventoryCount",
      "nfts_count",
      "listed_count",
      "items_count",
      "nfts",
      "gifts_count",
    ]),
    sales_count: pickInt(seller, ["salesCount", "soldCount", "totalSales", "sales_count", "sold", "sales"]),
    is_reseller: Boolean(seller.isReseller || seller.is_reseller || seller.isPro || seller.is_pro),
  };
}

function isReseller(seller, maxNfts) {
  if (seller.is_reseller) return true;
  if (seller.nft_count != null && seller.nft_count > maxNfts) return true;
  if (seller.sales_count != null && seller.sales_count >= 10) return true;
  if (seller.level != null && seller.level > 1) return true;
  return false;
}

function noviceScore(seller, filters) {
  const reasons = [];
  let score = 100;
  if (seller.level == null) {
    reasons.push("уровень неизвестен");
    score -= 25;
  } else if (seller.level > filters.maxLevel) {
    return { ok: false, reasons: [`уровень ${seller.level}`], score: 0 };
  } else {
    reasons.push(`уровень ${seller.level}`);
  }
  if (seller.nft_count == null) {
    reasons.push("число NFT неизвестно");
    score -= 20;
  } else if (seller.nft_count > filters.maxNfts) {
    return { ok: false, reasons: [`${seller.nft_count} NFT`], score: 0 };
  } else {
    reasons.push(`${seller.nft_count} NFT`);
  }
  if (filters.excludeResellers && isReseller(seller, filters.maxNfts)) {
    return { ok: false, reasons: ["похоже на перекупа"], score: 0 };
  }
  return { ok: true, reasons, score: Math.max(0, Math.min(100, score)) };
}

function withLinks(item) {
  const username = item.seller && item.seller.username;
  item.profile_url = username
    ? `https://t.me/${String(username).replace(/^@/, "")}`
    : item.url;
  return item;
}

function applyFilters(items, filters) {
  const query = (filters.query || "").toLowerCase();
  const out = [];
  for (const item of items) {
    if (filters.minPrice != null && item.price_ton < filters.minPrice) continue;
    if (filters.maxPrice != null && item.price_ton > filters.maxPrice) continue;
    if (query && !`${item.title} ${item.collection} ${item.model || ""}`.toLowerCase().includes(query)) continue;
    const judged = noviceScore(item.seller, filters);
    if (filters.onlyNovice && !judged.ok) continue;
    item.reasons = judged.reasons;
    item.novice_score = judged.score;
    out.push(item);
  }
  out.sort((a, b) => a.price_ton - b.price_ton || b.novice_score - a.novice_score);
  return out.slice(0, filters.limit);
}

async function fetchMrkt(token, filters) {
  const items = [];
  let cursor = "";
  for (let page = 0; page < 2 && items.length < filters.limit; page += 1) {
    const res = await pull("https://api.tgmrkt.io/api/v1/gifts/saling", {
      method: "POST",
      headers: {
        Authorization: token,
        Referer: "https://cdn.tgmrkt.io/",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        collectionNames: [],
        modelNames: [],
        backdropNames: [],
        symbolNames: [],
        ordering: "Price",
        lowToHigh: true,
        maxPrice: filters.maxPrice,
        minPrice: filters.minPrice,
        mintable: null,
        number: null,
        count: 20,
        cursor,
        query: filters.query || null,
        promotedFirst: false,
      }),
    });
    if (!res.ok) throw new Error(`MRKT ${res.status}`);
    const data = await res.json();
    const gifts = data.gifts || data.items || [];
    if (!gifts.length) break;
    for (const gift of gifts) items.push(mapMrkt(gift));
    cursor = data.cursor || "";
    if (!cursor) break;
  }
  return items.filter(Boolean);
}

function mapMrkt(gift) {
  const raw = Number(gift.price || gift.salePrice || gift.amount || 0);
  let price = raw > 1000 ? raw / 1e9 : raw;
  if (price > 10000) price = raw;
  const collection = asStr(gift.collectionName || gift.collection || gift.name) || "Unknown";
  const number = pickInt(gift, ["number", "num", "externalCollectionNumber"]);
  const item = {
    id: String(gift.id || gift.giftId || gift.slug || `${collection}-${number}`),
    source: "mrkt",
    title: number ? `${collection} #${number}` : collection,
    collection,
    model: asStr(gift.modelName || gift.model),
    backdrop: asStr(gift.backdropName || gift.backdrop),
    symbol: asStr(gift.symbolName || gift.symbol),
    number,
    price_ton: Math.round(price * 10000) / 10000,
    currency: "TON",
    image_url: asStr(gift.photoUrl || gift.image || gift.thumbnail),
    url: asStr(gift.url || gift.link) || `https://t.me/mrkt?startapp=${gift.id || ""}`,
    seller: sellerOf(gift.seller || gift.owner || gift.user),
  };
  return withLinks(item);
}

async function fetchPortals(token, filters) {
  const items = [];
  const headers = { Authorization: token, Accept: "application/json" };
  for (let offset = 0; offset < 100 && items.length < filters.limit; offset += 100) {
    const params = new URLSearchParams({
      offset: String(offset),
      limit: "100",
      sort_by: "price asc",
      status: "listed",
    });
    if (filters.minPrice != null) params.set("min_price", String(filters.minPrice));
    if (filters.maxPrice != null) params.set("max_price", String(filters.maxPrice));
    const res = await pull(`https://portal-market.com/api/nfts/search?${params}`, { headers });
    if (!res.ok) throw new Error(`Portals ${res.status}`);
    const data = await res.json();
    const rows = data.results || data.nfts || [];
    if (!rows.length) break;
    for (const row of rows) items.push(mapPortals(row));
    if (rows.length < 100) break;
  }
  return items.filter(Boolean);
}

function mapPortals(gift) {
  const collectionRaw = gift.collection || gift.name || "Unknown";
  const collection = typeof collectionRaw === "object" ? collectionRaw.name || collectionRaw.title || "Unknown" : String(collectionRaw);
  const number = pickInt(gift, ["external_collection_number", "number"]);
  const item = {
    id: String(gift.id || gift.nft_id || `${collection}-${number}`),
    source: "portals",
    title: number ? `${collection} #${number}` : collection,
    collection,
    model: asStr(gift.model || gift.model_name),
    backdrop: asStr(gift.backdrop || gift.backdrop_name),
    symbol: asStr(gift.symbol || gift.symbol_name),
    number,
    price_ton: Math.round(Number(gift.price || gift.floor_price || 0) * 10000) / 10000,
    currency: "TON",
    image_url: asStr(gift.photo_url || gift.image || gift.animation_url),
    url: asStr(gift.url) || "https://t.me/portals/market",
    seller: sellerOf(gift.owner || gift.seller || gift.user),
  };
  return withLinks(item);
}

async function fetchTonnel(token, filters) {
  const items = [];
  for (let page = 1; page <= 1 && items.length < filters.limit; page += 1) {
    const payload = {
      page,
      limit: 30,
      sort: "price_asc",
      filter: {},
      ref: 0,
      price_range: null,
      authData: token,
    };
    if (filters.query) payload.filter.gift_name = filters.query;
    if (filters.minPrice != null || filters.maxPrice != null) {
      payload.price_range = { min: filters.minPrice, max: filters.maxPrice };
    }
    let res = await pull("https://gifts2.tonnel.network/api/pageGifts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      res = await pull("https://gifts2.tonnel.network/api/gift/list", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }
    if (!res.ok) throw new Error(`Tonnel ${res.status}`);
    const data = await res.json();
    let rows = data.gifts || data.data || data.results || [];
    if (rows && !Array.isArray(rows)) rows = rows.gifts || [];
    if (!rows.length) break;
    for (const row of rows) items.push(mapTonnel(row));
    if (rows.length < 30) break;
  }
  return items.filter(Boolean);
}

function mapTonnel(gift) {
  const name = asStr(gift.name || gift.gift_name || gift.title) || "Gift";
  const number = pickInt(gift, ["gift_num", "number"]);
  const item = {
    id: String(gift.gift_id || gift.id || `${name}-${number}`),
    source: "tonnel",
    title: number ? `${name} #${number}` : name,
    collection: name,
    model: asStr(gift.model),
    backdrop: asStr(gift.backdrop),
    symbol: asStr(gift.symbol),
    number,
    price_ton: Math.round(Number(gift.price || gift.amount || 0) * 10000) / 10000,
    currency: "TON",
    image_url: asStr(gift.customEmoji || gift.photo || gift.image),
    url: asStr(gift.url) || "https://t.me/tonnel_network_bot",
    seller: sellerOf(gift.seller || gift.owner),
  };
  return withLinks(item);
}

async function searchMarkets(tokens, filters) {
  const jobs = [];
  if (tokens.mrkt) jobs.push(["mrkt", fetchMrkt(tokens.mrkt, filters)]);
  if (tokens.portals) jobs.push(["portals", fetchPortals(tokens.portals, filters)]);
  if (tokens.tonnel) jobs.push(["tonnel", fetchTonnel(tokens.tonnel, filters)]);
  const used = [];
  const failed = [];
  const items = [];
  const settled = await Promise.all(
    jobs.map(async ([name, job]) => {
      try {
        return { name, items: await job };
      } catch (err) {
        console.error("search", name, err && err.message ? err.message : err);
        return { name, error: true };
      }
    })
  );
  for (const row of settled) {
    if (row.error) failed.push(row.name);
    else {
      used.push(row.name);
      items.push(...row.items);
    }
  }
  let filtered = applyFilters(items, filters);
  if (!filtered.length && items.length) {
    filtered = items
      .filter((item) => {
        if (filters.minPrice != null && item.price_ton < filters.minPrice) return false;
        if (filters.maxPrice != null && item.price_ton > filters.maxPrice) return false;
        return true;
      })
      .sort((a, b) => a.price_ton - b.price_ton)
      .slice(0, filters.limit);
  }
  return {
    items: filtered,
    total: filtered.length,
    demo: false,
    sources_used: used,
    sources_failed: failed,
  };
}

module.exports = { searchMarkets };
