// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { IncidentDetail } from "@metrace/api-client";
import { Badge, Card } from "../../components/ui-primitives";
import { useBusinessClock } from "../../layout/business-clock";
import { SHIPMENT_STATUS_LABELS_VI, mealSlotLabel } from "../../lib/labels-vi";

/** held = stopped before leaving (amber); dispatched/delivered = already out, must be recalled (red). */
function ShipmentState({ status }: { status: string }) {
  if (status === "held") return <Badge tone="yellow">Đã giữ lại</Badge>;
  if (status === "dispatched" || status === "delivered") return <Badge tone="red">Cần thu hồi - {SHIPMENT_STATUS_LABELS_VI[status]}</Badge>;
  return <Badge tone="slate">{SHIPMENT_STATUS_LABELS_VI[status] ?? status}</Badge>;
}

export function AffectedShipmentsCard({ incident }: { incident: IncidentDetail }) {
  const clock = useBusinessClock();
  const held = incident.shipments.filter((s) => s.status === "held").length;
  const recall = incident.shipments.filter((s) => s.status === "dispatched" || s.status === "delivered").length;

  return (
    <Card title="Chuyến giao bị ảnh hưởng">
      {incident.shipments.length === 0 ? (
        <p className="text-lg text-slate-600">Chưa có chuyến giao nào bị ảnh hưởng (chưa khóa đối tượng nào).</p>
      ) : (
        <>
          <p className="mb-3 text-lg">
            <strong>{held}</strong> chuyến đã giữ lại, <strong className={recall ? "text-red-800" : ""}>{recall}</strong> chuyến cần thu hồi.
          </p>
          <ul className="divide-y divide-slate-200">
            {incident.shipments.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-lg">
                <span>
                  <span className="font-mono font-semibold">{s.code}</span> - {s.delivery_point} ({s.service_date}, {mealSlotLabel(s.meal_slot).toLowerCase()})
                </span>
                <ShipmentState status={s.status} />
              </li>
            ))}
          </ul>
        </>
      )}
      {incident.notices.length > 0 && (
        <div className="mt-4">
          <h3 className="mb-2 text-lg font-bold">Thông báo gửi khách hàng</h3>
          <ul className="space-y-1">
            {incident.notices.map((n) => (
              <li key={n.id} className="flex flex-wrap items-center gap-2 text-lg">
                <span>{n.delivery_point}</span>
                {n.acknowledged_at ? (
                  <Badge tone="green">Đã nhận lúc {clock.dateTime(n.acknowledged_at)}</Badge>
                ) : (
                  <Badge tone="yellow">Chưa xác nhận đã nhận</Badge>
                )}
                <span className="text-base text-slate-600">đối chiếu #{n.audit_seq}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
