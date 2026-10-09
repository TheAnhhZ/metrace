// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { DeliveryPoint, MealSlot } from "@metrace/api-client";
import { useState } from "react";
import { useCreateShipment } from "../../api/mutations";
import { Button, Card, Field, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { useBusinessClock } from "../../layout/business-clock";
import { mealSlotLabel } from "../../lib/labels-vi";

export function CreateShipmentForm({ points, slot }: { points: DeliveryPoint[]; slot: MealSlot }) {
  const clock = useBusinessClock();
  const create = useCreateShipment();
  const [pointId, setPointId] = useState("");

  return (
    <Card title={`Tạo chuyến giao - ${mealSlotLabel(slot)}`}>
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-72 flex-1">
          <Field label="Điểm giao">
            <select className={inputClass} value={pointId} onChange={(e) => setPointId(e.target.value)}>
              <option value="">- Chọn điểm giao -</option>
              {points.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} - {p.customer_name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Button
          busy={create.isPending}
          disabled={!pointId}
          onClick={() =>
            create.mutate(
              { delivery_point_id: pointId, service_date: clock.day(), meal_slot: slot },
              { onSuccess: () => setPointId("") },
            )
          }
        >
          Tạo chuyến
        </Button>
      </div>
      <div className="mt-3">
        <ViolationBanner error={create.error} />
      </div>
    </Card>
  );
}
