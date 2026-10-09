// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { ClusterSuggestion, Complaint, LineageNode } from "@metrace/api-client";
import { describe, expect, it } from "vitest";
import { candidateNodes, openComplaintIds, suggestionForComplaints } from "./suspect-candidates";

const node = (type: LineageNode["type"], id: string, label: string, locked = false): LineageNode => ({
  type,
  id,
  label,
  depth: 1,
  locked,
});

const suggestion = (batch: string, complaintIds: string[], upstream: LineageNode[] = []): ClusterSuggestion => ({
  batch_id: batch,
  batch_code: `B-${batch}`,
  dish: "Canh rau cải",
  n_complaints: complaintIds.length,
  n_points: 2,
  complaint_ids: complaintIds,
  upstream,
});

describe("candidateNodes", () => {
  it("lists the batch first, then lockable upstream nodes without duplicates", () => {
    const s = suggestion("b1", ["c1"], [
      node("lot", "l1", "LOT-1 · Rau cải", true),
      node("supplier", "s1", "NCC-02 · Rau an toàn"),
      node("batch", "b1", "same as the suggestion's batch"),
      node("asset", "a1", "Tủ mát"),
      node("lot", "l1", "duplicate"),
    ]);
    expect(candidateNodes(s).map((c) => `${c.type}:${c.id}`)).toEqual(["batch:b1", "lot:l1", "supplier:s1"]);
    expect(candidateNodes(s)[1]?.locked).toBe(true);
  });
});

describe("suggestionForComplaints", () => {
  it("picks the suggestion with the largest overlap", () => {
    const a = suggestion("a", ["c1"]);
    const b = suggestion("b", ["c1", "c2", "c3"]);
    expect(suggestionForComplaints([a, b], ["c2", "c3"])?.batch_id).toBe("b");
    expect(suggestionForComplaints([a, b], ["zzz"])).toBeUndefined();
  });
});

describe("openComplaintIds", () => {
  it("keeps only complaints that are still open", () => {
    const complaints = [
      { id: "c1", status: "open" },
      { id: "c2", status: "linked" },
    ] as Complaint[];
    expect(openComplaintIds(suggestion("a", ["c1", "c2", "c9"]), complaints)).toEqual(["c1"]);
  });
});
