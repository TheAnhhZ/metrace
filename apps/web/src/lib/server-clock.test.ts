// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { businessDay, computeOffsetMs, formatCountdown, parseInstant, remainingMs } from "./server-clock";

describe("server clock offset", () => {
  it("counts down on server time even when the tablet clock is wrong", () => {
    const serverNow = "2026-10-09T10:00:00Z";
    const tabletClock = Date.parse("2026-10-09T08:00:00Z"); // tablet is 2 h slow
    const offset = computeOffsetMs(serverNow, tabletClock);
    expect(offset).toBe(2 * 3600_000);

    const eligible = "2026-10-09T10:30:00Z";
    expect(remainingMs(eligible, tabletClock, offset)).toBe(30 * 60_000);
    // 10 s later on the tablet, 10 s less on the countdown
    expect(remainingMs(eligible, tabletClock + 10_000, offset)).toBe(30 * 60_000 - 10_000);
  });

  it("rejects a malformed server_now", () => {
    expect(() => computeOffsetMs("not-a-date", 0)).toThrow();
  });
});

describe("formatCountdown", () => {
  it("formats HH:MM:SS and clamps at zero", () => {
    expect(formatCountdown(3_661_000)).toBe("01:01:01");
    expect(formatCountdown(43.5 * 3600_000)).toBe("43:30:00");
    expect(formatCountdown(-5000)).toBe("00:00:00");
    expect(formatCountdown(999)).toBe("00:00:01");
  });
});

describe("businessDay", () => {
  it("uses the company time zone, not UTC", () => {
    const instant = Date.parse("2026-10-09T18:30:00Z"); // 01:30 on the 10th in Ho Chi Minh City
    expect(businessDay(instant, "Asia/Ho_Chi_Minh")).toBe("2026-10-10");
    expect(businessDay(instant, "UTC")).toBe("2026-10-09");
  });
});

describe("parseInstant", () => {
  it("accepts the server's microsecond timestamps", () => {
    expect(parseInstant("2026-10-09T10:14:42.964105Z")).toBe(Date.parse("2026-10-09T10:14:42.964Z"));
    expect(parseInstant("2026-10-09T10:14:42Z")).toBe(Date.parse("2026-10-09T10:14:42Z"));
    expect(parseInstant("2026-10-09T10:14:42.5+00:00")).toBe(Date.parse("2026-10-09T10:14:42.500Z"));
  });
});
