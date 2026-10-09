// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Ingredient } from "@metrace/api-client";
import { Button, Field, inputClass } from "../../components/ui-primitives";
import { STORAGE_LABELS_VI } from "../../lib/labels-vi";

export interface LineDraft {
  key: number;
  ingredientId: string;
  qtyKg: string;
  tempC: string;
}

let nextKey = 1;
export const newLine = (): LineDraft => ({ key: nextKey++, ingredientId: "", qtyKg: "", tempC: "" });

/** "Giới hạn ≤ 4 °C" hint for chilled/frozen lines, from the configured thresholds. */
function tempHint(storage: string | undefined, limits: Record<string, string>): string | undefined {
  if (storage === "chilled") return `Hàng mát: nhiệt độ tối đa ${limits.chilled ?? "4"} °C, bắt buộc phải đo`;
  if (storage === "frozen") return `Hàng đông: nhiệt độ tối đa ${limits.frozen ?? "-18"} °C, bắt buộc phải đo`;
  return undefined;
}

export function ReceivingLinesEditor(props: {
  lines: LineDraft[];
  onChange: (lines: LineDraft[]) => void;
  ingredients: Ingredient[];
  /** Receiving temperature limits by storage kind, as text. */
  limits: Record<string, string>;
}) {
  const { lines, onChange, ingredients, limits } = props;
  const patch = (key: number, change: Partial<LineDraft>) =>
    onChange(lines.map((l) => (l.key === key ? { ...l, ...change } : l)));

  return (
    <div className="space-y-3">
      {lines.map((line, index) => {
        const ingredient = ingredients.find((i) => i.id === line.ingredientId);
        return (
          <div key={line.key} className="grid items-start gap-3 rounded-xl bg-slate-50 p-3 md:grid-cols-[2fr_1fr_1fr_auto]">
            <Field label={`Nguyên liệu ${index + 1}`}>
              <select
                className={inputClass}
                value={line.ingredientId}
                onChange={(e) => patch(line.key, { ingredientId: e.target.value })}
              >
                <option value="">- Chọn nguyên liệu -</option>
                {ingredients.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.name} ({STORAGE_LABELS_VI[i.storage] ?? i.storage})
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Khối lượng (kg)">
              <input
                className={inputClass}
                inputMode="decimal"
                placeholder="0"
                value={line.qtyKg}
                onChange={(e) => patch(line.key, { qtyKg: e.target.value })}
              />
            </Field>
            <Field label="Nhiệt độ (°C)" hint={tempHint(ingredient?.storage, limits)}>
              <input
                className={inputClass}
                inputMode="decimal"
                placeholder="vd. 3,5"
                value={line.tempC}
                onChange={(e) => patch(line.key, { tempC: e.target.value })}
              />
            </Field>
            <div className="md:pt-7">
              <Button
                variant="secondary"
                disabled={lines.length === 1}
                aria-label={`Xóa dòng ${index + 1}`}
                onClick={() => onChange(lines.filter((l) => l.key !== line.key))}
              >
                Xóa
              </Button>
            </div>
          </div>
        );
      })}
      <Button variant="secondary" onClick={() => onChange([...lines, newLine()])}>
        + Thêm dòng hàng
      </Button>
    </div>
  );
}
