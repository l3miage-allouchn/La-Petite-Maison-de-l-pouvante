import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/** RGAA proxy: axe-core WCAG 2.1 A/AA rules. Zero "serious" or "critical" violation allowed. */
const PAGES = [
  { name: "accueil", path: "/" },
  { name: "boutique", path: "/boutique" },
  { name: "boutique filtrée", path: "/boutique?category=FIGURINE&store=LYON&q=figurine" },
  { name: "fiche produit", path: "/produit/fig-nosferatu" },
  { name: "déclaration d'accessibilité", path: "/accessibilite" },
  { name: "page 404", path: "/produit/n-existe-pas" },
];

for (const { name, path } of PAGES) {
  test(`axe : ${name}`, async ({ page }, testInfo) => {
    await page.goto(path);
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();

    await testInfo.attach(`axe-${name}.json`, { body: JSON.stringify(results.violations, null, 2), contentType: "application/json" });
    const blocking = results.violations
      .filter((v) => v.impact === "serious" || v.impact === "critical")
      .map((v) => `${v.impact} ${v.id}: ${v.help} (${v.nodes.length} élément(s))`);
    expect(blocking, blocking.join("\n")).toEqual([]);
  });
}
