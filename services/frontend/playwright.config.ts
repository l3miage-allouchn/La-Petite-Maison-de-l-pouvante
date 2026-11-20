import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests against the running stack (`make dev`, or the Compose stack started in CI).
 * Credentials of the test user come from the environment (never hard-coded):
 *   E2E_USERNAME (default "nesrine") / E2E_PASSWORD (= KC_USER_NESRINE_PASSWORD from .env)
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1, // a single shared local stack (16 GB budget): deterministic runs, no Keycloak/JVM contention
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    locale: "fr-FR",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
