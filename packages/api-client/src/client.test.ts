// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { ApiError } from "./api-error";
import { createApiClient, unwrap } from "./client";

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

describe("createApiClient", () => {
  it("attaches the bearer token from the provider on every request", async () => {
    const seen: string[] = [];
    const client = createApiClient({
      baseUrl: "http://api.test",
      getToken: async () => "tok-1",
      fetch: async (input) => {
        seen.push((input as Request).headers.get("authorization") ?? "");
        return json(200, { sub: "u" });
      },
    });
    await client.GET("/api/v1/whoami");
    expect(seen).toEqual(["Bearer tok-1"]);
  });

  it("sends no Authorization header when signed out", async () => {
    let header: string | null = "unset";
    const client = createApiClient({
      baseUrl: "http://api.test",
      getToken: async () => undefined,
      fetch: async (input) => {
        header = (input as Request).headers.get("authorization");
        return json(200, {});
      },
    });
    await client.GET("/api/v1/whoami");
    expect(header).toBeNull();
  });
});

describe("unwrap", () => {
  const envelope = {
    error: {
      code: "P3_MISSING_FORM_3",
      rule: "P3",
      message: "Blocked by Poka-yoke rule P3",
      details: {
        violations: [{ rule: "P3", code: "P3_MISSING_FORM_3", batch: "B-1" }],
        warnings: [{ rule: "P1", code: "P1_SUPPLIER_CERT_EXPIRING", supplier: "NCC-06", days_left: 5 }],
      },
      request_id: "req-1",
    },
  };

  it("throws ApiError with violations and warnings from the 422 envelope", async () => {
    const client = createApiClient({
      baseUrl: "http://api.test",
      getToken: async () => "t",
      fetch: async () => json(422, envelope),
    });
    const err = await unwrap(client.GET("/api/v1/whoami")).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    const api = err as ApiError;
    expect(api.status).toBe(422);
    expect(api.code).toBe("P3_MISSING_FORM_3");
    expect(api.rule).toBe("P3");
    expect(api.requestId).toBe("req-1");
    expect(api.violations).toHaveLength(1);
    expect(api.warnings[0]?.days_left).toBe(5);
  });

  it("maps a rejected fetch to NETWORK_ERROR", async () => {
    const client = createApiClient({
      baseUrl: "http://api.test",
      getToken: async () => "t",
      fetch: async () => {
        throw new TypeError("Failed to fetch");
      },
    });
    const err = (await unwrap(client.GET("/api/v1/whoami")).catch((e: unknown) => e)) as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
  });

  it.each([
    [502, "SERVICE_UNAVAILABLE"],
    [500, "SERVICE_UNAVAILABLE"],
    [401, "UNAUTHENTICATED"],
    [429, "RATE_LIMITED"],
    [418, "INTERNAL_ERROR"],
  ])("maps a body without an envelope (HTTP %i) to %s", async (status, code) => {
    const client = createApiClient({
      baseUrl: "http://api.test",
      getToken: async () => "t",
      fetch: async () => json(status, { detail: "from the gateway" }),
    });
    const err = (await unwrap(client.GET("/api/v1/whoami")).catch((e: unknown) => e)) as ApiError;
    expect(err.code).toBe(code);
    expect(err.status).toBe(status);
  });
});
