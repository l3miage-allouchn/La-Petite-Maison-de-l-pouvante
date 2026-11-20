import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, listProducts, productIndex, recommendedProducts, viewProduct } from "@/lib/api";
import type { RequestContext } from "@/lib/viewer";

const product = (id: string) => ({
  id,
  name: id,
  category: "FIGURINE",
  universe: "gothique",
  price: 10,
  exclusiveEvilEd: false,
  imageUrl: null,
  stockByStore: { ANGOULEME: 1, AIX: 0, LYON: 0, LONDRES: 0, ONLINE: 1 },
});

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const anonymous: RequestContext = {
  viewer: null,
  accessToken: null,
  sessionId: "session-test-0001",
  correlationId: "web-corr-0001",
  pathname: "/",
};
const nesrine: RequestContext = { ...anonymous, viewer: { userId: "user-42", name: "nesrine" }, accessToken: "token-abc" };

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

function lastCall(index = -1) {
  const call = fetchMock.mock.calls.at(index)!;
  return { url: String(call[0]), headers: (call[1] as RequestInit).headers as Record<string, string> };
}

describe("catalog client", () => {
  it("passes filters and pagination (1-based in the UI, 0-based in the API)", async () => {
    fetchMock.mockResolvedValue(json({ content: [], page: 1, size: 12, totalElements: 0, totalPages: 0 }));
    await listProducts({ category: "BD", store: "LYON", q: "orc", page: 2 }, anonymous);
    const { url, headers } = lastCall();
    expect(url).toBe("http://localhost:8081/api/catalog/products?page=1&size=12&category=BD&store=LYON&q=orc");
    expect(headers["X-Correlation-Id"]).toBe("web-corr-0001");
    expect(headers.Authorization).toBeUndefined();
  });

  it("sends the session id and the token when viewing a product", async () => {
    fetchMock.mockResolvedValue(json({ ...product("fig-nosferatu"), description: "d" }));
    await viewProduct("fig-nosferatu", nesrine);
    const { url, headers } = lastCall();
    expect(url).toBe("http://localhost:8081/api/catalog/products/fig-nosferatu");
    expect(headers["X-Session-Id"]).toBe("session-test-0001");
    expect(headers.Authorization).toBe("Bearer token-abc");
  });

  it("raises ApiError with the HTTP status", async () => {
    fetchMock.mockResolvedValue(json({ title: "Product not found" }, 404));
    await expect(viewProduct("ghost", anonymous)).rejects.toEqual(expect.any(ApiError));
    await expect(viewProduct("ghost", anonymous)).rejects.toMatchObject({ status: 404 });
  });

  it("indexes every page of the catalog", async () => {
    fetchMock
      .mockResolvedValueOnce(json({ content: [product("a1")], page: 0, size: 50, totalElements: 2, totalPages: 2 }))
      .mockResolvedValueOnce(json({ content: [product("b2")], page: 1, size: 50, totalElements: 2, totalPages: 2 }));
    const index = await productIndex(anonymous);
    expect([...index.keys()]).toEqual(["a1", "b2"]);
  });
});

describe("recommendations", () => {
  const catalogPage = json({ content: ["a1", "b2", "c3"].map(product), page: 0, size: 50, totalElements: 3, totalPages: 1 });

  it("uses personalised recommendations for a signed-in user", async () => {
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(url.includes("/api/reco/") ? json({ items: ["c3", "unknown", "a1"], model: "m" }) : catalogPage.clone()),
    );
    const items = await recommendedProducts(nesrine, { similarTo: "a1", limit: 4 });
    const recoCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/api/reco/"))!;
    expect(String(recoCall[0])).toBe("http://localhost:8082/api/reco/recommendations/user-42?limit=5");
    expect((recoCall[1] as RequestInit).headers).toMatchObject({ Authorization: "Bearer token-abc" });
    // unknown ids and the current product are filtered out
    expect(items.map((p) => p.id)).toEqual(["c3"]);
  });

  it("uses similar products for an anonymous visitor", async () => {
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(url.includes("/api/reco/") ? json({ items: ["b2"], model: "m" }) : catalogPage.clone()),
    );
    const items = await recommendedProducts(anonymous, { similarTo: "a1" });
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/api/reco/products/a1/similar?limit=4"))).toBe(true);
    expect(items.map((p) => p.id)).toEqual(["b2"]);
  });

  it("never breaks the page when the reco service is down", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    fetchMock.mockRejectedValue(new TypeError("fetch failed"));
    await expect(recommendedProducts(nesrine, {})).resolves.toEqual([]);
  });

  it("returns nothing for an anonymous visitor outside a product page", async () => {
    await expect(recommendedProducts(anonymous, {})).resolves.toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
