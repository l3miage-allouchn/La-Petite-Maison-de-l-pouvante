import "server-only";

import { config } from "@/lib/config";
import type { CatalogFilters, Page, ProductDetail, ProductSummary } from "@/lib/types";
import type { RequestContext } from "@/lib/viewer";

/** Server-side API client. Browsers never call the backends directly. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

type Ctx = Pick<RequestContext, "correlationId"> & Partial<Pick<RequestContext, "accessToken" | "sessionId">>;

async function getJson<T>(url: string, ctx: Ctx, init: { auth?: boolean; session?: boolean; timeoutMs?: number } = {}) {
  const headers: Record<string, string> = { Accept: "application/json", "X-Correlation-Id": ctx.correlationId };
  if (init.auth && ctx.accessToken) headers.Authorization = `Bearer ${ctx.accessToken}`;
  if (init.session && ctx.sessionId) headers["X-Session-Id"] = ctx.sessionId;
  const response = await fetch(url, {
    headers,
    cache: "no-store",
    signal: AbortSignal.timeout(init.timeoutMs ?? 5000), // absorbs a cold JVM on first call
  });
  if (!response.ok) throw new ApiError(response.status, `${response.status} on ${new URL(url).pathname}`);
  return (await response.json()) as T;
}

export const PAGE_SIZE = 12;

export function listProducts(filters: CatalogFilters, ctx: Ctx, size = PAGE_SIZE): Promise<Page<ProductSummary>> {
  const params = new URLSearchParams({ page: String((filters.page ?? 1) - 1), size: String(size) });
  if (filters.category) params.set("category", filters.category);
  if (filters.store) params.set("store", filters.store);
  if (filters.q) params.set("q", filters.q);
  return getJson(`${config.catalogApiUrl}/api/catalog/products?${params}`, ctx);
}

/** Detail page: the catalog publishes a product-viewed event (user from JWT, else session id). */
export function viewProduct(id: string, ctx: Ctx): Promise<ProductDetail> {
  return getJson(`${config.catalogApiUrl}/api/catalog/products/${encodeURIComponent(id)}`, ctx, {
    auth: true,
    session: true,
  });
}

/**
 * Summaries indexed by id, used to display recommended product ids.
 * Uses the list endpoint on purpose: the detail endpoint would record fake "views".
 */
export async function productIndex(ctx: Ctx): Promise<Map<string, ProductSummary>> {
  const index = new Map<string, ProductSummary>();
  let page = 1;
  let totalPages = 1;
  do {
    const result = await listProducts({ page }, ctx, 50);
    result.content.forEach((p) => index.set(p.id, p));
    totalPages = result.totalPages;
    page += 1;
  } while (page <= totalPages && page <= 20);
  return index;
}

interface RecoResponse {
  items: string[];
  model: string;
}

/** Recommendations never break a page: on error, the block is simply empty. */
export async function recommendedProducts(
  ctx: RequestContext,
  opts: { similarTo?: string; limit?: number } = {},
): Promise<ProductSummary[]> {
  const limit = opts.limit ?? 4;
  try {
    const url = ctx.viewer
      ? `${config.recoApiUrl}/api/reco/recommendations/${encodeURIComponent(ctx.viewer.userId)}?limit=${limit + 1}`
      : opts.similarTo
        ? `${config.recoApiUrl}/api/reco/products/${encodeURIComponent(opts.similarTo)}/similar?limit=${limit}`
        : null;
    if (!url) return [];
    const [reco, index] = await Promise.all([
      getJson<RecoResponse>(url, ctx, { auth: true, timeoutMs: 1500 }),
      productIndex(ctx),
    ]);
    return reco.items
      .filter((id) => id !== opts.similarTo)
      .map((id) => index.get(id))
      .filter((p): p is ProductSummary => p !== undefined)
      .slice(0, limit);
  } catch (error) {
    console.warn(
      JSON.stringify({ level: "WARN", message: "recommendations unavailable", error: String(error), correlation_id: ctx.correlationId }),
    );
    return [];
  }
}
