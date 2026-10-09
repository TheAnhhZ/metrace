// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Link } from "react-router";
import { useConfirmSuspects } from "../../api/incident-mutations";
import { Badge, Button, Card } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { NODE_TYPE_LABELS_VI } from "../../lib/labels-vi";
import type { SuspectCandidate } from "../../lib/suspect-candidates";
import { LockResultPanel } from "./lock-result-panel";

const keyOf = (c: SuspectCandidate) => `${c.type}:${c.id}`;

/** QA picks what is suspected; the server locks it and everything downstream in one transaction. */
export function SuspectConfirmPanel(props: { incidentId: string; candidates: SuspectCandidate[]; closed: boolean }) {
  const confirm = useConfirmSuspects();
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [lockLots, setLockLots] = useState(true);
  const toggle = (key: string) =>
    setPicked((prev) => {
      const next = new Set(prev);
      if (!next.delete(key)) next.add(key);
      return next;
    });

  function submit() {
    const nodes = props.candidates.filter((c) => picked.has(keyOf(c))).map((c) => ({ type: c.type, id: c.id }));
    confirm.mutate({ incidentId: props.incidentId, body: { nodes, lock_lots: lockLots } }, { onSuccess: () => setPicked(new Set()) });
  }

  return (
    <Card title="Xác nhận nghi vấn và khóa">
      {props.candidates.length === 0 ? (
        <p className="text-lg text-slate-700">
          Chưa có gợi ý nguồn nghi vấn cho sự cố này. Dùng màn hình{" "}
          <Link to="/ops/trace" className="font-semibold text-blue-800 underline">
            Truy vết
          </Link>{" "}
          để tìm nguồn gốc của mẻ bị phản ánh.
        </p>
      ) : (
        <div className="space-y-3">
          <p className="text-lg text-slate-700">Chọn mẻ, lô hoặc nhà cung cấp nghi vấn. Hệ thống sẽ giữ lại mọi chuyến giao chưa xuất có liên quan.</p>
          <ul className="space-y-2">
            {props.candidates.map((c) => (
              <li key={keyOf(c)} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 p-2 pl-3">
                <label className="flex min-h-12 flex-1 items-center gap-3 text-lg">
                  <input
                    type="checkbox"
                    className="size-6"
                    checked={picked.has(keyOf(c))}
                    disabled={props.closed}
                    onChange={() => toggle(keyOf(c))}
                  />
                  <Badge tone="slate">{NODE_TYPE_LABELS_VI[c.type] ?? c.type}</Badge>
                  <span className="font-semibold">{c.label}</span>
                  {c.locked && <Badge tone="red">Đã khóa</Badge>}
                </label>
                <Link
                  to={`/ops/trace?type=${c.type}&ref=${c.id}&direction=both`}
                  className="flex min-h-11 items-center rounded-lg border border-slate-400 bg-white px-4 text-base font-semibold hover:bg-slate-100"
                >
                  Truy vết
                </Link>
              </li>
            ))}
          </ul>
          <label className="flex min-h-12 items-center gap-3 text-lg font-semibold">
            <input type="checkbox" className="size-6" checked={lockLots} onChange={(e) => setLockLots(e.target.checked)} />
            Khóa cả các lô nguyên liệu phía trước của mẻ được chọn
          </label>
          <Button variant="danger" busy={confirm.isPending} disabled={picked.size === 0 || props.closed} onClick={submit}>
            Xác nhận nghi vấn và khóa ({picked.size})
          </Button>
        </div>
      )}
      <div className="mt-3 space-y-3">
        {confirm.data && <LockResultPanel result={confirm.data} />}
        <ViolationBanner error={confirm.error} />
      </div>
    </Card>
  );
}
