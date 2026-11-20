import Link from "next/link";

import { login, logout } from "@/app/actions";
import type { Viewer } from "@/lib/viewer";

export function Header({ viewer, returnTo }: { viewer: Viewer | null; returnTo: string }) {
  return (
    <header className="header">
      <div className="header__inner">
        <Link href="/" className="logo">
          La Petite Maison de l&apos;Épouvante
        </Link>

        <nav aria-label="Navigation principale">
          <ul className="nav">
            <li>
              <Link href="/boutique">Boutique</Link>
            </li>
            <li>
              <Link href="/boutique?category=FIGURINE">Figurines</Link>
            </li>
            <li>
              <Link href="/boutique?category=BLURAY">Films</Link>
            </li>
            <li>
              <Link href="/boutique?category=FANZINE">Fanzine</Link>
            </li>
          </ul>
        </nav>

        <search className="header__search">
          <form action="/boutique" method="get" role="search">
            <label htmlFor="header-q" className="sr-only">
              Rechercher un produit
            </label>
            <input id="header-q" name="q" type="search" placeholder="Rechercher un produit, un film…" maxLength={100} />
            <button type="submit" className="btn btn--ghost">
              Rechercher
            </button>
          </form>
        </search>

        <div className="header__account">
          {viewer ? (
            <>
              <span className="header__hello">
                Bonjour <strong>{viewer.name}</strong>
              </span>
              <form action={logout}>
                <button type="submit" className="btn btn--ghost">
                  Se déconnecter
                </button>
              </form>
            </>
          ) : (
            <form action={login}>
              <input type="hidden" name="returnTo" value={returnTo} />
              <button type="submit" className="btn btn--primary">
                Se connecter
              </button>
            </form>
          )}
        </div>
      </div>
    </header>
  );
}
