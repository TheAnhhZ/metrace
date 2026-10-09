// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { GENERIC_ERROR_MESSAGE_VI, REASON_CODE_MESSAGES_VI, messageForCode } from "./reason-code-messages-vi";

const REASON_CODES_PY = fileURLToPath(new URL("../../../services/api/app/core/reason_codes.py", import.meta.url));

/** Every `NAME = "NAME"` member of the ReasonCode enum in the backend. */
function backendReasonCodes(): string[] {
  const source = readFileSync(REASON_CODES_PY, "utf8");
  return [...source.matchAll(/^\s+([A-Z0-9_]+)\s*=\s*"([A-Z0-9_]+)"/gm)].map((m) => m[2] as string);
}

describe("reason code messages (vi)", () => {
  it("covers every backend reason code", () => {
    const codes = backendReasonCodes();
    expect(codes.length).toBeGreaterThan(30);
    const missing = codes.filter((c) => !REASON_CODE_MESSAGES_VI[c]);
    expect(missing).toEqual([]);
  });

  it("has no message for a code the backend no longer knows (except client-side codes)", () => {
    const known = new Set([...backendReasonCodes(), "NETWORK_ERROR"]);
    expect(Object.keys(REASON_CODE_MESSAGES_VI).filter((c) => !known.has(c))).toEqual([]);
  });

  it("falls back to a generic message for unknown codes", () => {
    expect(messageForCode("SOMETHING_NEW")).toBe(GENERIC_ERROR_MESSAGE_VI);
  });
});
