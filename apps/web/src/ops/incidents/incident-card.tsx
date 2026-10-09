// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Incident } from "@metrace/api-client";
import { Link } from "react-router";
import { Badge } from "../../components/ui-primitives";
import { useBusinessClock } from "../../layout/business-clock";
import { INCIDENT_STATUS_LABELS_VI } from "../../lib/labels-vi";

/** The badge the director must not miss. */
export function EscalatedBadge() {
  return <span className="inline-flex items-center rounded-full bg-red-700 px-3 py-1 text-base font-bold text-white">Đã leo thang giám đốc</span>;
}

export function IncidentCard({ incident }: { incident: Incident }) {
  const clock = useBusinessClock();
  const closed = incident.status === "closed";
  return (
    <Link
      to={`/ops/incidents/${incident.id}`}
      className={`block rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 hover:ring-blue-600 ${closed ? "opacity-70" : ""}`}
    >
      <p className="flex flex-wrap items-center gap-2 text-xl font-bold">
        <span className="font-mono">{incident.code}</span>
        <Badge tone={closed ? "slate" : incident.status === "contained" ? "yellow" : "red"}>
          {INCIDENT_STATUS_LABELS_VI[incident.status] ?? incident.status}
        </Badge>
        {incident.escalated && <EscalatedBadge />}
      </p>
      <p className="mt-1 text-lg">{incident.title}</p>
      <p className="mt-1 text-base text-slate-600">
        Mở bởi {incident.opened_by} lúc {clock.dateTime(incident.opened_at)} - {incident.suspects.length} đối tượng nghi vấn
      </p>
    </Link>
  );
}
