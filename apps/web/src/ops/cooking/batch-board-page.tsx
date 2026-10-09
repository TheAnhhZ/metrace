// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { MealSlot } from "@metrace/api-client";
import { useState } from "react";
import { useBatches, useDishes } from "../../api/read-queries";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { MealSlotTabs } from "../../components/meal-slot-tabs";
import { QueryBoundary } from "../../components/query-boundary";
import { PageTitle, RoleNotice } from "../../components/ui-primitives";
import { useBusinessClock } from "../../layout/business-clock";
import { MEAL_SLOTS, mealSlotLabel } from "../../lib/labels-vi";
import { BatchCard } from "./batch-card";
import { StartBatchForm } from "./start-batch-form";

/** Mẫu 2: today's cooking batches by meal slot. Only the chef starts, feeds and finishes batches. */
export function BatchBoardPage() {
  const clock = useBusinessClock();
  const day = clock.day();
  const batches = useBatches(day);
  const dishes = useDishes();
  const [slot, setSlot] = useState<MealSlot>("lunch");
  const canCook = canDo(currentSession().roles, "cook");

  const counts = Object.fromEntries(
    MEAL_SLOTS.map((s) => [s, batches.data?.filter((b) => b.meal_slot === s).length ?? 0]),
  ) as Record<MealSlot, number>;

  return (
    <>
      <PageTitle hint={`Mẻ nấu ngày ${day}. Mỗi mẻ phải ghi nguyên liệu đầu vào và nhiệt độ tâm trước khi hoàn tất.`}>
        Chế biến
      </PageTitle>
      <MealSlotTabs value={slot} onChange={setSlot} counts={counts} />
      <QueryBoundary query={dishes}>
        {(dishList) => (
          <QueryBoundary query={batches}>
            {(all) => {
              const inSlot = all.filter((b) => b.meal_slot === slot);
              const finished = all.filter((b) => b.status === "finished");
              return (
                <div className="space-y-4">
                  {canCook ? <StartBatchForm dishes={dishList} slot={slot} /> : <RoleNotice>Chỉ bếp trưởng được bắt đầu, thêm nguyên liệu và hoàn tất mẻ.</RoleNotice>}
                  {inSlot.length === 0 && <p className="p-4 text-lg text-slate-600">Chưa có mẻ nào cho {mealSlotLabel(slot).toLowerCase()}.</p>}
                  {inSlot.map((b) => (
                    <BatchCard key={b.id} batch={b} dishes={dishList} finishedBatches={finished} canCook={canCook} />
                  ))}
                </div>
              );
            }}
          </QueryBoundary>
        )}
      </QueryBoundary>
    </>
  );
}
