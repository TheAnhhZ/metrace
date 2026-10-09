// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { ShipmentItem } from "@metrace/api-client";
import { useState } from "react";
import { useRecordPortionCheck } from "../../api/mutations";
import { Button, Field, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { parsePositiveInt } from "../../lib/decimal";

/** Mẫu 3: check portions, menu match and sensory quality of one batch on one shipment. */
export function PortionCheckForm(props: { shipmentId: string; item: ShipmentItem; onClose: () => void }) {
  const record = useRecordPortionCheck();
  const [portions, setPortions] = useState(String(props.item.portions));
  const [menuMatch, setMenuMatch] = useState(true);
  const [sensoryOk, setSensoryOk] = useState(true);
  const [note, setNote] = useState("");
  const [localError, setLocalError] = useState<string>();

  function submit() {
    const amount = parsePositiveInt(portions);
    if (amount === undefined) return setLocalError("Nhập số suất kiểm (số nguyên lớn hơn 0).");
    setLocalError(undefined);
    record.mutate(
      {
        batch_id: props.item.batch_id,
        shipment_id: props.shipmentId,
        portions: amount,
        menu_match: menuMatch,
        sensory_ok: sensoryOk,
        note,
      },
      { onSuccess: props.onClose },
    );
  }

  return (
    <div className="space-y-3 rounded-xl bg-slate-50 p-3">
      <div className="flex flex-wrap items-end gap-4">
        <div className="w-40">
          <Field label="Số suất kiểm">
            <input className={inputClass} inputMode="numeric" value={portions} onChange={(e) => setPortions(e.target.value)} />
          </Field>
        </div>
        <label className="flex min-h-12 items-center gap-3 text-lg font-semibold">
          <input type="checkbox" className="size-6" checked={menuMatch} onChange={(e) => setMenuMatch(e.target.checked)} />
          Đúng thực đơn
        </label>
        <label className="flex min-h-12 items-center gap-3 text-lg font-semibold">
          <input type="checkbox" className="size-6" checked={sensoryOk} onChange={(e) => setSensoryOk(e.target.checked)} />
          Cảm quan đạt
        </label>
        <div className="min-w-56 flex-1">
          <Field label="Ghi chú">
            <input className={inputClass} value={note} onChange={(e) => setNote(e.target.value)} />
          </Field>
        </div>
        <Button busy={record.isPending} onClick={submit}>
          Ghi Mẫu 3
        </Button>
        <Button variant="secondary" onClick={props.onClose}>
          Đóng
        </Button>
      </div>
      {localError && <p role="alert" className="text-lg font-semibold text-red-800">{localError}</p>}
      <ViolationBanner error={record.error} />
    </div>
  );
}
