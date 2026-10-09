// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Link, useParams } from "react-router";
import { useClusterSuggestions, useIncident } from "../../api/incident-queries";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { QueryBoundary } from "../../components/query-boundary";
import { SlaCountdown } from "../../components/sla-countdown";
import { Badge, Card, PageTitle } from "../../components/ui-primitives";
import { useBusinessClock } from "../../layout/business-clock";
import { INCIDENT_STATUS_LABELS_VI, mealSlotLabel } from "../../lib/labels-vi";
import { candidateNodes, suggestionForComplaints } from "../../lib/suspect-candidates";
import { AffectedShipmentsCard } from "./affected-shipments-card";
import { CloseIncidentPanel } from "./close-incident-panel";
import { EscalatedBadge } from "./incident-card";
import { IncidentReportPanel } from "./incident-report-panel";
import { SuspectConfirmPanel } from "./suspect-confirm-panel";

export function IncidentDetailPage() {
  const { id = "" } = useParams();
  const clock = useBusinessClock();
  const [pollMs, setPollMs] = useState<number>();
  const incident = useIncident(id, pollMs);
  const suggestions = useClusterSuggestions();
  const mayConfirm = canDo(currentSession().roles, "confirmSuspects");

  return (
    <QueryBoundary query={incident}>
      {(inc) => {
        const suggestion = suggestionForComplaints(suggestions.data ?? [], inc.complaints.map((c) => c.id));
        return (
          <>
            <Link to="/ops/incidents" className="mb-2 inline-flex min-h-11 items-center text-lg font-semibold text-blue-800 underline">
              Tất cả sự cố
            </Link>
            <PageTitle hint={`Mở bởi ${inc.opened_by} lúc ${clock.dateTime(inc.opened_at)}`}>
              <span className="font-mono">{inc.code}</span> - {inc.title}
            </PageTitle>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <Badge tone={inc.status === "closed" ? "slate" : inc.status === "contained" ? "yellow" : "red"}>
                {INCIDENT_STATUS_LABELS_VI[inc.status] ?? inc.status}
              </Badge>
              {inc.escalated && <EscalatedBadge />}
              {suggestion && (
                <Link
                  to={`/ops/trace?type=batch&ref=${suggestion.batch_id}&direction=both`}
                  className="flex min-h-11 items-center rounded-lg border border-slate-400 bg-white px-4 text-base font-semibold hover:bg-slate-50"
                >
                  Xem truy vết mẻ {suggestion.batch_code}
                </Link>
              )}
            </div>
            <div className="space-y-4">
              <Card title={`Phản ánh liên quan (${inc.complaints.length})`}>
                <ul className="divide-y divide-slate-200">
                  {inc.complaints.map((c) => (
                    <li key={c.id} className="space-y-1 py-2">
                      <p className="text-lg">
                        <span className="font-mono font-semibold">{c.code}</span> - {c.service_date}, {mealSlotLabel(c.meal_slot).toLowerCase()}, {c.affected_count} người
                      </p>
                      {c.description && <p className="text-base text-slate-700">{c.description}</p>}
                      <SlaCountdown complaint={c} offsetMs={clock.offsetMs} />
                    </li>
                  ))}
                  {inc.complaints.length === 0 && <li className="py-2 text-lg text-slate-600">Sự cố chưa gắn phản ánh nào.</li>}
                </ul>
              </Card>
              {mayConfirm && (
                <SuspectConfirmPanel
                  incidentId={inc.id}
                  candidates={suggestion ? candidateNodes(suggestion) : []}
                  closed={inc.status === "closed"}
                />
              )}
              {inc.locks.length > 0 && (
                <Card title={`Khóa đang hiệu lực (${inc.locks.filter((l) => l.active).length}/${inc.locks.length})`}>
                  <ul className="space-y-1 text-lg">
                    {inc.locks.map((l) => (
                      <li key={l.id} className="flex flex-wrap items-center gap-2">
                        <Badge tone={l.active ? "red" : "slate"}>{l.active ? "Đang khóa" : "Đã gỡ"}</Badge>
                        <Link to={`/ops/trace?type=${l.target_type}&ref=${l.target_id}&direction=both`} className="font-mono underline">
                          {l.target_type}:{l.target_id.slice(0, 8)}
                        </Link>
                        <span className="text-base text-slate-600">bởi {l.created_by} lúc {clock.dateTime(l.created_at)}</span>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
              <AffectedShipmentsCard incident={inc} />
              <CloseIncidentPanel incident={inc} />
              <IncidentReportPanel incident={inc} onPoll={setPollMs} />
            </div>
          </>
        );
      }}
    </QueryBoundary>
  );
}
