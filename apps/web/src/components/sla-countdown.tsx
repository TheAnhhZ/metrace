// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Complaint } from "@metrace/api-client";
import { CountdownTimer } from "./countdown-timer";
import { Badge } from "./ui-primitives";

/**
 * Response deadline of a complaint. Counts down on the server's clock; red once the server flagged
 * `sla_breached` or the deadline passed. Resolved complaints show no deadline.
 */
export function SlaCountdown({ complaint, offsetMs }: { complaint: Complaint; offsetMs: number }) {
  if (complaint.status === "resolved") return <Badge tone="green">Đã xử lý</Badge>;
  if (complaint.sla_breached) return <Badge tone="red">Quá hạn SLA</Badge>;
  return (
    <span className="inline-flex items-center gap-2 text-base">
      Hạn phản hồi còn
      <CountdownTimer
        target={complaint.sla_due_at}
        offsetMs={offsetMs}
        className="font-mono text-lg font-bold tabular-nums text-amber-700"
        doneLabel="Quá hạn SLA"
        doneClassName="rounded-full bg-red-100 px-3 py-1 text-base font-semibold text-red-900 ring-1 ring-inset ring-red-600"
      />
    </span>
  );
}
