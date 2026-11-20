import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ProductGrid } from "@/components/ProductCard";
import { ProductVisual } from "@/components/ProductVisual";
import { ApiError, recommendedProducts, viewProduct } from "@/lib/api";
import { CATEGORY_LABELS, STORE_LABELS, availableStores, catalogHref, formatPrice, universeLabel } from "@/lib/format";
import { getRequestContext } from "@/lib/viewer";

const PRODUCT_ID = /^[a-z0-9][a-z0-9-]{0,63}$/;

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  return { title: id.replace(/-/g, " ") };
}

export default async function ProductPage({ params }: Props) {
  const { id } = await params;
  if (!PRODUCT_ID.test(id)) notFound();

  const ctx = await getRequestContext();
  let product;
  try {
    product = await viewProduct(id, ctx); // records a product-viewed event
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 400)) notFound();
    throw error;
  }
  const related = await recommendedProducts(ctx, { similarTo: product.id, limit: 4 });
  const stores = availableStores(product.stockByStore);
  const physicalStores = stores.filter((s) => s !== "ONLINE");

  return (
    <div className="container">
      <nav aria-label="Fil d'Ariane" className="breadcrumb">
        <ol>
          <li>
            <Link href="/">Accueil</Link>
          </li>
          <li>
            <Link href="/boutique">Boutique</Link>
          </li>
          <li>
            <Link href={catalogHref({ category: product.category })}>{CATEGORY_LABELS[product.category]}</Link>
          </li>
          <li aria-current="page">{product.name}</li>
        </ol>
      </nav>

      <article className="product">
        <ProductVisual name={product.name} category={product.category} size="large" />
        <div className="product__info">
          {product.exclusiveEvilEd && <p className="eyebrow">Exclusivité Evil Ed</p>}
          <h1>{product.name}</h1>
          <p className="product__price">{formatPrice(product.price)}</p>

          <p className={`stock ${stores.length ? "stock--ok" : "stock--out"}`}>
            <span aria-hidden="true">●</span>{" "}
            {stores.length === 0
              ? "Rupture de stock"
              : `${stores.includes("ONLINE") ? "En stock en ligne" : "Indisponible en ligne"}${
                  physicalStores.length
                    ? ` · Disponible en magasin à ${physicalStores.map((s) => STORE_LABELS[s]).join(", ")}`
                    : ""
                }`}
          </p>

          <h2 className="h3">Description</h2>
          <p className="muted">{product.description}</p>

          <h2 className="h3">Caractéristiques</h2>
          <dl className="specs">
            <dt>Catégorie</dt>
            <dd>{CATEGORY_LABELS[product.category]}</dd>
            <dt>Univers</dt>
            <dd>{universeLabel(product.universe)}</dd>
            <dt>Stock par magasin</dt>
            <dd>
              <ul className="stock-list">
                {Object.entries(product.stockByStore).map(([store, qty]) => (
                  <li key={store}>
                    {STORE_LABELS[store as keyof typeof STORE_LABELS]} : {qty}
                  </li>
                ))}
              </ul>
            </dd>
          </dl>
        </div>
      </article>

      <section className="section" aria-labelledby="related-title">
        <div className="section__head">
          <div>
            <h2 id="related-title">Vous aimerez aussi</h2>
            <p className="muted small">
              {ctx.viewer
                ? "Recommandations personnalisées selon votre navigation"
                : "Les visiteurs qui ont consulté ce produit ont aussi aimé"}
            </p>
          </div>
        </div>
        {related.length > 0 ? (
          <ProductGrid products={related} label="Vous aimerez aussi" />
        ) : (
          <p className="muted">Pas encore de suggestion pour ce produit.</p>
        )}
      </section>
    </div>
  );
}
