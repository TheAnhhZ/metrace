// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { ClusterSuggestion, Complaint } from "@metrace/api-client";
import { Link, useNavigate } from "react-router";
import { useOpenIncident } from "../../api/incident-mutations";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { Badge, Button, Card } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { openComplaintIds } from "../../lib/suspect-candidates";

/** Several delivery points complained about the same batch. Only a suggestion: QA decides. */
export function ClusterSuggestionCard({ suggestion, complaints }: { suggestion: ClusterSuggestion; complaints: Complaint[] }) {
  const navigate = useNavigate();
  const open = useOpenIncident();
  const fresh = openComplaintIds(suggestion, complaints);
  const lots = suggestion.upstream.filter((n) => n.type === "lot");
  const mayOpen = canDo(currentSession().roles, "openIncident");

  return (
    <Card
      title={
        <>
          Mẻ <span className="font-mono">{suggestion.batch_code}</span> - {suggestion.dish}
        </>
      }
      actions={<Badge tone="yellow">Gợi ý - QA xác nhận</Badge>}
    >
      <p className="text-lg">
        <strong>{suggestion.n_complaints}</strong> phản ánh từ <strong>{suggestion.n_points}</strong> điểm giao khác nhau cùng liên quan đến mẻ này.
        {lots.length > 0 && <> Nguyên liệu phía trước: {lots.map((l) => l.label).join("; ")}.</>}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Link
          to={`/ops/trace?type=batch&ref=${encodeURIComponent(suggestion.batch_code)}&direction=both`}
          className="flex min-h-12 items-center rounded-lg border border-slate-400 bg-white px-5 text-lg font-semibold hover:bg-slate-50"
        >
          Xem truy vết mẻ
        </Link>
        {mayOpen &&
          (fresh.length > 0 ? (
            <Button
              variant="danger"
              busy={open.isPending}
              onClick={() =>
                open.mutate(
                  { title: `Nghi vấn mẻ ${suggestion.batch_code} - ${suggestion.dish}`, complaint_ids: fresh },
                  { onSuccess: (incident) => navigate(`/ops/incidents/${incident.id}`) },
                )
              }
            >
              Mở sự cố ({fresh.length} phản ánh mới)
            </Button>
          ) : (
            <span className="text-base text-slate-600">Các phản ánh này đã được gắn vào sự cố.</span>
          ))}
      </div>
      <div className="mt-3">
        <ViolationBanner error={open.error} />
      </div>
    </Card>
  );
}
