// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { LineageDirection, LineageNode, LineageNodeType } from "@metrace/api-client";
import { lazy, Suspense, useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { type LineageParams, useLineage } from "../../api/incident-queries";
import { QueryBoundary } from "../../components/query-boundary";
import { Badge, Button, Card, Field, PageTitle, inputClass } from "../../components/ui-primitives";
import { LINEAGE_DIRECTION_LABELS_VI, NODE_TYPE_LABELS_VI } from "../../lib/labels-vi";
import { LineageNodeDetails } from "./lineage-node-details";
import { LineageTable } from "./lineage-table";
import { nodeKey, summarize } from "./lineage-elements";

// Cytoscape is large and only this screen needs it, so the graph loads on demand.
const LineageGraph = lazy(() => import("./lineage-graph").then((m) => ({ default: m.LineageGraph })));

const TYPES = Object.keys(NODE_TYPE_LABELS_VI) as LineageNodeType[];
const DIRECTIONS = Object.keys(LINEAGE_DIRECTION_LABELS_VI) as LineageDirection[];

function paramsFrom(search: URLSearchParams): LineageParams | undefined {
  const ref = search.get("ref")?.trim();
  if (!ref) return undefined;
  const type = search.get("type") as LineageNodeType;
  const direction = search.get("direction") as LineageDirection;
  const depth = Number(search.get("max_depth"));
  return {
    type: TYPES.includes(type) ? type : "lot",
    ref,
    direction: DIRECTIONS.includes(direction) ? direction : "both",
    maxDepth: Number.isInteger(depth) && depth >= 1 && depth <= 12 ? depth : 8,
  };
}

function Legend() {
  return (
    <p className="flex flex-wrap items-center gap-2 text-base">
      <Badge tone="red">Đỏ: đang bị khóa</Badge>
      <Badge tone="yellow">Vàng: chuyến đã giữ lại</Badge>
      <span className="rounded-full bg-orange-200 px-3 py-1 text-base font-semibold text-orange-900 ring-1 ring-inset ring-orange-600">Cam nét đứt: đã xuất, cần thu hồi</span>
      <span className="text-slate-600">Viền dày: nút gốc</span>
    </p>
  );
}

/** Trace table + graph for any lot, batch, supplier, shipment, delivery point or fridge; URL = shareable query. */
export function TracePage() {
  const [search, setSearch] = useSearchParams();
  const params = useMemo(() => paramsFrom(search), [search]);
  const lineage = useLineage(params);
  const [view, setView] = useState<"graph" | "table">("graph");
  const [selected, setSelected] = useState<string>();
  const [type, setType] = useState<LineageNodeType>(params?.type ?? "lot");
  const [ref, setRef] = useState(params?.ref ?? "");
  const [direction, setDirection] = useState<LineageDirection>(params?.direction ?? "both");
  const [depth, setDepth] = useState(String(params?.maxDepth ?? 8));
  const [graphFailed, setGraphFailed] = useState(false);

  const go = (next: { type: string; ref: string; direction: string; max_depth: string }) => {
    setSelected(undefined);
    setGraphFailed(false);
    setSearch(next);
  };
  const onGraphError = useCallback(() => setGraphFailed(true), []);
  const reroot = (node: LineageNode) => {
    setType(node.type);
    setRef(node.id);
    go({ type: node.type, ref: node.id, direction, max_depth: depth });
  };

  return (
    <>
      <PageTitle hint="Nhập mã (hoặc mã nội bộ) của lô, mẻ, nhà cung cấp, chuyến giao, điểm giao hoặc tủ lạnh để xem hàng đến từ đâu và đã đi đâu.">
        Truy vết
      </PageTitle>
      <Card>
        <form
          className="grid gap-3 md:grid-cols-[1fr_2fr_1.5fr_8rem_auto] md:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            if (ref.trim()) go({ type, ref: ref.trim(), direction, max_depth: depth });
          }}
        >
          <Field label="Loại">
            <select className={inputClass} value={type} onChange={(e) => setType(e.target.value as LineageNodeType)}>
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {NODE_TYPE_LABELS_VI[t]}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Mã hoặc mã nội bộ" hint="Ví dụ LOT-20261009-RAU-CAI hoặc B-20261009-lunch-COM">
            <input className={inputClass} value={ref} onChange={(e) => setRef(e.target.value)} />
          </Field>
          <Field label="Chiều truy vết">
            <select className={inputClass} value={direction} onChange={(e) => setDirection(e.target.value as LineageDirection)}>
              {DIRECTIONS.map((d) => (
                <option key={d} value={d}>
                  {LINEAGE_DIRECTION_LABELS_VI[d]}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Độ sâu tối đa">
            <input className={inputClass} inputMode="numeric" value={depth} onChange={(e) => setDepth(e.target.value)} />
          </Field>
          <Button type="submit">
            Truy vết
          </Button>
        </form>
      </Card>
      {params && (
        <div className="mt-4 space-y-4">
          <QueryBoundary query={lineage}>
            {(result) => {
              const stats = summarize(result);
              const node = result.nodes.find((n) => nodeKey(n) === selected);
              const showGraph = view === "graph" && !graphFailed;
              return (
                <>
                  <div className="flex flex-wrap items-center gap-3">
                    <p className="text-lg">
                      <strong>{result.nodes.length}</strong> nút, <strong className={stats.locked ? "text-red-800" : ""}>{stats.locked}</strong> đang khóa,{" "}
                      <strong>{stats.held}</strong> chuyến giữ lại, <strong>{stats.recall}</strong> cần thu hồi, <strong>{stats.portions}</strong> suất đã tới khách.
                    </p>
                    <div role="tablist" aria-label="Kiểu hiển thị" className="inline-flex overflow-hidden rounded-xl ring-1 ring-slate-400">
                      {(["graph", "table"] as const).map((v) => (
                        <button key={v} type="button" role="tab" aria-selected={view === v} onClick={() => setView(v)} className={`min-h-12 px-5 text-lg font-semibold ${view === v ? "bg-blue-700 text-white" : "bg-white hover:bg-slate-50"}`}>
                          {v === "graph" ? "Đồ thị" : "Bảng"}
                        </button>
                      ))}
                    </div>
                  </div>
                  {result.truncated && (
                    <p role="alert" className="rounded-xl border-2 border-yellow-500 bg-yellow-50 p-3 text-lg font-semibold text-yellow-900">
                      Truy vết bị cắt vì quá sâu hoặc quá nhiều nút: kết quả chưa đầy đủ. Thu hẹp phạm vi hoặc truy vết từ một nút gần hơn.
                    </p>
                  )}
                  {graphFailed && <p className="text-base text-slate-700">Không vẽ được đồ thị trên thiết bị này; đang hiển thị dạng bảng.</p>}
                  <Legend />
                  {showGraph ? (
                    <Suspense fallback={<p className="p-4 text-lg text-slate-600">Đang tải đồ thị...</p>}>
                      <LineageGraph lineage={result} selected={selected} onSelect={setSelected} onError={onGraphError} />
                    </Suspense>
                  ) : (
                    <LineageTable lineage={result} selected={selected} onSelect={setSelected} />
                  )}
                  {node && <LineageNodeDetails node={node} onReroot={reroot} />}
                </>
              );
            }}
          </QueryBoundary>
        </div>
      )}
    </>
  );
}
