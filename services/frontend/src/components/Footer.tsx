import Link from "next/link";

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner">
        <p>© La Petite Maison de l&apos;Épouvante · Hébergé en Europe</p>
        <ul className="footer__links">
          <li>
            <Link href="/accessibilite">Accessibilité : partiellement conforme (RGAA)</Link>
          </li>
        </ul>
      </div>
    </footer>
  );
}
