// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Batch, Dish } from "@metrace/api-client";
import { useState } from "react";
import { useAddBatchInput } from "../../api/mutations";
import { useLots } from "../../api/read-queries";
import { QueryBoundary } from "../../components/query-boundary";
import { Button, Field, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { parseDecimal } from "../../lib/decimal";
import { LotPicker } from "./lot-picker";

type Source = "lot" | "batch";

/** Record what goes into a batch: a stock lot, or a finished batch of the day (bán thành phẩm). */
export function AddBatchInputPanel(props: { batch: Batch; finishedBatches: Batch[]; dishes: Dish[]; onClose: () => void }) {
  const { batch } = props;
  const lots = useLots();
  const add = useAddBatchInput();
  const [source, setSource] = useState<Source>("lot");
  const [lotId, setLotId] = useState("");
  const [inputBatchId, setInputBatchId] = useState("");
  const [qty, setQty] = useState("");
  const [localError, setLocalError] = useState<string>();
  const [added, setAdded] = useState<string[]>([]);

  function submit() {
    const qtyKg = parseDecimal(qty);
    const chosen = source === "lot" ? lotId : inputBatchId;
    if (!chosen) return setLocalError(source === "lot" ? "Chọn lô nguyên liệu." : "Chọn mẻ bán thành phẩm.");
    if (qtyKg === undefined || qtyKg <= 0) return setLocalError("Nhập khối lượng lớn hơn 0 (kg).");
    setLocalError(undefined);
    add.mutate(
      {
        batchId: batch.id,
        body: { qty_kg: qtyKg, ...(source === "lot" ? { lot_id: chosen } : { input_batch_id: chosen }) },
      },
      {
        onSuccess: () => {
          const label =
            source === "lot"
              ? (lots.data?.find((l) => l.id === chosen)?.lot_code ?? "lô")
              : (props.finishedBatches.find((b) => b.id === chosen)?.batch_code ?? "mẻ");
          setAdded((prev) => [...prev, `${label}: ${qtyKg} kg`]);
          setLotId("");
          setInputBatchId("");
          setQty("");
        },
      },
    );
  }

  const tabClass = (active: boolean) =>
    `min-h-12 flex-1 px-4 text-lg font-semibold ${active ? "bg-blue-700 text-white" : "bg-white hover:bg-slate-50"}`;

  return (
    <div className="space-y-3 rounded-xl bg-slate-50 p-3">
      <div role="tablist" className="flex overflow-hidden rounded-lg ring-1 ring-slate-400">
        <button type="button" role="tab" aria-selected={source === "lot"} className={tabClass(source === "lot")} onClick={() => setSource("lot")}>
          Lô nguyên liệu
        </button>
        <button type="button" role="tab" aria-selected={source === "batch"} className={tabClass(source === "batch")} onClick={() => setSource("batch")}>
          Bán thành phẩm (mẻ đã xong)
        </button>
      </div>
      {source === "lot" ? (
        <QueryBoundary query={lots}>{(list) => <LotPicker lots={list} value={lotId} onChange={setLotId} />}</QueryBoundary>
      ) : (
        <select className={inputClass} value={inputBatchId} onChange={(e) => setInputBatchId(e.target.value)} aria-label="Mẻ bán thành phẩm">
          <option value="">- Chọn mẻ đã hoàn tất -</option>
          {props.finishedBatches.map((b) => (
            <option key={b.id} value={b.id}>
              {b.batch_code} - {props.dishes.find((d) => d.id === b.dish_id)?.name ?? "Món"}
            </option>
          ))}
        </select>
      )}
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-48">
          <Field label="Khối lượng dùng (kg)">
            <input className={inputClass} inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} />
          </Field>
        </div>
        <Button busy={add.isPending} onClick={submit}>
          Thêm vào mẻ
        </Button>
        <Button variant="secondary" onClick={props.onClose}>
          Đóng
        </Button>
      </div>
      {localError && <p role="alert" className="text-lg font-semibold text-red-800">{localError}</p>}
      {added.length > 0 && <p role="status" className="text-lg text-green-800">Đã ghi: {added.join("; ")}</p>}
      <ViolationBanner error={add.error} />
    </div>
  );
}
