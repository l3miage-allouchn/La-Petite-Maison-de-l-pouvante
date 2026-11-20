import Link from "next/link";

import { ProductVisual } from "@/components/ProductVisual";
import { CATEGORY_BADGES, formatPrice } from "@/lib/format";
import type { ProductSummary } from "@/lib/types";

export function ProductCard({ product, headingLevel = 3 }: { product: ProductSummary; headingLevel?: 2 | 3 }) {
  const Heading = `h${headingLevel}` as const;
  return (
    <article className="card">
      <ProductVisual name={product.name} category={product.category} />
      <div className="card__body">
        <p className="badge">{product.exclusiveEvilEd ? "Exclusivité Evil Ed" : CATEGORY_BADGES[product.category]}</p>
        <Heading className="card__title">
          {/* The whole card is clickable through this link (stretched with CSS), one tab stop per card. */}
          <Link href={`/produit/${product.id}`} className="card__link">
            {product.name}
          </Link>
        </Heading>
        <p className="card__price">{formatPrice(product.price)}</p>
      </div>
    </article>
  );
}

export function ProductGrid({ products, label }: { products: ProductSummary[]; label: string }) {
  return (
    <ul className="grid" aria-label={label}>
      {products.map((product) => (
        <li key={product.id}>
          <ProductCard product={product} />
        </li>
      ))}
    </ul>
  );
}
