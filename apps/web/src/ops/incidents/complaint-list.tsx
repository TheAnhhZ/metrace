// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { ComplaintStatus, DeliveryPoint } from "@metrace/api-client";
import { useState } from "react";
import { useComplaints } from "../../api/incident-queries";
import { QueryBoundary } from "../../components/query-boundary";
import { SlaCountdown } from "../../components/sla-countdown";
import { Badge, Card } from "../../components/ui-primitives";
import { useBusinessClock } from "../../layout/business-clock";
import { COMPLAINT_CHANNEL_LABELS_VI, COMPLAINT_STATUS_LABELS_VI, mealSlotLabel } from "../../lib/labels-vi";

const FILTERS: readonly (ComplaintStatus | undefined)[] = [undefined, "open", "linked", "resolved"];

export function ComplaintList({ points }: { points: DeliveryPoint[] }) {
  const clock = useBusinessClock();
  const [status, setStatus] = useState<ComplaintStatus>();
  const complaints = useComplaints(status);

  return (
    <Card title="Danh sách phản ánh">
      <div role="tablist" aria-label="Lọc theo trạng thái" className="mb-3 inline-flex flex-wrap overflow-hidden rounded-xl ring-1 ring-slate-400">
        {FILTERS.map((f) => (
          <button
            key={f ?? "all"}
            type="button"
            role="tab"
            aria-selected={f === status}
            onClick={() => setStatus(f)}
            className={`min-h-12 px-5 text-lg font-semibold ${f === status ? "bg-blue-700 text-white" : "bg-white hover:bg-slate-50"}`}
          >
            {f ? COMPLAINT_STATUS_LABELS_VI[f] : "Tất cả"}
          </button>
        ))}
      </div>
      <QueryBoundary query={complaints}>
        {(list) =>
          list.length === 0 ? (
            <p className="text-lg text-slate-600">Không có phản ánh nào.</p>
          ) : (
            <ul className="divide-y divide-slate-200">
              {list.map((c) => (
                <li key={c.id} className="space-y-1 py-3">
                  <p className="flex flex-wrap items-center gap-2 text-lg">
                    <span className="font-mono font-bold">{c.code}</span>
                    <Badge tone={c.status === "open" ? "yellow" : c.status === "linked" ? "blue" : "green"}>
                      {COMPLAINT_STATUS_LABELS_VI[c.status] ?? c.status}
                    </Badge>
                    <span>
                      {points.find((p) => p.id === c.delivery_point_id)?.name ?? "Điểm giao"} - {c.service_date}, {mealSlotLabel(c.meal_slot).toLowerCase()}
                    </span>
                    <span className="text-slate-600">
                      ({c.affected_count} người, {COMPLAINT_CHANNEL_LABELS_VI[c.channel] ?? c.channel}, ghi nhận lúc {clock.dateTime(c.created_at)})
                    </span>
                  </p>
                  {c.description && <p className="text-base text-slate-700">{c.description}</p>}
                  <SlaCountdown complaint={c} offsetMs={clock.offsetMs} />
                </li>
              ))}
            </ul>
          )
        }
      </QueryBoundary>
    </Card>
  );
}
