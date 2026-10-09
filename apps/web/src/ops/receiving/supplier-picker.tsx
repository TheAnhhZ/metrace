// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { QueryBoundary } from "../../components/query-boundary";
import { Badge } from "../../components/ui-primitives";
import { useSuppliers } from "../../api/read-queries";
import { SupplierCertBadge } from "./supplier-cert-badge";

/**
 * Touch-friendly list of suppliers with certificate state. Blocked or expired suppliers stay
 * selectable on purpose: the server's refusal (P1) is the safety net and teaches the reason.
 */
export function SupplierPicker({ value, onChange }: { value: string; onChange: (id: string) => void }) {
  const suppliers = useSuppliers();
  return (
    <QueryBoundary query={suppliers}>
      {(list) => (
        <div role="radiogroup" aria-label="Nhà cung cấp" className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {list.map((s) => {
            const selected = s.id === value;
            return (
              <button
                key={s.id}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => onChange(s.id)}
                className={`min-h-24 rounded-xl border-2 p-3 text-left ${
                  selected ? "border-blue-700 bg-blue-50" : "border-slate-300 bg-white hover:border-slate-400"
                }`}
              >
                <span className="block text-lg font-bold">{s.name}</span>
                <span className="block font-mono text-base text-slate-600">{s.code}</span>
                <span className="mt-2 flex flex-wrap gap-2">
                  <SupplierCertBadge supplier={s} />
                  {s.status === "blocked" && <Badge tone="red">Bị chặn</Badge>}
                  {s.locked && <Badge tone="red">Đang bị khóa</Badge>}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </QueryBoundary>
  );
}
