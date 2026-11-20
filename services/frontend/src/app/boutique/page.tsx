import type { Metadata } from "next";
import Link from "next/link";

import { ActiveFilters, CatalogFilters, Pagination } from "@/components/CatalogFilters";
import { ProductGrid } from "@/components/ProductCard";
import { listProducts } from "@/lib/api";
import { CATEGORY_LABELS, parseFilters } from "@/lib/format";
import { getRequestContext } from "@/lib/viewer";

export const metadata: Metadata = { title: "Boutique" };

export default async function CatalogPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const filters = parseFilters(await searchParams);
  const ctx = await getRequestContext();
  const result = await listProducts(filters, ctx);

  const count = `${result.totalElements} produit${result.totalElements > 1 ? "s" : ""}`;
  const summary = filters.q ? `${count} · résultats pour « ${filters.q} »` : count;

  return (
    <div className="container">
      <nav aria-label="Fil d'Ariane" className="breadcrumb">
        <ol>
          <li>
            <Link href="/">Accueil</Link>
          </li>
          <li aria-current="page">Boutique</li>
        </ol>
      </nav>

      <div className="page-head">
        <h1>{filters.category ? CATEGORY_LABELS[filters.category] : "Boutique"}</h1>
        {/* Announced to screen readers when the results change */}
        <p className="muted" role="status">
          {summary}
        </p>
      </div>

      <div className="catalog">
        <aside className="catalog__filters">
          <CatalogFilters filters={filters} />
        </aside>
        <section className="catalog__results" aria-label="Résultats">
          <ActiveFilters filters={filters} />
          {result.content.length > 0 ? (
            <ProductGrid products={result.content} label="Produits" />
          ) : (
            <p className="panel">Aucun produit ne correspond à ces critères.</p>
          )}
          <Pagination filters={filters} totalPages={result.totalPages} />
        </section>
      </div>
    </div>
  );
}
