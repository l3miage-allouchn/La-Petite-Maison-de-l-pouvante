import Link from "next/link";

import { CATEGORY_LABELS, STORE_LABELS, catalogHref } from "@/lib/format";
import { CATEGORIES, STORES, type CatalogFilters as Filters } from "@/lib/types";

/** Plain GET form: works without JavaScript and keeps filters in the URL (shareable, back button). */
export function CatalogFilters({ filters }: { filters: Filters }) {
  return (
    <form action="/boutique" method="get" className="filters" aria-labelledby="filters-title">
      <h2 id="filters-title" className="filters__title">
        Filtrer
      </h2>

      <div className="field">
        <label htmlFor="filter-q">Recherche</label>
        <input id="filter-q" name="q" type="search" defaultValue={filters.q ?? ""} maxLength={100} />
      </div>

      <fieldset>
        <legend>Catégories</legend>
        <div className="choice">
          <input type="radio" id="cat-all" name="category" value="" defaultChecked={!filters.category} />
          <label htmlFor="cat-all">Toutes</label>
        </div>
        {CATEGORIES.map((category) => (
          <div className="choice" key={category}>
            <input
              type="radio"
              id={`cat-${category}`}
              name="category"
              value={category}
              defaultChecked={filters.category === category}
            />
            <label htmlFor={`cat-${category}`}>{CATEGORY_LABELS[category]}</label>
          </div>
        ))}
      </fieldset>

      <fieldset>
        <legend>Disponible en magasin</legend>
        <div className="choice">
          <input type="radio" id="store-all" name="store" value="" defaultChecked={!filters.store} />
          <label htmlFor="store-all">Peu importe</label>
        </div>
        {STORES.map((store) => (
          <div className="choice" key={store}>
            <input type="radio" id={`store-${store}`} name="store" value={store} defaultChecked={filters.store === store} />
            <label htmlFor={`store-${store}`}>{STORE_LABELS[store]}</label>
          </div>
        ))}
      </fieldset>

      <button type="submit" className="btn btn--primary btn--block">
        Appliquer les filtres
      </button>
    </form>
  );
}

export function ActiveFilters({ filters }: { filters: Filters }) {
  const chips = [
    filters.category && { label: CATEGORY_LABELS[filters.category], href: catalogHref(filters, { category: undefined, page: 1 }) },
    filters.store && { label: STORE_LABELS[filters.store], href: catalogHref(filters, { store: undefined, page: 1 }) },
    filters.q && { label: `« ${filters.q} »`, href: catalogHref(filters, { q: undefined, page: 1 }) },
  ].filter((chip): chip is { label: string; href: string } => Boolean(chip));

  if (chips.length === 0) return null;
  return (
    <div className="chips">
      <ul aria-label="Filtres actifs">
        {chips.map((chip) => (
          <li key={chip.label}>
            <Link href={chip.href} className="chip">
              {chip.label} <span aria-hidden="true">×</span>
              <span className="sr-only"> (retirer ce filtre)</span>
            </Link>
          </li>
        ))}
      </ul>
      <Link href="/boutique" className="link">
        Tout effacer
      </Link>
    </div>
  );
}

export function Pagination({ filters, totalPages }: { filters: Filters; totalPages: number }) {
  if (totalPages <= 1) return null;
  const current = filters.page ?? 1;
  return (
    <nav aria-label="Pagination" className="pagination">
      <ul>
        {current > 1 && (
          <li>
            <Link href={catalogHref(filters, { page: current - 1 })} rel="prev">
              <span aria-hidden="true">‹</span> Précédente
            </Link>
          </li>
        )}
        {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
          <li key={page}>
            <Link
              href={catalogHref(filters, { page })}
              aria-current={page === current ? "page" : undefined}
              aria-label={`Page ${page}`}
            >
              {page}
            </Link>
          </li>
        ))}
        {current < totalPages && (
          <li>
            <Link href={catalogHref(filters, { page: current + 1 })} rel="next">
              Suivante <span aria-hidden="true">›</span>
            </Link>
          </li>
        )}
      </ul>
    </nav>
  );
}
