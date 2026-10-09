// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { MealStep } from "@metrace/api-client";
import { MEAL_STEP_LABELS_VI } from "../../lib/labels-vi";

const count = (detail: Record<string, unknown>, key: string): number => Number(detail[key] ?? 0);

/** Short progress text per step, from the numbers the API computes. */
function stepDetailVi(step: MealStep): string {
  const d = step.detail;
  switch (step.key) {
    case "menu":
      return `${count(d, "dishes")} món`;
    case "received":
      return `${count(d, "receivings_today")} phiếu nhận`;
    case "cooked":
      return `${count(d, "finished")}/${count(d, "planned")} món xong`;
    case "samples":
      return `${count(d, "sampled")}/${count(d, "served_batches")} mẻ có mẫu`;
    case "form3":
      return `${count(d, "checked")}/${count(d, "items")} mục đã kiểm`;
    case "dispatched": {
      const held = count(d, "held");
      return `${count(d, "dispatched")}/${count(d, "shipments")} chuyến${held ? `, ${held} bị giữ` : ""}`;
    }
    default:
      return "";
  }
}

/** The six steps of one meal service, done/not done at a glance. */
export function MealChecklistStrip({ steps }: { steps: MealStep[] }) {
  return (
    <ol aria-label="Tiến độ bữa ăn" className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-6">
      {steps.map((step, index) => (
        <li
          key={step.key}
          className={`rounded-xl border-2 p-3 ${step.done ? "border-green-600 bg-green-50" : "border-slate-300 bg-white"}`}
        >
          <p className="flex items-center gap-2 text-lg font-bold">
            <span
              aria-hidden="true"
              className={`flex size-7 items-center justify-center rounded-full text-base text-white ${step.done ? "bg-green-600" : "bg-slate-400"}`}
            >
              {step.done ? "✓" : index + 1}
            </span>
            {MEAL_STEP_LABELS_VI[step.key] ?? step.key}
          </p>
          <p className="mt-1 text-base text-slate-700">
            <span className="sr-only">{step.done ? "Đã xong. " : "Chưa xong. "}</span>
            {stepDetailVi(step)}
          </p>
        </li>
      ))}
    </ol>
  );
}
