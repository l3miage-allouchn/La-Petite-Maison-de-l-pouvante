import Link from "next/link";

export default function NotFound() {
  return (
    <div className="container prose">
      <h1>Page introuvable</h1>
      <p>Ce produit ou cette page n&apos;existe pas (ou s&apos;est volatilisé dans la brume).</p>
      <p>
        <Link href="/boutique" className="btn btn--primary">
          Retour à la boutique
        </Link>
      </p>
    </div>
  );
}
