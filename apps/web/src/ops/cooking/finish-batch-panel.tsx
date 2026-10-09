// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type Batch, plainNumber } from "@metrace/api-client";
import { useState } from "react";
import { useFinishBatch } from "../../api/mutations";
import { useThresholds } from "../../api/read-queries";
import { Button, Field, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { parseDecimal } from "../../lib/decimal";

/** Mẫu 2: finish a batch with core temperature and portions. The server applies P2. */
export function FinishBatchPanel({ batch, onClose }: { batch: Batch; onClose: () => void }) {
  const finish = useFinishBatch();
  const minTemp = useThresholds().data?.core_temp_min_c?.value;
  const [temp, setTemp] = useState("");
  const [portions, setPortions] = useState(String(batch.portions_planned));
  const [localError, setLocalError] = useState<string>();

  function submit() {
    const coreTemp = parseDecimal(temp);
    const produced = parseDecimal(portions);
    if (coreTemp === undefined) return setLocalError("Nhập nhiệt độ tâm đo được (°C).");
    if (produced === undefined || !Number.isInteger(produced) || produced < 0) return setLocalError("Nhập số suất thực tế.");
    setLocalError(undefined);
    finish.mutate({ batchId: batch.id, body: { core_temp_c: coreTemp, portions_produced: produced } }, { onSuccess: onClose });
  }

  return (
    <div className="space-y-3 rounded-xl bg-slate-50 p-3">
      <p className="text-base text-slate-700">
        Mẻ phải có ít nhất một nguyên liệu đầu vào (bấm "Thêm nguyên liệu") mới hoàn tất được.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-56">
          <Field label="Nhiệt độ tâm (°C)" hint={minTemp ? `Tối thiểu ${plainNumber(minTemp)} °C` : undefined}>
            <input className={inputClass} inputMode="decimal" value={temp} onChange={(e) => setTemp(e.target.value)} />
          </Field>
        </div>
        <div className="w-56">
          <Field label="Số suất thực tế">
            <input className={inputClass} inputMode="numeric" value={portions} onChange={(e) => setPortions(e.target.value)} />
          </Field>
        </div>
        <Button busy={finish.isPending} onClick={submit}>
          Hoàn tất mẻ
        </Button>
        <Button variant="secondary" onClick={onClose}>
          Đóng
        </Button>
      </div>
      {localError && <p role="alert" className="text-lg font-semibold text-red-800">{localError}</p>}
      <ViolationBanner error={finish.error} />
    </div>
  );
}
