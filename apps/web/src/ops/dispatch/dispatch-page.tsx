// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { MealSlot } from "@metrace/api-client";
import { useState } from "react";
import { useBatches, useDeliveryPoints, useDishes, useMealStatus, useShipments } from "../../api/read-queries";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { MealSlotTabs } from "../../components/meal-slot-tabs";
import { QueryBoundary } from "../../components/query-boundary";
import { PageTitle, RoleNotice } from "../../components/ui-primitives";
import { useBusinessClock } from "../../layout/business-clock";
import { mealSlotLabel } from "../../lib/labels-vi";
import { CreateShipmentForm } from "./create-shipment-form";
import { MealChecklistStrip } from "./meal-checklist-strip";
import { ShipmentCard } from "./shipment-card";

/** P3: loading the truck and sending it out. The blockers list explains what is still missing. */
export function DispatchPage() {
  const clock = useBusinessClock();
  const day = clock.day();
  const [slot, setSlot] = useState<MealSlot>("lunch");
  const status = useMealStatus(day, slot);
  const shipments = useShipments(day, slot);
  const batches = useBatches(day);
  const dishes = useDishes();
  const points = useDeliveryPoints();
  const roles = currentSession().roles;

  return (
    <>
      <PageTitle hint={`Chuyến giao ngày ${day}. Xe chỉ được xuất khi đủ Mẫu 1, 2, 3 và không có nguyên liệu bị khóa.`}>
        Xuất hàng
      </PageTitle>
      <MealSlotTabs value={slot} onChange={setSlot} />
      <QueryBoundary query={status}>{(s) => <MealChecklistStrip steps={s.steps} />}</QueryBoundary>
      <div className="space-y-4">
        {canDo(roles, "planShipment") ? (
          <QueryBoundary query={points}>{(list) => <CreateShipmentForm points={list} slot={slot} />}</QueryBoundary>
        ) : (
          <RoleNotice>Chỉ bếp trưởng và tài xế được tạo chuyến giao và xuất xe.</RoleNotice>
        )}
        <QueryBoundary query={shipments}>
          {(shipmentList) => (
            <QueryBoundary query={batches}>
              {(batchList) => (
                <QueryBoundary query={dishes}>
                  {(dishList) => (
                    <>
                      {shipmentList.length === 0 && (
                        <p className="p-4 text-lg text-slate-600">Chưa có chuyến giao nào cho {mealSlotLabel(slot).toLowerCase()}.</p>
                      )}
                      {shipmentList.map((s) => (
                        <ShipmentCard key={s.id} shipment={s} batches={batchList} dishes={dishList} />
                      ))}
                    </>
                  )}
                </QueryBoundary>
              )}
            </QueryBoundary>
          )}
        </QueryBoundary>
      </div>
    </>
  );
}
