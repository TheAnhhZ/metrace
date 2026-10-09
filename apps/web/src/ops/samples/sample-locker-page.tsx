// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { useBatches, useDishes, useSamples } from "../../api/read-queries";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { QueryBoundary } from "../../components/query-boundary";
import { PageTitle, RoleNotice } from "../../components/ui-primitives";
import { useBusinessClock } from "../../layout/business-clock";
import { SampleCard } from "./sample-card";
import { StoreSampleForm } from "./store-sample-form";

/** P4: retained-sample locker. Countdowns run on the server's clock; only QA can discard. */
export function SampleLockerPage() {
  const clock = useBusinessClock();
  const day = clock.day();
  const samples = useSamples(day);
  const batches = useBatches(day);
  const dishes = useDishes();
  const roles = currentSession().roles;

  return (
    <>
      <PageTitle hint={`Mẫu lưu ngày ${day}. Mẫu phải được giữ đủ thời gian quy định trước khi hủy.`}>Tủ lưu mẫu</PageTitle>
      <QueryBoundary query={samples}>
        {(sampleData) => (
          <QueryBoundary query={batches}>
            {(batchList) => (
              <QueryBoundary query={dishes}>
                {(dishList) => {
                  const label = (batchId: string) => {
                    const batch = batchList.find((b) => b.id === batchId);
                    const dish = dishList.find((d) => d.id === batch?.dish_id);
                    return batch ? `${batch.batch_code} - ${dish?.name ?? "Món"}` : "Mẻ không rõ";
                  };
                  // Samples still in the locker first, soonest-to-be-discardable on top.
                  const ordered = [...sampleData.samples].sort(
                    (a, b) =>
                      Number(a.status !== "stored") - Number(b.status !== "stored") ||
                      a.eligible_discard_at.localeCompare(b.eligible_discard_at),
                  );
                  return (
                    <div className="space-y-4">
                      {canDo(roles, "storeSample") ? (
                        <StoreSampleForm batches={batchList} dishes={dishList} samples={sampleData.samples} />
                      ) : (
                        <RoleNotice>Chỉ bếp trưởng và QA được lưu mẫu.</RoleNotice>
                      )}
                      {!canDo(roles, "discardSample") && <RoleNotice>Chỉ QA được hủy mẫu.</RoleNotice>}
                      {ordered.length === 0 && <p className="p-4 text-lg text-slate-600">Chưa có mẫu lưu nào hôm nay.</p>}
                      <div className="grid gap-4 lg:grid-cols-2">
                        {ordered.map((s) => (
                          <SampleCard
                            key={s.id}
                            sample={s}
                            batchLabel={label(s.batch_id)}
                            offsetMs={sampleData.offsetMs}
                            canDiscard={canDo(roles, "discardSample")}
                          />
                        ))}
                      </div>
                    </div>
                  );
                }}
              </QueryBoundary>
            )}
          </QueryBoundary>
        )}
      </QueryBoundary>
    </>
  );
}
