import { expect, test } from "@playwright/test";

const username = process.env.E2E_USERNAME ?? "nesrine";
const password = process.env.E2E_PASSWORD;

test.describe("Parcours connecté (Keycloak)", () => {
  test.skip(!password, "E2E_PASSWORD non défini (mot de passe de l'utilisateur de test)");

  test("connexion → 3 figurines → recommandations → déconnexion", async ({ page }) => {
    await page.goto("/boutique");
    await page.getByRole("banner").getByRole("button", { name: "Se connecter" }).click();

    // Keycloak login page (Authorization Code + PKCE)
    // First render of the Keycloak login theme can be slow in dev mode.
    await expect(page).toHaveURL(/\/realms\/petite-maison\/protocol\/openid-connect\/auth/, { timeout: 30_000 });
    expect(new URL(page.url()).searchParams.get("code_challenge_method")).toBe("S256");
    await page.locator("#username").fill(username);
    await page.locator("#password").fill(password!);
    await page.locator("#kc-login").click();

    // Back on the page we started from, signed in
    await expect(page).toHaveURL(/\/boutique/);
    const banner = page.getByRole("banner");
    await expect(banner).toContainText("Bonjour");
    await expect(banner.getByRole("button", { name: "Se déconnecter" })).toBeVisible();

    for (const id of ["fig-orc-evil-ed", "fig-nosferatu", "fig-masque-hockey"]) {
      await page.goto(`/produit/${id}`);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    }

    // Events go through Kafka asynchronously: poll the home page until recommendations show up.
    await expect(async () => {
      await page.goto("/");
      const reco = page.getByRole("list", { name: "Recommandé pour vous" });
      await expect(reco.getByRole("listitem")).toHaveCount(4, { timeout: 2_000 });
    }).toPass({ timeout: 30_000 });

    await page.goto("/produit/fig-nosferatu");
    const related = page.getByRole("region", { name: "Vous aimerez aussi" });
    await expect(related).toContainText("Recommandations personnalisées selon votre navigation");
    await expect(related.getByRole("listitem").first()).toBeVisible();

    await page.getByRole("button", { name: "Se déconnecter" }).click();
    await expect(page).toHaveURL(/localhost:3000\/$/);
    await expect(page.getByRole("banner").getByRole("button", { name: "Se connecter" })).toBeVisible();
  });
});
