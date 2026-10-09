// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import Keycloak from "keycloak-js";

/**
 * Keycloak URL is always the gateway origin (also in dev), so token issuers match the API:
 * iss = http://localhost:9080/auth/realms/metrace. Override with VITE_KEYCLOAK_* for other hosts.
 */
const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL ?? "http://localhost:9080/auth",
  realm: import.meta.env.VITE_KEYCLOAK_REALM ?? "metrace",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? "metrace-web",
});

/** Refresh the access token when it expires within this many seconds. */
const MIN_TOKEN_VALIDITY_S = 30;

let initPromise: Promise<void> | undefined;

/** Log in (authorization code + PKCE S256). Resolves once a user is authenticated; call once before render. */
export function initSession(): Promise<void> {
  initPromise ??= keycloak
    .init({
      onLoad: "login-required",
      pkceMethod: "S256",
      scope: "openid organization",
      checkLoginIframe: false, // needs third-party cookies; the token refresh below is enough
    })
    .then((authenticated) => {
      if (!authenticated) throw new Error("not authenticated");
    });
  return initPromise;
}

/**
 * Access token for API calls, refreshed first when it is about to expire.
 * If the refresh fails (SSO session gone) the user is sent back to the login page.
 */
export async function getAccessToken(): Promise<string | undefined> {
  if (!keycloak.authenticated) return undefined;
  try {
    await keycloak.updateToken(MIN_TOKEN_VALIDITY_S);
  } catch {
    await keycloak.login();
    return undefined;
  }
  return keycloak.token;
}

export interface SessionInfo {
  username: string;
  /** Every realm role in the token (includes Keycloak defaults like offline_access). */
  roles: string[];
}

export function currentSession(): SessionInfo {
  const claims = keycloak.tokenParsed as
    | { preferred_username?: string; realm_access?: { roles?: string[] } }
    | undefined;
  return {
    username: claims?.preferred_username ?? "?",
    roles: claims?.realm_access?.roles ?? [],
  };
}

/** Send the user to the Keycloak login page again (token rejected or SSO session gone). */
export function forceLogin(): Promise<void> {
  return keycloak.login();
}

export function logout(): Promise<void> {
  return keycloak.logout({ redirectUri: `${window.location.origin}/` });
}
