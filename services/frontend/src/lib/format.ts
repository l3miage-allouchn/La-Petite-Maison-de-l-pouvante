import { CATEGORIES, STORES, type CatalogFilters, type Category, type Store } from "@/lib/types";

const priceFormatter = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });

export function formatPrice(value: number): string {
  // Intl uses a narrow no-break space before "€"; keep it (correct French typography).
  return priceFormatter.format(value);
}

export const CATEGORY_LABELS: Record<Category, string> = {
  FIGURINE: "Figurines",
  BLURAY: "Films Blu-ray",
  BD: "Bandes dessinées",
  BOARD_GAME: "Jeux de société",
  GOODIES: "Goodies",
  FANZINE: "Fanzine",
};

export const CATEGORY_BADGES: Record<Category, string> = {
  FIGURINE: "Figurine",
  BLURAY: "Blu-ray",
  BD: "BD",
  BOARD_GAME: "Jeu de société",
  GOODIES: "Goodies",
  FANZINE: "Fanzine",
};

export const STORE_LABELS: Record<Store, string> = {
  ANGOULEME: "Angoulême",
  AIX: "Aix-en-Provence",
  LYON: "Lyon",
  LONDRES: "Londres",
  ONLINE: "En ligne",
};

export function universeLabel(universe: string): string {
  const label = universe.replace(/-/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

/** Parses untrusted search params into valid filters (unknown values are dropped). */
export function parseFilters(params: Record<string, string | string[] | undefined>): CatalogFilters {
  const first = (key: string) => {
    const value = params[key];
    return Array.isArray(value) ? value[0] : value;
  };
  const category = first("category");
  const store = first("store");
  const q = first("q")?.trim().slice(0, 100);
  const page = Number.parseInt(first("page") ?? "1", 10);
  return {
    category: CATEGORIES.includes(category as Category) ? (category as Category) : undefined,
    store: STORES.includes(store as Store) ? (store as Store) : undefined,
    q: q || undefined,
    page: Number.isFinite(page) && page >= 1 && page <= 1000 ? page : 1,
  };
}

/** Builds a /boutique URL, optionally overriding some filters (undefined removes a filter). */
export function catalogHref(filters: CatalogFilters, overrides: Partial<CatalogFilters> = {}): string {
  const merged = { ...filters, ...overrides };
  const params = new URLSearchParams();
  if (merged.category) params.set("category", merged.category);
  if (merged.store) params.set("store", merged.store);
  if (merged.q) params.set("q", merged.q);
  if (merged.page && merged.page > 1) params.set("page", String(merged.page));
  const query = params.toString();
  return query ? `/boutique?${query}` : "/boutique";
}

export function availableStores(stock: Record<Store, number>): Store[] {
  return STORES.filter((store) => (stock[store] ?? 0) > 0);
}
