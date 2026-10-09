// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { MealSlot } from "@metrace/api-client";
import { MEAL_SLOTS, MEAL_SLOT_LABELS_VI } from "../lib/labels-vi";

/** Big segmented control for choosing the meal of the day; `counts` adds a number per slot. */
export function MealSlotTabs(props: {
  value: MealSlot;
  onChange: (slot: MealSlot) => void;
  counts?: Partial<Record<MealSlot, number>>;
}) {
  return (
    <div role="tablist" aria-label="Bữa ăn" className="mb-4 inline-flex overflow-hidden rounded-xl ring-1 ring-slate-400">
      {MEAL_SLOTS.map((slot) => {
        const active = slot === props.value;
        const count = props.counts?.[slot];
        return (
          <button
            key={slot}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => props.onChange(slot)}
            className={`min-h-12 px-6 text-lg font-semibold ${active ? "bg-blue-700 text-white" : "bg-white text-slate-800 hover:bg-slate-50"}`}
          >
            {MEAL_SLOT_LABELS_VI[slot]}
            {count !== undefined && <span className="ml-2 opacity-80">({count})</span>}
          </button>
        );
      })}
    </div>
  );
}
