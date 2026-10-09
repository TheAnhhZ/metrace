// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { basisLabelVi, describeFindingVi, plainNumber } from "./finding-format-vi";

describe("basisLabelVi", () => {
  it("combines basis type and text", () => {
    expect(basisLabelVi({ basis: "QĐ 1246", basis_type: "guidance" })).toBe("Căn cứ: hướng dẫn (QĐ 1246)");
  });
  it("handles a missing basis and unknown types", () => {
    expect(basisLabelVi({})).toBeUndefined();
    expect(basisLabelVi({ basis_type: "internal" })).toBe("Căn cứ: quy định nội bộ");
    expect(basisLabelVi({ basis_type: "weird", basis: "x" })).toBe("Căn cứ: weird (x)");
  });
});

describe("describeFindingVi", () => {
  it("formats a temperature violation with measured, limit and basis", () => {
    const v = describeFindingVi({
      rule: "P1",
      code: "P1_TEMP_OUT_OF_RANGE",
      ingredient: "Thịt gà",
      measured: "9",
      limit: "4",
      basis: "Ngưỡng nội bộ",
      basis_type: "internal",
    });
    expect(v.subject).toBe("Nguyên liệu Thịt gà");
    expect(v.measuredLimit).toBe("Đo được 9 °C, giới hạn 4 °C");
    expect(v.basis).toBe("Căn cứ: quy định nội bộ (Ngưỡng nội bộ)");
  });

  it("shows limits without trailing zeros", () => {
    const v = describeFindingVi({ rule: "P2", code: "P2_CORE_TEMP_BELOW_MIN", batch: "B-1", measured: "62.5", limit: "75.00" });
    expect(v.measuredLimit).toBe("Đo được 62.5 °C, giới hạn 75 °C");
  });

  it("says the temperature is missing when measured is null", () => {
    const v = describeFindingVi({ rule: "P1", code: "P1_TEMP_OUT_OF_RANGE", measured: null, limit: "4" });
    expect(v.measuredLimit).toBe("Chưa đo nhiệt độ, giới hạn 4 °C");
  });

  it("uses held_minutes for the hold-time rule", () => {
    const v = describeFindingVi({ rule: "P3", code: "P3_HOLD_TIME_EXCEEDED", batch: "B-1", held_minutes: 150, limit: "120" });
    expect(v.measuredLimit).toBe("Đo được 150 phút, giới hạn 120 phút");
    expect(v.subject).toBe("Mẻ B-1");
  });

  it("lists lock incidents once and the retention countdown", () => {
    const v = describeFindingVi({
      rule: "P2",
      code: "P2_INPUT_LOCKED",
      locks: [
        { target: "lot:1", incident: "INC-1" },
        { target: "batch:2", incident: "INC-1" },
      ],
    });
    expect(v.context).toEqual(["Sự cố khóa: INC-1"]);
    expect(describeFindingVi({ rule: "P4", code: "P4_DISCARD_BEFORE_RETENTION", remaining_minutes: 90 }).context).toEqual([
      "Còn khoảng 90 phút nữa mới được hủy",
    ]);
  });
});

describe("plainNumber", () => {
  it("trims server decimals but leaves non-numbers alone", () => {
    expect(plainNumber("4.00")).toBe("4");
    expect(plainNumber("-18.00")).toBe("-18");
    expect(plainNumber("62.5")).toBe("62.5");
    expect(plainNumber(75)).toBe("75");
    expect(plainNumber("abc")).toBe("abc");
    expect(plainNumber("")).toBe("");
  });
});
