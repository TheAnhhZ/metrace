// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { createApiClient } from "@metrace/api-client";
import { getAccessToken } from "../auth/keycloak-session";

/**
 * The one API client of the app. Same-origin `/api/...`: in dev Vite proxies to the gateway,
 * in production nginx sits behind the gateway. Every request gets a fresh bearer token.
 */
export const api = createApiClient({ baseUrl: window.location.origin, getToken: getAccessToken });
