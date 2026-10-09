// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type Batch, type Dish, type Sample, plainNumber } from "@metrace/api-client";
import { useState } from "react";
import { useStoreSample } from "../../api/mutations";
import { useThresholds } from "../../api/read-queries";
import { Button, Card, Field, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { parsePositiveInt } from "../../lib/decimal";

/** Store a retained sample of a finished batch; liquid dishes are measured in ml, the rest in g. */
export function StoreSampleForm(props: { batches: Batch[]; dishes: Dish[]; samples: Sample[] }) {
  const store = useStoreSample();
  const thresholds = useThresholds().data;
  const [batchId, setBatchId] = useState("");
  const [qty, setQty] = useState("");
  const [localError, setLocalError] = useState<string>();

  const finished = props.batches.filter((b) => b.status === "finished");
  const dishOf = (b: Batch | undefined) => props.dishes.find((d) => d.id === b?.dish_id);
  const batch = finished.find((b) => b.id === batchId);
  const liquid = dishOf(batch)?.kind === "liquid";
  const unit = liquid ? "ml" : "g";
  const minimum = (liquid ? thresholds?.sample_min_liquid_ml : thresholds?.sample_min_solid_g)?.value;

  function submit() {
    const amount = parsePositiveInt(qty);
    if (!batch) return setLocalError("Chọn mẻ cần lưu mẫu.");
    if (amount === undefined) return setLocalError(`Nhập lượng mẫu (${unit}), số nguyên lớn hơn 0.`);
    setLocalError(undefined);
    store.mutate(
      { batch_id: batch.id, ...(liquid ? { qty_ml: amount } : { qty_g: amount }) },
      { onSuccess: () => { setBatchId(""); setQty(""); } },
    );
  }

  return (
    <Card title="Lưu mẫu mới">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-72 flex-1">
          <Field label="Mẻ đã nấu xong">
            <select className={inputClass} value={batchId} onChange={(e) => setBatchId(e.target.value)}>
              <option value="">- Chọn mẻ -</option>
              {finished.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.batch_code} - {dishOf(b)?.name ?? "Món"}
                  {props.samples.some((s) => s.batch_id === b.id && s.status === "stored") ? " (đã có mẫu)" : ""}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="w-52">
          <Field label={`Lượng mẫu (${unit})`} hint={minimum ? `Tối thiểu ${plainNumber(minimum)} ${unit}` : undefined}>
            <input className={inputClass} inputMode="numeric" value={qty} onChange={(e) => setQty(e.target.value)} />
          </Field>
        </div>
        <Button busy={store.isPending} onClick={submit}>
          Lưu mẫu và in tem
        </Button>
      </div>
      {localError && <p role="alert" className="mt-2 text-lg font-semibold text-red-800">{localError}</p>}
      <div className="mt-3">
        <ViolationBanner error={store.error} />
      </div>
    </Card>
  );
}
