// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Notice, NoticeShipment } from "@metrace/api-client";
import { useAcknowledgeNotice, usePortalNotices } from "../api/portal-api";
import { AuditAnchor } from "../components/audit-anchor";
import { QueryBoundary } from "../components/query-boundary";
import { Badge, Button, PageTitle } from "../components/ui-primitives";
import { ViolationBanner } from "../components/violation-banner";
import { useBusinessClock } from "../layout/business-clock";
import { mealSlotLabel } from "../lib/labels-vi";

function ShipmentLine({ s }: { s: NoticeShipment }) {
  const recall = s.action === "recall";
  return (
    <li className={`rounded-lg p-3 ${recall ? "bg-red-50" : "bg-yellow-50"}`}>
      <p className="flex flex-wrap items-center gap-2 text-lg font-semibold">
        <Badge tone={recall ? "red" : "yellow"}>{recall ? "Thu hồi - không sử dụng" : "Giữ lại - chưa sử dụng"}</Badge>
        {s.service_date}, {mealSlotLabel(s.meal_slot).toLowerCase()}
      </p>
      <p className="text-base text-slate-700">Chuyến {s.shipment}</p>
      <ul className="mt-1 text-lg">
        {s.items.map((i) => (
          <li key={`${i.batch}-${i.dish}`}>
            {i.dish} - {i.portions} suất <span className="text-base text-slate-600">(mẻ {i.batch})</span>
          </li>
        ))}
      </ul>
    </li>
  );
}

function NoticeCard({ notice }: { notice: Notice }) {
  const clock = useBusinessClock();
  const ack = useAcknowledgeNotice();
  const done = notice.acknowledged_at !== null;
  return (
    <article className={`rounded-xl bg-white p-4 shadow-sm ring-2 ${done ? "ring-slate-200" : "ring-red-600"}`}>
      <header className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-bold">
          {notice.content.incident} - {notice.content.title}
        </h2>
        {done ? <Badge tone="green">Đã nhận lúc {clock.dateTime(notice.acknowledged_at as string)}</Badge> : <Badge tone="red">Chưa xác nhận</Badge>}
      </header>
      <p className="mb-2 text-base text-slate-700">
        {notice.content.delivery_point} - gửi lúc {clock.dateTime(notice.created_at)}
      </p>
      <ul className="space-y-2">
        {notice.content.shipments.map((s) => (
          <ShipmentLine key={s.shipment} s={s} />
        ))}
      </ul>
      <div className="mt-3 space-y-3">
        <AuditAnchor anchor={{ seq: notice.audit_seq, hash: notice.audit_hash }} />
        {!done && (
          <Button className="w-full" busy={ack.isPending} onClick={() => ack.mutate(notice.id)}>
            Đã nhận
          </Button>
        )}
        <ViolationBanner error={ack.error} />
      </div>
    </article>
  );
}

/** Hold/recall notices from the kitchen. Unacknowledged ones first; acknowledging is one tap. */
export function PortalNoticesPage() {
  const notices = usePortalNotices();
  return (
    <>
      <PageTitle hint="Thông báo khi suất ăn cần giữ lại hoặc thu hồi vì lý do an toàn thực phẩm.">Thông báo</PageTitle>
      <QueryBoundary query={notices}>
        {(list) => {
          const ordered = [...list].sort((a, b) => Number(a.acknowledged_at !== null) - Number(b.acknowledged_at !== null) || b.created_at.localeCompare(a.created_at));
          return ordered.length === 0 ? (
            <p className="p-4 text-lg text-slate-600">Không có thông báo nào.</p>
          ) : (
            <div className="space-y-4">
              {ordered.map((n) => (
                <NoticeCard key={n.id} notice={n} />
              ))}
            </div>
          );
        }}
      </QueryBoundary>
    </>
  );
}
