// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Lineage, LineageNode } from "@metrace/api-client";
import { describe, expect, it } from "vitest";
import { buildElements, nodeLabel, summarize, visualOf } from "./lineage-elements";

const node = (type: LineageNode["type"], id: string, extra: Partial<LineageNode> = {}): LineageNode =>
  ({ type, id, label: `${type}-${id}`, depth: 0, locked: false, ...extra }) as LineageNode;

const lineage: Lineage = {
  root: "lot:l1",
  direction: "forward",
  truncated: false,
  nodes: [
    node("lot", "l1", { locked: true }),
    node("batch", "b1", { locked: true }),
    node("shipment", "s1", { status: "held" }),
    node("shipment", "s2", { status: "dispatched" }),
    node("delivery_point", "d1", { portions: 120 }),
  ],
  edges: [
    { from: "lot:l1", to: "batch:b1" },
    { from: "batch:b1", to: "shipment:s1" },
    { from: "shipment:s2", to: "delivery_point:d1" },
    { from: "batch:b1", to: "shipment:cut-off" },
  ],
};

describe("visualOf", () => {
  it("locks win, then held and recall shipments", () => {
    expect(visualOf(node("lot", "x", { locked: true }))).toBe("locked");
    expect(visualOf(node("shipment", "x", { status: "held" }))).toBe("held");
    expect(visualOf(node("shipment", "x", { status: "dispatched" }))).toBe("recall");
    expect(visualOf(node("shipment", "x", { status: "delivered" }))).toBe("recall");
    expect(visualOf(node("shipment", "x", { status: "planned" }))).toBe("normal");
    expect(visualOf(node("batch", "x", { status: "held" }))).toBe("normal");
  });
});

describe("buildElements", () => {
  it("keys nodes as type:id, marks the root, and drops edges to missing nodes", () => {
    const elements = buildElements(lineage);
    const nodes = elements.filter((e) => !("source" in e.data));
    const edges = elements.filter((e) => "source" in e.data);
    expect(nodes).toHaveLength(5);
    expect(edges).toHaveLength(3);
    expect(nodes[0]?.data.id).toBe("lot:l1");
    expect(nodes[0]?.classes).toContain("root");
    expect(nodes[0]?.classes).toContain("locked");
    expect(nodes[3]?.classes).toContain("recall");
  });

  it("labels delivery points with their portions", () => {
    expect(nodeLabel(node("delivery_point", "d1", { portions: 120 }))).toBe("delivery_point-d1\n120 suất");
    expect(nodeLabel(node("lot", "l1"))).toBe("lot-l1");
  });
});

describe("summarize", () => {
  it("counts locked, held and recall nodes and affected portions", () => {
    expect(summarize(lineage)).toEqual({ locked: 2, held: 1, recall: 1, portions: 120 });
  });
});
