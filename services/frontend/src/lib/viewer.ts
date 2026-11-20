import "server-only";

import { cookies, headers } from "next/headers";
import { getToken } from "next-auth/jwt";

import { auth } from "@/auth";
import { refreshAccessToken } from "@/lib/tokens";

export const SESSION_COOKIE = "pme_sid";
export const SESSION_HEADER = "x-pme-sid";
export const CORRELATION_HEADER = "x-correlation-id";
export const PATHNAME_HEADER = "x-pathname";

export interface Viewer {
  userId: string;
  name: string;
}

export interface RequestContext {
  viewer: Viewer | null;
  /** Server-only. Never rendered nor serialized to client components. */
  accessToken: string | null;
  sessionId: string;
  correlationId: string;
  pathname: string;
}

/** Everything a page needs to call the backend APIs on behalf of the visitor. */
export async function getRequestContext(): Promise<RequestContext> {
  const [session, headerList, cookieStore] = await Promise.all([auth(), headers(), cookies()]);
  const sessionId = cookieStore.get(SESSION_COOKIE)?.value ?? headerList.get(SESSION_HEADER) ?? "anon";
  const correlationId = headerList.get(CORRELATION_HEADER) ?? crypto.randomUUID();
  const pathname = headerList.get(PATHNAME_HEADER) ?? "/";

  if (!session?.user?.id || session.error) {
    return { viewer: null, accessToken: null, sessionId, correlationId, pathname };
  }

  // Read the encrypted session cookie server-side to get the access token (not exposed by session()).
  const secureCookie = (process.env.AUTH_URL ?? "").startsWith("https://");
  let token = await getToken({ req: { headers: headerList }, secret: process.env.AUTH_SECRET, secureCookie });
  if (token?.expiresAt && Date.now() >= (token.expiresAt - 30) * 1000) {
    // Server components cannot rewrite cookies: refresh for this request only.
    token = await refreshAccessToken(token);
  }
  const accessToken = token && !token.error ? (token.accessToken ?? null) : null;
  return {
    viewer: accessToken ? { userId: session.user.id, name: session.user.name ?? "client" } : null,
    accessToken,
    sessionId,
    correlationId,
    pathname,
  };
}

export async function getIdToken(): Promise<string | undefined> {
  const secureCookie = (process.env.AUTH_URL ?? "").startsWith("https://");
  const token = await getToken({ req: { headers: await headers() }, secret: process.env.AUTH_SECRET, secureCookie });
  return token?.idToken;
}
