// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { IncidentDetail } from "@metrace/api-client";
import { useState } from "react";
import { useApproveClose, useRequestClose } from "../../api/incident-mutations";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { Badge, Button, Card, Field, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { useBusinessClock } from "../../layout/business-clock";
import { CLOSE_REQUEST_STATUS_LABELS_VI } from "../../lib/labels-vi";

/** Four-eyes close: QA requests, a different person with the approver role approves (rule P5). */
export function CloseIncidentPanel({ incident }: { incident: IncidentDetail }) {
  const clock = useBusinessClock();
  const roles = currentSession().roles;
  const request = useRequestClose();
  const approve = useApproveClose();
  const [note, setNote] = useState("");
  const pending = incident.close_requests.find((r) => r.status === "pending");

  return (
    <Card title="Đóng sự cố (hai người xác nhận)">
      {incident.status === "closed" ? (
        <p className="text-lg">
          <Badge tone="green">Đã đóng</Badge> {incident.closed_at && <>lúc {clock.dateTime(incident.closed_at)}. </>}
          Các khóa đã được gỡ.
        </p>
      ) : pending ? (
        <div className="space-y-3">
          <p className="text-lg">
            <Badge tone="yellow">Chờ phê duyệt</Badge> Đề nghị đóng sự cố của <strong>{pending.requested_by}</strong> lúc{" "}
            {clock.dateTime(pending.requested_at)}.{pending.note && <> Ghi chú: {pending.note}</>}
          </p>
          {canDo(roles, "approveClose") ? (
            <Button busy={approve.isPending} onClick={() => approve.mutate(pending.id)}>
              Phê duyệt đóng sự cố
            </Button>
          ) : (
            <p className="text-base text-slate-700">Cần một người có vai trò người duyệt (khác người đề nghị) để phê duyệt.</p>
          )}
          <ViolationBanner error={approve.error} />
        </div>
      ) : canDo(roles, "requestClose") ? (
        <div className="space-y-3">
          <Field label="Ghi chú đề nghị đóng (đã xử lý gì, vì sao an toàn)">
            <input className={inputClass} value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} />
          </Field>
          <Button variant="secondary" busy={request.isPending} onClick={() => request.mutate({ incidentId: incident.id, note }, { onSuccess: () => setNote("") })}>
            Đề nghị đóng sự cố
          </Button>
          <ViolationBanner error={request.error} />
        </div>
      ) : (
        <p className="text-base text-slate-700">Chỉ QA được đề nghị đóng sự cố.</p>
      )}
      {incident.close_requests.some((r) => r.status !== "pending") && (
        <ul className="mt-3 space-y-1 text-base text-slate-700">
          {incident.close_requests
            .filter((r) => r.status !== "pending")
            .map((r) => (
              <li key={r.id}>
                {CLOSE_REQUEST_STATUS_LABELS_VI[r.status] ?? r.status}: đề nghị bởi {r.requested_by}
                {r.decided_by && <>, quyết định bởi {r.decided_by}</>}
              </li>
            ))}
        </ul>
      )}
    </Card>
  );
}
