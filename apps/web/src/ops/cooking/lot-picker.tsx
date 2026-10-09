// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Lot } from "@metrace/api-client";
import { useState } from "react";
import { Badge, inputClass } from "../../components/ui-primitives";

/**
 * Pick an ingredient lot from stock. Locked lots (open incident) are shown but cannot be chosen,
 * so nobody has to find out at the server that a lot is quarantined.
 */
export function LotPicker(props: { lots: Lot[]; value: string; onChange: (lotId: string) => void }) {
  const [filter, setFilter] = useState("");
  const needle = filter.trim().toLowerCase();
  const shown = props.lots.filter(
    (l) => !needle || `${l.lot_code} ${l.ingredient_name} ${l.supplier_code}`.toLowerCase().includes(needle),
  );

  return (
    <div className="space-y-2">
      <input
        className={inputClass}
        placeholder="Tìm theo mã lô, tên nguyên liệu hoặc nhà cung cấp"
        aria-label="Tìm lô nguyên liệu"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
      <div role="radiogroup" aria-label="Lô nguyên liệu" className="max-h-72 space-y-2 overflow-y-auto">
        {shown.length === 0 && <p className="p-2 text-lg text-slate-600">Không có lô nào trong kho.</p>}
        {shown.map((lot) => {
          const selected = lot.id === props.value;
          return (
            <button
              key={lot.id}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={lot.locked}
              onClick={() => props.onChange(lot.id)}
              className={`flex min-h-14 w-full flex-wrap items-center justify-between gap-2 rounded-lg border-2 px-3 py-2 text-left disabled:cursor-not-allowed disabled:opacity-60 ${
                selected ? "border-blue-700 bg-blue-50" : "border-slate-300 bg-white"
              }`}
            >
              <span>
                <span className="block text-lg font-semibold">{lot.ingredient_name}</span>
                <span className="font-mono text-base text-slate-600">
                  {lot.lot_code} - {lot.supplier_code}
                </span>
              </span>
              <span className="flex items-center gap-2">
                <span className="text-lg">{lot.qty_kg} kg</span>
                {lot.locked && <Badge tone="red">Đang bị khóa</Badge>}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
