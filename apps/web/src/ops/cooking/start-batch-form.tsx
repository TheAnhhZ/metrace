// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Dish, MealSlot } from "@metrace/api-client";
import { useState } from "react";
import { useStartBatch } from "../../api/mutations";
import { Button, Card, Field, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { useBusinessClock } from "../../layout/business-clock";
import { mealSlotLabel } from "../../lib/labels-vi";
import { parsePositiveInt } from "../../lib/decimal";

/** Start a cooking batch for the selected meal slot (the batch code is assigned by the server). */
export function StartBatchForm({ dishes, slot }: { dishes: Dish[]; slot: MealSlot }) {
  const clock = useBusinessClock();
  const start = useStartBatch();
  const [dishId, setDishId] = useState("");
  const [portions, setPortions] = useState("");
  const [localError, setLocalError] = useState<string>();

  function submit() {
    const planned = parsePositiveInt(portions);
    if (!dishId) return setLocalError("Chọn món.");
    if (planned === undefined) return setLocalError("Nhập số suất dự kiến (số nguyên lớn hơn 0).");
    setLocalError(undefined);
    start.mutate(
      { dish_id: dishId, service_date: clock.day(), meal_slot: slot, portions_planned: planned },
      { onSuccess: () => { setDishId(""); setPortions(""); } },
    );
  }

  return (
    <Card title={`Bắt đầu mẻ mới - ${mealSlotLabel(slot)}`}>
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-64 flex-1">
          <Field label="Món">
            <select className={inputClass} value={dishId} onChange={(e) => setDishId(e.target.value)}>
              <option value="">- Chọn món -</option>
              {dishes.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="w-48">
          <Field label="Số suất dự kiến">
            <input className={inputClass} inputMode="numeric" value={portions} onChange={(e) => setPortions(e.target.value)} />
          </Field>
        </div>
        <Button busy={start.isPending} onClick={submit}>
          Bắt đầu nấu
        </Button>
      </div>
      {localError && <p role="alert" className="mt-2 text-lg font-semibold text-red-800">{localError}</p>}
      <div className="mt-3">
        <ViolationBanner error={start.error} />
      </div>
    </Card>
  );
}
