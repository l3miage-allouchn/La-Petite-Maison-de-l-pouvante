"use client";

import Link from "next/link";

/** Shown when a backend is unavailable. No technical detail is displayed to visitors. */
export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="container prose">
      <h1>Un frisson inattendu…</h1>
      <p role="alert">Le service est momentanément indisponible. Merci de réessayer dans quelques instants.</p>
      <p className="hero__actions">
        <button type="button" className="btn btn--primary" onClick={() => reset()}>
          Réessayer
        </button>
        <Link href="/" className="btn btn--ghost">
          Accueil
        </Link>
      </p>
    </div>
  );
}
