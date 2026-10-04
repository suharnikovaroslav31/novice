export type SourceName = "mrkt" | "portals" | "tonnel" | "demo";

export interface SellerProfile {
  id: string;
  username?: string | null;
  display_name?: string | null;
  level?: number | null;
  nft_count?: number | null;
  sales_count?: number | null;
  is_reseller: boolean;
}

export interface NftListing {
  id: string;
  source: SourceName;
  title: string;
  collection: string;
  model?: string | null;
  backdrop?: string | null;
  symbol?: string | null;
  number?: number | null;
  price_ton: number;
  currency: string;
  image_url?: string | null;
  url?: string | null;
  seller: SellerProfile;
  listed_at?: string | null;
  novice_score: number;
  reasons: string[];
}

export interface SearchFilters {
  max_seller_level: number;
  max_seller_nfts: number;
  max_price_ton: number | null;
  min_price_ton: number | null;
  collections: string[];
  sources: SourceName[];
  only_novice: boolean;
  exclude_resellers: boolean;
  query: string;
  limit: number;
}

export interface SearchResponse {
  items: NftListing[];
  total: number;
  demo: boolean;
  sources_used: string[];
  sources_failed: string[];
  applied_filters: SearchFilters;
}
