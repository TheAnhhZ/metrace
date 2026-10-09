// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { LineageNode } from "@metrace/api-client";
import { Button, Card } from "../../components/ui-primitives";
import { NODE_TYPE_LABELS_VI, mealSlotLabel } from "../../lib/labels-vi";
import { NodeStateBadge } from "./lineage-table";

/** Details of the clicked node, plus "trace from here" to re-root the walk on it. */
export function LineageNodeDetails({ node, onReroot }: { node: LineageNode; onReroot: (node: LineageNode) => void }) {
  return (
    <Card title={node.label} actions={<NodeStateBadge node={node} />}>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-lg">
        <dt className="text-slate-600">Loại</dt>
        <dd>{NODE_TYPE_LABELS_VI[node.type] ?? node.type}</dd>
        <dt className="text-slate-600">Cách gốc</dt>
        <dd>{node.depth} bước</dd>
        {node.status && (
          <>
            <dt className="text-slate-600">Trạng thái</dt>
            <dd>{node.status}</dd>
          </>
        )}
        {node.portions != null && (
          <>
            <dt className="text-slate-600">Số suất đã giao</dt>
            <dd>{node.portions}</dd>
          </>
        )}
        {node.org && (
          <>
            <dt className="text-slate-600">Khách hàng</dt>
            <dd>{node.org}</dd>
          </>
        )}
        {node.service_date && (
          <>
            <dt className="text-slate-600">Bữa ăn</dt>
            <dd>
              {node.service_date}
              {node.meal_slot && `, ${mealSlotLabel(node.meal_slot).toLowerCase()}`}
            </dd>
          </>
        )}
        <dt className="text-slate-600">Mã nội bộ</dt>
        <dd className="break-all font-mono text-base">{node.id}</dd>
      </dl>
      <div className="mt-3">
        <Button variant="secondary" onClick={() => onReroot(node)}>
          Truy vết từ nút này
        </Button>
      </div>
    </Card>
  );
}
