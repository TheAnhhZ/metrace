// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Lineage, LineageNode } from "@metrace/api-client";
import type { ElementDefinition } from "cytoscape";

/** How a node is drawn: locked = red, held shipment = amber, already-dispatched shipment = recall. */
export type NodeVisual = "locked" | "held" | "recall" | "normal";

export const nodeKey = (n: { type: string; id: string }): string => `${n.type}:${n.id}`;

export function visualOf(node: Pick<LineageNode, "type" | "locked" | "status">): NodeVisual {
  if (node.locked) return "locked";
  if (node.type === "shipment") {
    if (node.status === "held") return "held";
    if (node.status === "dispatched" || node.status === "delivered") return "recall";
  }
  return "normal";
}

/** Delivery points show how many portions reached them. */
export function nodeLabel(node: LineageNode): string {
  return node.type === "delivery_point" && node.portions != null ? `${node.label}\n${node.portions} suất` : node.label;
}

/**
 * Cytoscape elements for a lineage. Node ids are the API's "type:id" keys, so edges map 1:1;
 * edges whose endpoint was cut off (truncated walk) are dropped instead of crashing the graph.
 */
export function buildElements(lineage: Lineage): ElementDefinition[] {
  const keys = new Set(lineage.nodes.map(nodeKey));
  const nodes: ElementDefinition[] = lineage.nodes.map((n) => ({
    data: { id: nodeKey(n), label: nodeLabel(n), type: n.type, depth: n.depth },
    classes: [n.type, visualOf(n), nodeKey(n) === lineage.root ? "root" : ""].filter(Boolean).join(" "),
  }));
  const edges: ElementDefinition[] = lineage.edges
    .filter((e) => keys.has(e.from) && keys.has(e.to))
    .map((e, i) => ({ data: { id: `edge-${i}`, source: e.from, target: e.to } }));
  return [...nodes, ...edges];
}

/** Counts for the summary line above the result. */
export function summarize(lineage: Lineage): { locked: number; held: number; recall: number; portions: number } {
  let locked = 0;
  let held = 0;
  let recall = 0;
  let portions = 0;
  for (const n of lineage.nodes) {
    const v = visualOf(n);
    if (v === "locked") locked++;
    else if (v === "held") held++;
    else if (v === "recall") recall++;
    if (n.type === "delivery_point") portions += n.portions ?? 0;
  }
  return { locked, held, recall, portions };
}
