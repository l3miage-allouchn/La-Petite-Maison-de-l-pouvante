"use server";

import { redirect } from "next/navigation";

import { signIn, signOut } from "@/auth";
import { config } from "@/lib/config";
import { getIdToken } from "@/lib/viewer";

/** Only same-site relative paths are accepted as return targets (no open redirect). */
function safeReturnPath(value: FormDataEntryValue | null): string {
  const path = typeof value === "string" ? value : "/";
  return path.startsWith("/") && !path.startsWith("//") ? path : "/";
}

export async function login(formData: FormData) {
  await signIn("keycloak", { redirectTo: safeReturnPath(formData.get("returnTo")) });
}

/** Local sign-out + Keycloak RP-initiated logout (ends the SSO session too). */
export async function logout() {
  const idToken = await getIdToken();
  await signOut({ redirect: false });
  const url = new URL(`${config.keycloakIssuer}/protocol/openid-connect/logout`);
  url.searchParams.set("post_logout_redirect_uri", `${config.appUrl}/`);
  url.searchParams.set("client_id", config.keycloakClientId);
  if (idToken) url.searchParams.set("id_token_hint", idToken);
  redirect(url.toString());
}
