// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Lineage, LineageNode } from "@metrace/api-client";
import { Badge } from "../../components/ui-primitives";
import { BATCH_STATUS_LABELS_VI, NODE_TYPE_LABELS_VI, SHIPMENT_STATUS_LABELS_VI } from "../../lib/labels-vi";
import { nodeKey, visualOf } from "./lineage-elements";

function statusText(node: LineageNode): string {
  if (!node.status) return "";
  if (node.type === "batch") return BATCH_STATUS_LABELS_VI[node.status] ?? node.status;
  if (node.type === "shipment") return SHIPMENT_STATUS_LABELS_VI[node.status] ?? node.status;
  return node.status;
}

export function NodeStateBadge({ node }: { node: LineageNode }) {
  switch (visualOf(node)) {
    case "locked":
      return <Badge tone="red">Đang bị khóa</Badge>;
    case "held":
      return <Badge tone="yellow">Đã giữ lại</Badge>;
    case "recall":
      return <Badge tone="red">Cần thu hồi</Badge>;
    default:
      return null;
  }
}

/** The always-available reading of a lineage: sorted by distance from the root, one row per node. */
export function LineageTable(props: { lineage: Lineage; selected?: string; onSelect: (key: string) => void }) {
  const rows = [...props.lineage.nodes].sort((a, b) => a.depth - b.depth || a.type.localeCompare(b.type) || a.label.localeCompare(b.label));
  return (
    <div className="overflow-x-auto rounded-xl bg-white ring-1 ring-slate-300">
      <table className="w-full text-left text-lg">
        <thead className="bg-slate-100 text-base">
          <tr>
            <th className="p-3">Loại</th>
            <th className="p-3">Đối tượng</th>
            <th className="p-3">Cách gốc</th>
            <th className="p-3">Trạng thái</th>
            <th className="p-3 text-right">Số suất</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((n) => {
            const key = nodeKey(n);
            return (
              <tr
                key={key}
                aria-selected={key === props.selected}
                className={`border-t border-slate-200 ${key === props.selected ? "bg-blue-50" : ""} ${key === props.lineage.root ? "font-bold" : ""}`}
              >
                <td className="p-3">{NODE_TYPE_LABELS_VI[n.type] ?? n.type}</td>
                <td className="p-3">
                  <button type="button" onClick={() => props.onSelect(key)} className="min-h-11 text-left underline decoration-dotted">
                    {n.label}
                  </button>
                </td>
                <td className="p-3">{n.depth}</td>
                <td className="flex flex-wrap items-center gap-2 p-3">
                  {statusText(n)} <NodeStateBadge node={n} />
                </td>
                <td className="p-3 text-right">{n.portions ?? ""}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
