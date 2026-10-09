// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type Batch, type Dish, type Shipment, toFindings } from "@metrace/api-client";
import { useEffect, useState } from "react";
import { useDispatchShipment } from "../../api/mutations";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { Badge, Button, Card } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { useBusinessClock } from "../../layout/business-clock";
import { SHIPMENT_STATUS_LABELS_VI } from "../../lib/labels-vi";
import { AddShipmentItemForm } from "./add-shipment-item-form";
import { PortionCheckForm } from "./portion-check-form";

const OPEN = ["planned", "ready", "held"];

export function ShipmentCard(props: { shipment: Shipment; batches: Batch[]; dishes: Dish[] }) {
  const { shipment } = props;
  const clock = useBusinessClock();
  const roles = currentSession().roles;
  const dispatch = useDispatchShipment();
  const [checking, setChecking] = useState<string | null>(null);
  const open = OPEN.includes(shipment.status);
  const blocked = shipment.blockers.length > 0;

  // A refusal is only true for the blockers it was about: forget it once the live blockers change.
  const blockerKey = shipment.blockers.map((b) => `${b.code}:${String(b.batch ?? "")}`).join("|");
  const resetAttempt = dispatch.reset;
  useEffect(() => resetAttempt(), [blockerKey, resetAttempt]);

  const tone = shipment.status === "held" ? "red" : shipment.status === "dispatched" || shipment.status === "delivered" ? "green" : "yellow";

  return (
    <Card
      title={
        <>
          <span className="font-mono">{shipment.code}</span> - {shipment.delivery_point}
        </>
      }
      actions={<Badge tone={tone}>{SHIPMENT_STATUS_LABELS_VI[shipment.status] ?? shipment.status}</Badge>}
    >
      {shipment.items.length === 0 ? (
        <p className="text-lg text-slate-600">Chưa có mẻ nào trên xe.</p>
      ) : (
        <ul className="space-y-2">
          {shipment.items.map((item) => (
            <li key={item.batch_id} className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-lg">
                  <span className="font-mono font-semibold">{item.batch_code}</span> - {item.portions} suất
                </span>
                <span className="flex items-center gap-2">
                  <Badge tone={item.form3_done ? "green" : "yellow"}>{item.form3_done ? "Đã ghi Mẫu 3" : "Chưa ghi Mẫu 3"}</Badge>
                  {open && !item.form3_done && canDo(roles, "portionCheck") && (
                    <Button variant="secondary" onClick={() => setChecking(checking === item.batch_id ? null : item.batch_id)}>
                      Ghi Mẫu 3
                    </Button>
                  )}
                </span>
              </div>
              {checking === item.batch_id && (
                <PortionCheckForm shipmentId={shipment.id} item={item} onClose={() => setChecking(null)} />
              )}
            </li>
          ))}
        </ul>
      )}

      {open && canDo(roles, "addShipmentItem") && (
        <div className="mt-3">
          <AddShipmentItemForm
            shipmentId={shipment.id}
            batches={props.batches.filter((b) => b.status === "finished" && b.meal_slot === shipment.meal_slot)}
            dishes={props.dishes}
          />
        </div>
      )}

      {open && (
        <div className="mt-4 space-y-3">
          {dispatch.error ? (
            <ViolationBanner error={dispatch.error} title="Hệ thống từ chối xuất xe" />
          ) : blocked ? (
            <ViolationBanner violations={toFindings(shipment.blockers)} title="Chưa thể xuất xe - hệ thống đang chặn vì:" />
          ) : (
            <p role="status" className="rounded-xl bg-green-50 p-3 text-lg font-semibold text-green-900">
              Đủ điều kiện xuất xe.
            </p>
          )}
          {canDo(roles, "dispatch") && (
            <div className="flex flex-wrap items-center gap-3">
              <Button variant={blocked ? "blocked" : "primary"} busy={dispatch.isPending} onClick={() => dispatch.mutate(shipment.id)}>
                Xuất xe
              </Button>
              {blocked && (
                <span className="text-base text-red-800">Chưa đủ điều kiện ({shipment.blockers.length} lỗi chặn). Bấm để xem phản hồi của hệ thống.</span>
              )}
            </div>
          )}
        </div>
      )}
      {shipment.dispatched_at && <p className="mt-3 text-lg text-slate-700">Đã xuất xe lúc {clock.dateTime(shipment.dispatched_at)}.</p>}
    </Card>
  );
}
