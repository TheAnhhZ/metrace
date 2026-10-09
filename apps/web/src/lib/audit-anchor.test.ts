// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { formatAnchor, parseAnchor, shortAnchor } from "./audit-anchor";

const HASH = "44aebcaed6c69035a59466e16ea3a4655607df81b1d4aaa41e6870657d9d83e3";

describe("audit anchor", () => {
  it("round-trips the copy format and shows a short form", () => {
    const anchor = { seq: 189, hash: HASH };
    expect(parseAnchor(formatAnchor(anchor))).toEqual(anchor);
    expect(shortAnchor(anchor)).toBe("#189 · 44aebcaed6c6");
  });

  it.each([`12 ${HASH}`, `#12 · ${HASH}`, `seq=12 hash=${HASH}`, `${HASH.toUpperCase()}:12`])("parses %s", (text) => {
    expect(parseAnchor(text)).toEqual({ seq: 12, hash: HASH });
  });

  it("rejects a truncated hash, a missing sequence number and garbage", () => {
    expect(parseAnchor(`12 ${HASH.slice(0, 12)}`)).toBeUndefined();
    expect(parseAnchor(HASH)).toBeUndefined();
    expect(parseAnchor("hello")).toBeUndefined();
    expect(parseAnchor(`0 ${HASH}`)).toBeUndefined();
  });
});
