// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { useIncidents } from "../../api/incident-queries";
import { QueryBoundary } from "../../components/query-boundary";
import { PageTitle } from "../../components/ui-primitives";
import { IncidentCard } from "./incident-card";

export function IncidentsPage() {
  const incidents = useIncidents();
  return (
    <>
      <PageTitle hint="Sự cố an toàn thực phẩm đang điều tra và đã đóng. Mở sự cố từ màn hình Phản ánh.">Sự cố</PageTitle>
      <QueryBoundary query={incidents}>
        {(list) => {
          const active = list.filter((i) => i.status !== "closed");
          const closed = list.filter((i) => i.status === "closed");
          return (
            <div className="space-y-4">
              {active.length === 0 && <p className="p-4 text-lg text-slate-600">Không có sự cố nào đang mở.</p>}
              <div className="grid gap-3 lg:grid-cols-2">
                {active.map((i) => (
                  <IncidentCard key={i.id} incident={i} />
                ))}
              </div>
              {closed.length > 0 && (
                <details className="rounded-xl bg-white p-4 ring-1 ring-slate-200">
                  <summary className="min-h-11 cursor-pointer text-xl font-bold">Đã đóng ({closed.length})</summary>
                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                    {closed.map((i) => (
                      <IncidentCard key={i.id} incident={i} />
                    ))}
                  </div>
                </details>
              )}
            </div>
          );
        }}
      </QueryBoundary>
    </>
  );
}
