// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { CertState, Supplier } from "@metrace/api-client";

export interface SupplierCertSummary {
  state: CertState;
  /** Days left on the best certificate (negative when expired); undefined when none on file. */
  daysLeft?: number;
}

/**
 * The supplier's standing is that of its best certificate: one valid certificate is enough,
 * mirroring the backend (P1 blocks only when no certificate is valid today).
 */
export function summarizeSupplierCert(supplier: Pick<Supplier, "certificates">): SupplierCertSummary {
  const best = [...supplier.certificates].sort((a, b) => b.days_left - a.days_left)[0];
  if (!best) return { state: "expired" };
  const state: CertState = best.state === "valid" || best.state === "expiring" ? best.state : "expired";
  return { state, daysLeft: best.days_left };
}
