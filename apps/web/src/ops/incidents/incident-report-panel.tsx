// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { IncidentDetail } from "@metrace/api-client";
import { useEffect, useState } from "react";
import { useApproveReport, useRequestReportDraft, useSaveReport } from "../../api/incident-mutations";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { Badge, Button, Card } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { useBusinessClock } from "../../layout/business-clock";

/** The draft is written by the worker within seconds (template) or ~30 s (language model); give up polling after this. */
const MAX_WAIT_MS = 60_000;

/** Which kind of draft this is: the template needs no caveat, a model's text must be read by QA. */
function DraftOrigin({ model }: { model: string | null | undefined }) {
  if (!model) return null;
  return model === "template" ? (
    <Badge tone="slate">Bản nháp mẫu (không dùng AI)</Badge>
  ) : (
    <Badge tone="yellow">Bản nháp do AI soạn - QA phải đọc lại</Badge>
  );
}

/**
 * Incident report: request a draft, edit, approve (QA). The draft never triggers anything; approval
 * freezes the text and records its hash in the audit chain. `onPoll` asks the page to refresh fast.
 */
export function IncidentReportPanel({ incident, onPoll }: { incident: IncidentDetail; onPoll: (ms: number | undefined) => void }) {
  const clock = useBusinessClock();
  const mayEdit = canDo(currentSession().roles, "editReport");
  const draft = useRequestReportDraft();
  const save = useSaveReport();
  const approve = useApproveReport();
  const [text, setText] = useState(incident.report_draft ?? "");
  const [dirty, setDirty] = useState(false);
  const [waiting, setWaiting] = useState<{ baseline: string | null; since: number }>();

  // A fresh draft from the server replaces the editor text unless QA is in the middle of editing.
  useEffect(() => {
    if (!dirty) setText(incident.report_draft ?? "");
  }, [incident.report_draft, dirty]);

  // Stop waiting as soon as the draft changed, or after the time limit.
  useEffect(() => {
    if (!waiting) return;
    const arrived = incident.report_draft !== waiting.baseline;
    const expired = Date.now() - waiting.since > MAX_WAIT_MS;
    if (arrived || expired) setWaiting(undefined);
  }, [waiting, incident.report_draft, incident.server_now]);
  useEffect(() => onPoll(waiting ? 2_000 : undefined), [waiting, onPoll]);

  if (incident.report_final !== null && incident.report_final !== undefined) {
    return (
      <Card title="Báo cáo sự cố" actions={<Badge tone="green">Đã phê duyệt</Badge>}>
        <pre className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-base">{incident.report_final}</pre>
        <p className="mt-2 text-base text-slate-700">
          Phê duyệt bởi {incident.report_approved_by}
          {incident.report_approved_at && <> lúc {clock.dateTime(incident.report_approved_at)}</>}. Nội dung đã được khóa và mã băm ghi vào nhật ký kiểm toán.
        </p>
      </Card>
    );
  }

  return (
    <Card title="Báo cáo sự cố" actions={<DraftOrigin model={incident.report_draft ? incident.report_model : null} />}>
      {mayEdit && (
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <Button
            variant="secondary"
            busy={draft.isPending}
            disabled={waiting !== undefined}
            onClick={() => draft.mutate(incident.id, { onSuccess: () => { setDirty(false); setWaiting({ baseline: incident.report_draft ?? null, since: Date.now() }); } })}
          >
            {incident.report_draft ? "Soạn lại bản nháp" : "Soạn bản nháp"}
          </Button>
          {waiting && <span role="status" className="text-lg text-slate-700">Đang soạn bản nháp...</span>}
        </div>
      )}
      {incident.report_draft || mayEdit ? (
        <textarea
          aria-label="Nội dung báo cáo"
          className="min-h-72 w-full rounded-lg border border-slate-400 bg-white p-3 font-mono text-base disabled:bg-slate-100"
          value={text}
          readOnly={!mayEdit}
          placeholder="Chưa có bản nháp. Bấm 'Soạn bản nháp' để hệ thống soạn từ dữ liệu sự cố."
          onChange={(e) => { setText(e.target.value); setDirty(true); }}
        />
      ) : (
        <p className="text-lg text-slate-600">Chưa có bản nháp báo cáo.</p>
      )}
      {mayEdit && (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button variant="secondary" busy={save.isPending} disabled={!dirty || text.trim() === ""} onClick={() => save.mutate({ incidentId: incident.id, text }, { onSuccess: () => setDirty(false) })}>
            Lưu chỉnh sửa
          </Button>
          <Button busy={approve.isPending} disabled={dirty || !incident.report_draft} onClick={() => approve.mutate(incident.id)}>
            Phê duyệt báo cáo
          </Button>
          {dirty && <span className="text-base text-slate-700">Lưu chỉnh sửa trước khi phê duyệt.</span>}
        </div>
      )}
      <div className="mt-3 space-y-3">
        <ViolationBanner error={draft.error ?? save.error ?? approve.error} />
      </div>
    </Card>
  );
}
