// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { messageForCode } from "./reason-code-messages-vi";
import type { PokaYokeFinding } from "./types";

const BASIS_TYPE_LABELS_VI: Readonly<Record<string, string>> = {
  law: "quy định pháp luật",
  guidance: "hướng dẫn",
  field: "thực tế bếp",
  internal: "quy định nội bộ",
};

/** "Căn cứ: hướng dẫn (QĐ 1246/QĐ-BYT ...)"; undefined when the finding carries no basis. */
export function basisLabelVi(finding: Pick<PokaYokeFinding, "basis" | "basis_type">): string | undefined {
  const { basis, basis_type: type } = finding;
  if (!basis && !type) return undefined;
  const typeLabel = type ? (BASIS_TYPE_LABELS_VI[type] ?? type) : undefined;
  if (typeLabel && basis) return `Căn cứ: ${typeLabel} (${basis})`;
  return `Căn cứ: ${typeLabel ?? basis}`;
}

const DEFAULT_UNIT_BY_CODE: Readonly<Record<string, string>> = {
  P1_TEMP_OUT_OF_RANGE: "°C",
  P2_CORE_TEMP_BELOW_MIN: "°C",
  P3_HOLD_TIME_EXCEEDED: "phút",
  P3_SAMPLE_MISSING: "suất",
};

/** Which thing the finding is about, e.g. "Mẻ B-001" or "Nhà cung cấp NCC-06". */
export function subjectLabelVi(f: PokaYokeFinding): string | undefined {
  if (f.batch) return `Mẻ ${f.batch}`;
  if (f.ingredient) return `Nguyên liệu ${f.ingredient}`;
  if (f.supplier) return `Nhà cung cấp ${f.supplier}`;
  if (f.shipment) return `Chuyến giao ${f.shipment}`;
  return undefined;
}

/** The API formats limits as decimals ("4.00"); show them the way people write them ("4"). */
export function plainNumber(value: string | number): string {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) && String(value).trim() !== "" ? String(n) : String(value);
}

/** "Đo được 8 °C, giới hạn 4 °C" style line from measured/limit/unit; undefined when nothing to show. */
export function measuredLimitVi(f: PokaYokeFinding): string | undefined {
  const unit = f.unit ?? DEFAULT_UNIT_BY_CODE[f.code] ?? "";
  const suffix = unit ? ` ${unit}` : "";
  const measured = f.code === "P3_HOLD_TIME_EXCEEDED" ? f.held_minutes : f.measured;
  const parts: string[] = [];
  if (f.code === "P1_TEMP_OUT_OF_RANGE" && (f.measured === null || f.measured === undefined)) {
    parts.push("Chưa đo nhiệt độ");
  } else if (measured !== undefined && measured !== null) {
    parts.push(`Đo được ${plainNumber(measured)}${suffix}`);
  }
  if (f.limit !== undefined && f.limit !== null) parts.push(`giới hạn ${plainNumber(f.limit)}${suffix}`);
  if (parts.length === 0) return undefined;
  const line = parts.join(", ");
  return line.charAt(0).toUpperCase() + line.slice(1);
}

/** Extra context lines for codes whose details are not measured/limit. */
function contextLinesVi(f: PokaYokeFinding): string[] {
  const lines: string[] = [];
  if (f.days_left !== undefined) lines.push(`Còn ${f.days_left} ngày hiệu lực`);
  if (f.expired_on) lines.push(`Hết hạn từ ${f.expired_on}`);
  if (f.remaining_minutes !== undefined) lines.push(`Còn khoảng ${f.remaining_minutes} phút nữa mới được hủy`);
  if (f.locks?.length) lines.push(`Sự cố khóa: ${[...new Set(f.locks.map((l) => l.incident))].join(", ")}`);
  if (f.open_incidents?.length) lines.push(`Sự cố đang mở: ${f.open_incidents.join(", ")}`);
  return lines;
}

export interface FindingViewVi {
  code: string;
  rule: string;
  message: string;
  subject?: string;
  measuredLimit?: string;
  context: string[];
  basis?: string;
}

/** Everything the violation banner needs to render one finding, all in Vietnamese. */
export function describeFindingVi(f: PokaYokeFinding): FindingViewVi {
  return {
    code: f.code,
    rule: f.rule,
    message: messageForCode(f.code),
    subject: subjectLabelVi(f),
    measuredLimit: measuredLimitVi(f),
    context: contextLinesVi(f),
    basis: basisLabelVi(f),
  };
}
