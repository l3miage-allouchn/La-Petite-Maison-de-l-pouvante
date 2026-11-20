import { expect, test } from "@playwright/test";

test.describe("Visiteur non connecté", () => {
  test("accueil → boutique filtrée → fiche produit avec « Vous aimerez aussi »", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "Le lieu de rêve pour frissonner" })).toBeVisible();
    await expect(page.getByRole("list", { name: "Nouveautés" }).getByRole("listitem")).toHaveCount(4);

    await page.getByRole("link", { name: "Découvrir la boutique" }).click();
    await expect(page).toHaveURL(/\/boutique$/);

    const filters = page.getByRole("form", { name: "Filtrer" });
    await filters.getByLabel("Figurines").check();
    await filters.getByLabel("Lyon").check();
    await filters.getByRole("button", { name: "Appliquer les filtres" }).click();

    await expect(page).toHaveURL(/category=FIGURINE/);
    await expect(page.getByRole("status")).toContainText("produits");
    await expect(page.getByRole("list", { name: "Filtres actifs" })).toContainText("Lyon");

    await page.getByRole("list", { name: "Produits" }).getByRole("link").first().click();
    await expect(page).toHaveURL(/\/produit\/fig-/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByText(/Disponible en magasin à .*Lyon/)).toBeVisible();

    const related = page.getByRole("region", { name: "Vous aimerez aussi" });
    await expect(related.getByRole("listitem").first()).toBeVisible();
  });

  test("recherche depuis l'en-tête", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("searchbox", { name: "Rechercher un produit" }).fill("orc");
    await page.getByRole("searchbox", { name: "Rechercher un produit" }).press("Enter");
    await expect(page.getByRole("status")).toContainText("résultats pour « orc »");
  });

  test("navigation au clavier : lien d'évitement puis contenu", async ({ page }) => {
    await page.goto("/boutique");
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Aller au contenu" });
    await expect(skip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("main#contenu")).toBeFocused();
  });

  test("produit inconnu : page 404", async ({ page }) => {
    const response = await page.goto("/produit/n-existe-pas");
    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });

  test("en-têtes de sécurité présents", async ({ page }) => {
    const response = await page.goto("/");
    const headers = response!.headers();
    expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
    expect(headers["strict-transport-security"]).toContain("max-age=");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
    expect(headers["x-powered-by"]).toBeUndefined();
  });
});
