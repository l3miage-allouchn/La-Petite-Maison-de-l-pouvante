import type { Metadata } from "next";

export const metadata: Metadata = { title: "Déclaration d'accessibilité" };

export default function AccessibilityPage() {
  return (
    <div className="container prose">
      <h1>Déclaration d&apos;accessibilité</h1>
      <p>
        La Petite Maison de l&apos;Épouvante s&apos;engage à rendre son site accessible conformément au référentiel
        général d&apos;amélioration de l&apos;accessibilité (RGAA 4.1).
      </p>
      <h2>État de conformité</h2>
      <p>
        Le site est <strong>partiellement conforme</strong> au RGAA 4.1 : il s&apos;agit d&apos;un prototype
        (projet d&apos;école). Aucun audit complet n&apos;a été réalisé ; des tests automatisés (axe-core) sont exécutés à
        chaque intégration continue sur les pages d&apos;accueil, de boutique et de produit.
      </p>
      <h2>Mesures mises en œuvre</h2>
      <ul>
        <li>Langue de la page déclarée, structure de titres hiérarchisée, régions (en-tête, navigation, contenu, pied).</li>
        <li>Lien d&apos;évitement « Aller au contenu », navigation complète au clavier, focus toujours visible.</li>
        <li>Contrastes conformes au niveau AA, textes alternatifs pour les visuels, champs de formulaire étiquetés.</li>
        <li>Filtres du catalogue utilisables sans JavaScript ; nombre de résultats annoncé aux lecteurs d&apos;écran.</li>
      </ul>
      <h2>Contenus non accessibles</h2>
      <p>Les visuels produits sont des illustrations de remplacement en attendant les photographies.</p>
    </div>
  );
}
