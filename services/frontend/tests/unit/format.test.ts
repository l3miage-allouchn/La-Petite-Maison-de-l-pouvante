import { describe, expect, it } from "vitest";

import { availableStores, catalogHref, formatPrice, parseFilters, universeLabel } from "@/lib/format";
import { buildCsp } from "@/lib/security-headers";

describe("formatPrice", () => {
  it("formats euros the French way", () => {
    expect(formatPrice(49.9).replace(/\s/g, " ")).toBe("49,90 €");
  });
});

describe("parseFilters", () => {
  it("keeps valid filters", () => {
    expect(parseFilters({ category: "FIGURINE", store: "LYON", q: "  orc ", page: "2" })).toEqual({
      category: "FIGURINE",
      store: "LYON",
      q: "orc",
      page: 2,
    });
  });

  it("drops unknown or malicious values", () => {
    expect(parseFilters({ category: "TOASTER", store: "<script>", page: "-3", q: "" })).toEqual({
      category: undefined,
      store: undefined,
      q: undefined,
      page: 1,
    });
  });

  it("truncates long searches and takes the first value of repeated params", () => {
    const filters = parseFilters({ q: ["x".repeat(500), "ignored"] });
    expect(filters.q).toHaveLength(100);
  });
});

describe("catalogHref", () => {
  it("builds URLs and removes filters on override", () => {
    const filters = { category: "BD" as const, q: "orc", page: 3 };
    expect(catalogHref(filters)).toBe("/boutique?category=BD&q=orc&page=3");
    expect(catalogHref(filters, { category: undefined, page: 1 })).toBe("/boutique?q=orc");
    expect(catalogHref({})).toBe("/boutique");
  });
});

describe("helpers", () => {
  it("lists stores with stock and labels universes", () => {
    expect(availableStores({ ANGOULEME: 0, AIX: 2, LYON: 0, LONDRES: 1, ONLINE: 5 })).toEqual(["AIX", "LONDRES", "ONLINE"]);
    expect(universeLabel("heroic-fantasy")).toBe("Heroic fantasy");
  });
});

describe("buildCsp", () => {
  it("uses a nonce, allows the Keycloak form redirect and forbids framing", () => {
    const csp = buildCsp("abc123", { keycloakOrigin: "http://localhost:8080", dev: false });
    expect(csp).toContain("script-src 'self' 'nonce-abc123' 'strict-dynamic'");
    expect(csp).toContain("form-action 'self' http://localhost:8080");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).not.toContain("unsafe-eval");
  });

  it("allows eval only in development (React refresh)", () => {
    expect(buildCsp("n", { keycloakOrigin: "http://k", dev: true })).toContain("'unsafe-eval'");
  });
});
