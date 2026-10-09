// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { buildSparkline } from "./sparkline-geometry";

const SIZE = { width: 200, height: 100, pad: 10 };
const at = (min: number) => new Date(Date.UTC(2026, 9, 9, 10, min)).toISOString();

describe("buildSparkline", () => {
  it("returns nothing without readings", () => {
    expect(buildSparkline([], { max_c: 5 }, SIZE)).toBeUndefined();
  });

  it("maps time to x and temperature to y (higher temperature = smaller y)", () => {
    const s = buildSparkline(
      [
        { at: at(0), temp_c: "3.0" },
        { at: at(30), temp_c: 9 },
        { at: at(60), temp_c: "4" },
      ],
      { min_c: 0, max_c: 5 },
      SIZE,
    );
    expect(s).toBeDefined();
    const dots = s?.dots ?? [];
    expect(dots[0]?.x).toBe(10);
    expect(dots[2]?.x).toBe(190);
    expect(dots[1]?.y).toBeLessThan(dots[0]?.y ?? 0);
    expect(dots.map((d) => d.breach)).toEqual([false, true, false]);
  });

  it("draws the limits and keeps them inside the plotted range", () => {
    const s = buildSparkline([{ at: at(0), temp_c: 2 }, { at: at(10), temp_c: 3 }], { min_c: 0, max_c: 5 }, SIZE);
    expect(s?.yMin).toBeLessThanOrEqual(-1);
    expect(s?.yMax).toBeGreaterThanOrEqual(6);
    expect(s?.maxY).toBeLessThan(s?.minY ?? 0);
  });

  it("sorts unordered readings and ignores unusable ones", () => {
    const s = buildSparkline(
      [
        { at: at(20), temp_c: 4 },
        { at: "garbage", temp_c: 4 },
        { at: at(0), temp_c: "x" },
        { at: at(10), temp_c: 3 },
      ],
      {},
      SIZE,
    );
    expect(s?.dots).toHaveLength(2);
    expect(s?.dots[0]?.temp).toBe(3);
    expect(s?.maxY).toBeUndefined();
  });

  it("handles a single reading", () => {
    const s = buildSparkline([{ at: at(0), temp_c: 4 }], { max_c: 5 }, SIZE);
    expect(s?.dots).toHaveLength(1);
    expect(s?.last.x).toBe(190);
  });
});
