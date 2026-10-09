// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import createClient, { type Client } from "openapi-fetch";
import { ApiError, networkError, toApiError } from "./api-error";
import type { paths } from "./schema";

export type ApiClient = Client<paths>;

/** Returns a fresh access token (refreshing it when close to expiry), or undefined if signed out. */
export type TokenProvider = () => Promise<string | undefined>;

export interface ApiClientOptions {
  /** Origin the `/api/...` paths hang off; "" means same origin. */
  baseUrl?: string;
  getToken: TokenProvider;
  /** Override for tests. */
  fetch?: typeof fetch;
}

/** openapi-fetch client that attaches `Authorization: Bearer` from the token provider. */
export function createApiClient({ baseUrl = "", getToken, fetch: fetchImpl }: ApiClientOptions): ApiClient {
  const client = createClient<paths>({ baseUrl, ...(fetchImpl ? { fetch: fetchImpl } : {}) });
  client.use({
    async onRequest({ request }) {
      const token = await getToken();
      if (token) request.headers.set("Authorization", `Bearer ${token}`);
      return request;
    },
  });
  return client;
}

interface FetchResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/**
 * Await an openapi-fetch call and return its data, or throw ApiError.
 * Network failures (fetch rejects) also become ApiError(code NETWORK_ERROR).
 */
export async function unwrap<T>(call: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await call;
  } catch (cause) {
    if (cause instanceof ApiError) throw cause;
    throw networkError(cause);
  }
  if (result.response.ok) return result.data as T;
  throw toApiError(result.response.status, result.error);
}

/**
 * Download a binary/text resource (e.g. the SVG seal) with the bearer token.
 * Returns a Blob the caller can turn into an object URL.
 */
export async function fetchBlob(
  url: string,
  getToken: TokenProvider,
  fetchImpl: typeof fetch = fetch,
): Promise<Blob> {
  const token = await getToken();
  let response: Response;
  try {
    response = await fetchImpl(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  } catch (cause) {
    throw networkError(cause);
  }
  if (!response.ok) {
    throw toApiError(response.status, await response.json().catch(() => null));
  }
  return response.blob();
}
