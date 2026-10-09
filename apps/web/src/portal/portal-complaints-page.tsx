// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { usePortalComplaints, usePortalPoints } from "../api/portal-api";
import { QueryBoundary } from "../components/query-boundary";
import { SlaCountdown } from "../components/sla-countdown";
import { Badge, Card, PageTitle } from "../components/ui-primitives";
import { useBusinessClock } from "../layout/business-clock";
import { COMPLAINT_STATUS_LABELS_VI, mealSlotLabel } from "../lib/labels-vi";
import { PortalComplaintForm } from "./portal-complaint-form";

export function PortalComplaintsPage() {
  const points = usePortalPoints();
  const complaints = usePortalComplaints();
  const clock = useBusinessClock();

  return (
    <>
      <PageTitle hint="Báo cho chúng tôi nếu suất ăn có vấn đề. Mỗi phản ánh có thời hạn phản hồi cam kết.">Phản ánh</PageTitle>
      <div className="space-y-4">
        <QueryBoundary query={points}>
          {(list) =>
            list.length === 0 ? (
              <p className="rounded-xl bg-yellow-50 p-4 text-lg text-yellow-900">Tài khoản chưa được gắn với điểm nhận hàng nào, nên chưa gửi phản ánh được.</p>
            ) : (
              <PortalComplaintForm points={list} />
            )
          }
        </QueryBoundary>
        <Card title="Phản ánh đã gửi">
          <QueryBoundary query={complaints}>
            {(data) =>
              data.complaints.length === 0 ? (
                <p className="text-lg text-slate-600">Bạn chưa gửi phản ánh nào.</p>
              ) : (
                <ul className="divide-y divide-slate-200">
                  {data.complaints.map((c) => (
                    <li key={c.id} className="space-y-1 py-3">
                      <p className="flex flex-wrap items-center gap-2 text-lg">
                        <span className="font-mono font-bold">{c.code}</span>
                        <Badge tone={c.status === "resolved" ? "green" : c.status === "linked" ? "blue" : "yellow"}>
                          {COMPLAINT_STATUS_LABELS_VI[c.status] ?? c.status}
                        </Badge>
                      </p>
                      <p className="text-base text-slate-700">
                        {c.service_date}, {mealSlotLabel(c.meal_slot).toLowerCase()} - gửi lúc {clock.dateTime(c.created_at)}
                      </p>
                      {c.description && <p className="text-lg">{c.description}</p>}
                      <SlaCountdown complaint={c} offsetMs={data.offsetMs} />
                    </li>
                  ))}
                </ul>
              )
            }
          </QueryBoundary>
        </Card>
      </div>
    </>
  );
}
