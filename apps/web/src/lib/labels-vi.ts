// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { MealSlot } from "@metrace/api-client";

export const MEAL_SLOTS: readonly MealSlot[] = ["breakfast", "lunch", "dinner"];

export const MEAL_SLOT_LABELS_VI: Readonly<Record<MealSlot, string>> = {
  breakfast: "Bữa sáng",
  lunch: "Bữa trưa",
  dinner: "Bữa tối",
};

export const STORAGE_LABELS_VI: Readonly<Record<string, string>> = {
  chilled: "Hàng mát",
  frozen: "Hàng đông",
  dry: "Hàng khô",
};

export const BATCH_STATUS_LABELS_VI: Readonly<Record<string, string>> = {
  cooking: "Đang nấu",
  finished: "Hoàn tất",
  discarded: "Đã hủy",
};

export const SHIPMENT_STATUS_LABELS_VI: Readonly<Record<string, string>> = {
  planned: "Đã lên kế hoạch",
  ready: "Sẵn sàng",
  held: "Bị giữ",
  dispatched: "Đã xuất xe",
  delivered: "Đã giao",
};

/** The six steps of the meal-service checklist, in order. */
export const MEAL_STEP_LABELS_VI: Readonly<Record<string, string>> = {
  menu: "Thực đơn",
  received: "Nhận hàng",
  cooked: "Nấu xong",
  samples: "Lưu mẫu",
  form3: "Mẫu 3",
  dispatched: "Xuất xe",
};

export function mealSlotLabel(slot: string): string {
  return MEAL_SLOT_LABELS_VI[slot as MealSlot] ?? slot;
}
