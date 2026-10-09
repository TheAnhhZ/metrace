// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Supplier } from "@metrace/api-client";
import { Badge } from "../../components/ui-primitives";
import { summarizeSupplierCert } from "../../lib/supplier-cert-state";

/** Certificate standing of a supplier: red = expired, yellow = expiring (days left), green = valid. */
export function SupplierCertBadge({ supplier }: { supplier: Pick<Supplier, "certificates"> }) {
  const cert = summarizeSupplierCert(supplier);
  if (cert.state === "expired") return <Badge tone="red">Giấy chứng nhận hết hạn</Badge>;
  if (cert.state === "expiring") return <Badge tone="yellow">Sắp hết hạn - còn {cert.daysLeft} ngày</Badge>;
  return <Badge tone="green">Giấy chứng nhận còn hạn</Badge>;
}
