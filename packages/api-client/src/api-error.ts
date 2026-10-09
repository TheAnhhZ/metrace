// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { PokaYokeFinding } from "./types";

/** The single error envelope every failing API call returns. */
export interface ErrorEnvelope {
  error: {
    code: string;
    rule: string | null;
    message: string;
    details: Record<string, unknown>;
    request_id: string;
  };
}

/** Client-side code for "the request never got an answer" (offline, DNS, CORS). */
export const NETWORK_ERROR_CODE = "NETWORK_ERROR";

/** Thrown by `unwrap` for any non-2xx answer; carries the parsed envelope. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly rule: string | null;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;

  constructor(init: {
    status: number;
    code: string;
    rule?: string | null;
    message: string;
    details?: Record<string, unknown>;
    requestId?: string | null;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.rule = init.rule ?? null;
    this.details = init.details ?? {};
    this.requestId = init.requestId ?? null;
  }

  /** Blocking Poka-yoke findings (422 only); empty for every other error. */
  get violations(): PokaYokeFinding[] {
    return toFindings(this.details.violations);
  }

  /** Non-blocking findings that travelled with the error. */
  get warnings(): PokaYokeFinding[] {
    return toFindings(this.details.warnings);
  }
}

/**
 * Validate a loosely typed list (the OpenAPI schema models blockers/warnings as open objects)
 * into Poka-yoke findings; entries without a string `code` are dropped.
 */
export function toFindings(value: unknown): PokaYokeFinding[] {
  if (!Array.isArray(value)) return [];
  return value.filter(
    (v): v is PokaYokeFinding =>
      typeof v === "object" && v !== null && typeof (v as { code?: unknown }).code === "string",
  );
}

function isEnvelope(body: unknown): body is ErrorEnvelope {
  if (typeof body !== "object" || body === null) return false;
  const err = (body as { error?: unknown }).error;
  return typeof err === "object" && err !== null && typeof (err as { code?: unknown }).code === "string";
}

/** Turn an error response body (envelope or anything else) into an ApiError. */
export function toApiError(status: number, body: unknown): ApiError {
  if (isEnvelope(body)) {
    const e = body.error;
    return new ApiError({
      status,
      code: e.code,
      rule: e.rule ?? null,
      message: e.message,
      details: e.details ?? {},
      requestId: e.request_id ?? null,
    });
  }
  return new ApiError({ status, code: codeForBareStatus(status), message: `HTTP ${status}` });
}

/**
 * The API always answers with the envelope, so a body without one came from the gateway or a
 * proxy in front of it (APISIX 401/429, nginx 413, dev proxy 500 when the gateway is down).
 */
function codeForBareStatus(status: number): string {
  switch (status) {
    case 401:
      return "UNAUTHENTICATED";
    case 403:
      return "FORBIDDEN";
    case 404:
      return "NOT_FOUND";
    case 413:
      return "FILE_TOO_LARGE";
    case 429:
      return "RATE_LIMITED";
    default:
      return status >= 500 ? "SERVICE_UNAVAILABLE" : "INTERNAL_ERROR";
  }
}

export function networkError(cause: unknown): ApiError {
  const message = cause instanceof Error ? cause.message : "network error";
  return new ApiError({ status: 0, code: NETWORK_ERROR_CODE, message });
}
