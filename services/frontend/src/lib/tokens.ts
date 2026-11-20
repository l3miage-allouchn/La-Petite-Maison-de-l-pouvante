import "server-only";

import type { JWT } from "next-auth/jwt";

import { config } from "@/lib/config";

/** Refresh-token grant against the internal Keycloak URL. Never throws: marks the token instead. */
export async function refreshAccessToken(token: JWT): Promise<JWT> {
  if (!token.refreshToken) return { ...token, error: "RefreshTokenError" };
  try {
    const response = await fetch(`${config.keycloakInternalIssuer}/protocol/openid-connect/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: token.refreshToken,
        client_id: config.keycloakClientId,
        client_secret: config.keycloakClientSecret,
      }),
      cache: "no-store",
    });
    const body = (await response.json()) as {
      access_token?: string;
      refresh_token?: string;
      id_token?: string;
      expires_in?: number;
    };
    if (!response.ok || !body.access_token) return { ...token, error: "RefreshTokenError" };
    return {
      ...token,
      accessToken: body.access_token,
      refreshToken: body.refresh_token ?? token.refreshToken,
      idToken: body.id_token ?? token.idToken,
      expiresAt: Math.floor(Date.now() / 1000) + (body.expires_in ?? 300),
      error: undefined,
    };
  } catch {
    return { ...token, error: "RefreshTokenError" };
  }
}
