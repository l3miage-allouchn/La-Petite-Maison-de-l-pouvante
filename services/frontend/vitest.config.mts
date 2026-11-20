import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      // "server-only" throws outside a React Server Component bundle: neutralise it in unit tests.
      "server-only": path.resolve(__dirname, "tests/unit/empty.ts"),
    },
  },
  test: {
    environment: "jsdom",
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    setupFiles: ["tests/unit/setup.ts"],
    coverage: {
      provider: "v8",
      include: ["src/lib/**", "src/components/**"],
      exclude: ["src/lib/viewer.ts", "src/lib/tokens.ts", "src/lib/config.ts"],
      reporter: ["text", "lcov"],
      thresholds: { lines: 70 },
    },
  },
});
