import "server-only";

/** Server-side configuration. Nothing here is ever sent to the browser. */
function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing environment variable ${name}`);
  return value;
}

export const config = {
  /** Internal URLs (container network in Compose, Services in Kubernetes). */
  catalogApiUrl: process.env.CATALOG_API_URL ?? "http://localhost:8081",
  recoApiUrl: process.env.RECO_API_URL ?? "http://localhost:8082",
  /** Public issuer: what the browser is redirected to and the "iss" claim of tokens (ADR-005). */
  get keycloakIssuer(): string {
    return process.env.KEYCLOAK_ISSUER ?? "http://localhost:8080/realms/petite-maison";
  },
  /** Same realm, reachable from the Next.js server (token, userinfo, refresh). */
  get keycloakInternalIssuer(): string {
    return process.env.KEYCLOAK_INTERNAL_ISSUER ?? this.keycloakIssuer;
  },
  get keycloakClientId(): string {
    return process.env.AUTH_KEYCLOAK_ID ?? "frontend";
  },
  get keycloakClientSecret(): string {
    return required("AUTH_KEYCLOAK_SECRET");
  },
  get appUrl(): string {
    return process.env.AUTH_URL ?? "http://localhost:3000";
  },
};
