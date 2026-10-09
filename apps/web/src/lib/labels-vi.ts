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

export const COMPLAINT_STATUS_LABELS_VI: Readonly<Record<string, string>> = {
  open: "Mới",
  linked: "Đã gắn sự cố",
  resolved: "Đã xử lý",
};

export const COMPLAINT_CHANNEL_LABELS_VI: Readonly<Record<string, string>> = {
  portal: "Cổng khách hàng",
  phone: "Điện thoại",
  cskh: "CSKH",
};

export const INCIDENT_STATUS_LABELS_VI: Readonly<Record<string, string>> = {
  open: "Đang điều tra",
  contained: "Đã khoanh vùng",
  closed: "Đã đóng",
};

export const CLOSE_REQUEST_STATUS_LABELS_VI: Readonly<Record<string, string>> = {
  pending: "Chờ phê duyệt",
  approved: "Đã phê duyệt",
  rejected: "Bị từ chối",
};

export const NODE_TYPE_LABELS_VI: Readonly<Record<string, string>> = {
  supplier: "Nhà cung cấp",
  lot: "Lô nguyên liệu",
  batch: "Mẻ nấu",
  shipment: "Chuyến giao",
  delivery_point: "Điểm giao",
  asset: "Thiết bị lạnh",
};

export const LINEAGE_DIRECTION_LABELS_VI: Readonly<Record<string, string>> = {
  both: "Cả hai chiều",
  forward: "Xuôi dòng (hàng đã đi đâu)",
  backward: "Ngược dòng (nguồn gốc)",
};

/** Why the audit chain check failed, as reported by GET /audit/verify. */
export const AUDIT_FAILURE_REASONS_VI: Readonly<Record<string, string>> = {
  "hash mismatch": "Nội dung bản ghi, hoặc liên kết với bản ghi liền trước, đã bị sửa.",
  "anchor mismatch": "Mã băm tại vị trí đối chiếu khác với mã đã in: lịch sử trước mốc này đã bị thay đổi.",
  "anchor not found": "Không có bản ghi nào mang số thứ tự này trong nhật ký.",
};

/** Shipment status as a customer should read it (the kitchen's own words are in SHIPMENT_STATUS_LABELS_VI). */
export const PORTAL_SHIPMENT_STATUS_LABELS_VI: Readonly<Record<string, string>> = {
  planned: "Đang chuẩn bị",
  ready: "Sẵn sàng giao",
  held: "Tạm giữ để kiểm tra an toàn",
  dispatched: "Đã xuất xe",
  delivered: "Đã giao",
};
