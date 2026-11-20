export const CATEGORIES = ["FIGURINE", "BLURAY", "BD", "BOARD_GAME", "GOODIES", "FANZINE"] as const;
export const STORES = ["ANGOULEME", "AIX", "LYON", "LONDRES", "ONLINE"] as const;

export type Category = (typeof CATEGORIES)[number];
export type Store = (typeof STORES)[number];

export interface ProductSummary {
  id: string;
  name: string;
  category: Category;
  universe: string;
  price: number;
  exclusiveEvilEd: boolean;
  imageUrl: string | null;
  stockByStore: Record<Store, number>;
}

export interface ProductDetail extends ProductSummary {
  description: string | null;
}

export interface Page<T> {
  content: T[];
  page: number;
  size: number;
  totalElements: number;
  totalPages: number;
}

export interface CatalogFilters {
  category?: Category;
  q?: string;
  store?: Store;
  page?: number;
}
