import NextAuth from "next-auth";
import type { JWT } from "next-auth/jwt";
import Keycloak from "next-auth/providers/keycloak";

import { config } from "@/lib/config";
import { refreshAccessToken } from "@/lib/tokens";

/**
 * Auth.js + Keycloak: Authorization Code flow with PKCE, confidential client.
 *
 * Endpoints are explicit (no discovery) because the browser and the Next.js server do not reach
 * Keycloak at the same address (ADR-005): the authorization endpoint uses the public URL,
 * token and userinfo endpoints use the internal one. The issuer stays the public one.
 *
 * Tokens live only in the encrypted session cookie (JWE) and are read server-side; the session
 * object exposed to the browser contains no token.
 */
export const { handlers, auth, signIn, signOut } = NextAuth(() => {
  const publicIssuer = config.keycloakIssuer;
  const internalIssuer = config.keycloakInternalIssuer;
  return {
    providers: [
      Keycloak({
        clientId: config.keycloakClientId,
        clientSecret: config.keycloakClientSecret,
        issuer: publicIssuer,
        authorization: {
          url: `${publicIssuer}/protocol/openid-connect/auth`,
          params: { scope: "openid profile email" },
        },
        token: `${internalIssuer}/protocol/openid-connect/token`,
        userinfo: `${internalIssuer}/protocol/openid-connect/userinfo`,
        checks: ["pkce", "state", "nonce"],
      }),
    ],
    session: { strategy: "jwt", maxAge: 30 * 60 },
    trustHost: true,
    callbacks: {
      async jwt({ token, account, profile }): Promise<JWT> {
        if (account) {
          // First sign-in: keep what the server needs to call the APIs and to log out.
          return {
            ...token,
            sub: profile?.sub ?? token.sub,
            accessToken: account.access_token,
            refreshToken: account.refresh_token,
            idToken: account.id_token,
            expiresAt: account.expires_at,
          };
        }
        if (token.expiresAt && Date.now() < (token.expiresAt - 30) * 1000) return token;
        return refreshAccessToken(token);
      },
      async session({ session, token }) {
        // Only non-sensitive fields reach the browser.
        session.user.id = token.sub ?? "";
        session.error = token.error;
        return session;
      },
    },
  };
});
