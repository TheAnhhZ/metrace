// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { parseDecimal, parsePositiveInt } from "./decimal";

describe("parseDecimal", () => {
  it("accepts comma and dot decimals and negatives", () => {
    expect(parseDecimal("4,5")).toBe(4.5);
    expect(parseDecimal(" 4.5 ")).toBe(4.5);
    expect(parseDecimal("-18")).toBe(-18);
    expect(parseDecimal("0")).toBe(0);
  });
  it("returns undefined for empty or garbage", () => {
    expect(parseDecimal("")).toBeUndefined();
    expect(parseDecimal("abc")).toBeUndefined();
    expect(parseDecimal("1,2,3")).toBeUndefined();
  });
});

describe("parsePositiveInt", () => {
  it("only accepts whole numbers above zero", () => {
    expect(parsePositiveInt("250")).toBe(250);
    expect(parsePositiveInt("0")).toBeUndefined();
    expect(parsePositiveInt("2.5")).toBeUndefined();
    expect(parsePositiveInt("-3")).toBeUndefined();
  });
});
