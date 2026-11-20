import { type NextRequest, NextResponse } from "next/server";

import { buildCsp } from "@/lib/security-headers";

const SESSION_COOKIE = "pme_sid";
const SESSION_ID = /^[A-Za-z0-9-]{8,64}$/;

/**
 * Runs before every page request:
 *  - per-request CSP nonce,
 *  - anonymous browsing session id (cookie) → X-Session-Id for product-viewed events,
 *  - correlation id, propagated to the backend APIs (and their logs / Kafka headers),
 *  - current path (used for "return to this page" after sign-in).
 */
export function proxy(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const keycloakOrigin = new URL(process.env.KEYCLOAK_ISSUER ?? "http://localhost:8080").origin;
  const csp = buildCsp(nonce, { keycloakOrigin, dev: process.env.NODE_ENV === "development" });

  const existing = request.cookies.get(SESSION_COOKIE)?.value;
  const sessionId = existing && SESSION_ID.test(existing) ? existing : `session-${crypto.randomUUID()}`;

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("content-security-policy", csp);
  requestHeaders.set("x-pme-sid", sessionId);
  requestHeaders.set("x-correlation-id", `web-${crypto.randomUUID()}`);
  requestHeaders.set("x-pathname", request.nextUrl.pathname + request.nextUrl.search);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  if (existing !== sessionId) {
    response.cookies.set(SESSION_COOKIE, sessionId, {
      httpOnly: true,
      sameSite: "lax",
      secure: request.nextUrl.protocol === "https:",
      path: "/",
      maxAge: 60 * 60 * 24 * 30,
    });
  }
  return response;
}

export const config = {
  // Pages only: skip static assets, images, favicon and the Auth.js API.
  matcher: [
    {
      source: "/((?!api/|_next/static|_next/image|favicon.ico|robots.txt).*)",
      missing: [{ type: "header", key: "next-router-prefetch" }],
    },
  ],
};
