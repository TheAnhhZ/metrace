// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Batch, Dish } from "@metrace/api-client";
import { useState } from "react";
import { useAddShipmentItem } from "../../api/mutations";
import { Button, Field, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { parsePositiveInt } from "../../lib/decimal";

/** Put a finished batch on the truck (chef only). */
export function AddShipmentItemForm(props: { shipmentId: string; batches: Batch[]; dishes: Dish[] }) {
  const add = useAddShipmentItem();
  const [batchId, setBatchId] = useState("");
  const [portions, setPortions] = useState("");
  const [localError, setLocalError] = useState<string>();

  function choose(id: string) {
    setBatchId(id);
    const produced = props.batches.find((b) => b.id === id)?.portions_produced;
    if (produced) setPortions(String(produced));
  }

  function submit() {
    const amount = parsePositiveInt(portions);
    if (!batchId) return setLocalError("Chọn mẻ đưa lên xe.");
    if (amount === undefined) return setLocalError("Nhập số suất (số nguyên lớn hơn 0).");
    setLocalError(undefined);
    add.mutate(
      { shipmentId: props.shipmentId, body: { batch_id: batchId, portions: amount } },
      { onSuccess: () => { setBatchId(""); setPortions(""); } },
    );
  }

  return (
    <div className="space-y-3 rounded-xl bg-slate-50 p-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-64 flex-1">
          <Field label="Thêm mẻ lên xe">
            <select className={inputClass} value={batchId} onChange={(e) => choose(e.target.value)}>
              <option value="">- Chọn mẻ đã xong -</option>
              {props.batches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.batch_code} - {props.dishes.find((d) => d.id === b.dish_id)?.name ?? "Món"} ({b.portions_produced ?? 0} suất)
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="w-40">
          <Field label="Số suất">
            <input className={inputClass} inputMode="numeric" value={portions} onChange={(e) => setPortions(e.target.value)} />
          </Field>
        </div>
        <Button busy={add.isPending} onClick={submit}>
          Thêm
        </Button>
      </div>
      {localError && <p role="alert" className="text-lg font-semibold text-red-800">{localError}</p>}
      <ViolationBanner error={add.error} />
    </div>
  );
}
