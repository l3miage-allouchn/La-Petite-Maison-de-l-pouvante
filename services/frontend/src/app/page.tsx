import Link from "next/link";

import { login } from "@/app/actions";
import { ProductGrid } from "@/components/ProductCard";
import { ProductVisual } from "@/components/ProductVisual";
import { listProducts, recommendedProducts } from "@/lib/api";
import type { ProductSummary } from "@/lib/types";
import { getRequestContext } from "@/lib/viewer";

export default async function HomePage() {
  const ctx = await getRequestContext();
  const [catalog, recommendations] = await Promise.all([
    // The home page stays usable when the catalog is slow or down: the block shows a message instead.
    listProducts({}, ctx, 50).then(
      (page) => page.content,
      (error: unknown) => {
        console.warn(JSON.stringify({ msg: "catalog unavailable on home page", error: String(error), correlationId: ctx.correlationId }));
        return null;
      },
    ),
    ctx.viewer ? recommendedProducts(ctx, { limit: 4 }) : Promise.resolve([]),
  ]);
  // "Nouveautés": Evil Ed exclusives first, then the rest of the catalog.
  const highlights: ProductSummary[] | null = catalog && [...catalog].sort((a, b) => Number(b.exclusiveEvilEd) - Number(a.exclusiveEvilEd)).slice(0, 4);

  return (
    <div className="container">
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero__text">
          <p className="eyebrow">Nouveau · Exclusivité Evil Ed</p>
          <h1 id="hero-title">Le lieu de rêve pour frissonner</h1>
          <p className="muted">
            Figurines, films, BD et jeux de société horrifiques — et la figurine de L&apos;Orc, disponible uniquement en
            ligne.
          </p>
          <div className="hero__actions">
            <Link href="/boutique" className="btn btn--primary">
              Découvrir la boutique
            </Link>
            <Link href="/boutique?category=FANZINE" className="btn btn--ghost">
              Le fanzine
            </Link>
          </div>
        </div>
        <ProductVisual name="Figurine L'Orc — édition collector" category="FIGURINE" size="large" />
      </section>

      <section className="section" aria-labelledby="new-title">
        <div className="section__head">
          <h2 id="new-title">Nouveautés</h2>
          <Link href="/boutique" className="link">
            Tout voir <span aria-hidden="true">→</span>
          </Link>
        </div>
        {highlights ? (
          <ProductGrid products={highlights} label="Nouveautés" />
        ) : (
          <p className="muted" role="status">
            Le catalogue est momentanément indisponible. Merci de réessayer dans quelques instants.
          </p>
        )}
      </section>

      <section className="section" aria-labelledby="reco-title">
        <div className="section__head">
          <div>
            <h2 id="reco-title">Recommandé pour vous</h2>
            <p className="muted small">Basé sur vos consultations</p>
          </div>
        </div>
        {ctx.viewer ? (
          recommendations.length > 0 ? (
            <ProductGrid products={recommendations} label="Recommandé pour vous" />
          ) : (
            <p className="muted">Les recommandations sont momentanément indisponibles.</p>
          )
        ) : (
          <div className="panel">
            <p>Connectez-vous pour recevoir des recommandations personnalisées selon votre navigation.</p>
            <form action={login}>
              <input type="hidden" name="returnTo" value="/" />
              <button type="submit" className="btn btn--primary">
                Se connecter
              </button>
            </form>
          </div>
        )}
      </section>

      <section className="banner" aria-labelledby="festival-title">
        <div>
          <h2 id="festival-title">Petit Festival de l&apos;Épouvante — 6e édition</h2>
          <p className="muted">Projections, masterclasses, tournois de jeux de plateau · Billetterie bientôt en ligne</p>
        </div>
      </section>
    </div>
  );
}
