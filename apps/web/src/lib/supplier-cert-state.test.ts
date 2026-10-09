// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { summarizeSupplierCert } from "./supplier-cert-state";

const cert = (days_left: number, state: string) => ({
  number: "C",
  cert_type: "ATTP",
  issued_on: "2025-01-01",
  expires_on: "2027-01-01",
  days_left,
  state,
});

describe("summarizeSupplierCert", () => {
  it("uses the best certificate", () => {
    expect(summarizeSupplierCert({ certificates: [cert(-10, "expired"), cert(200, "valid")] })).toEqual({
      state: "valid",
      daysLeft: 200,
    });
  });
  it("reports expiring with days left", () => {
    expect(summarizeSupplierCert({ certificates: [cert(12, "expiring")] })).toEqual({ state: "expiring", daysLeft: 12 });
  });
  it("is expired when all are expired or none on file", () => {
    expect(summarizeSupplierCert({ certificates: [cert(-3, "expired")] }).state).toBe("expired");
    expect(summarizeSupplierCert({ certificates: [] })).toEqual({ state: "expired" });
  });
});
