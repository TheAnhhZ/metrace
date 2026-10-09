// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { useClusterSuggestions, useComplaints } from "../../api/incident-queries";
import { useDeliveryPoints } from "../../api/read-queries";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { QueryBoundary } from "../../components/query-boundary";
import { PageTitle, RoleNotice } from "../../components/ui-primitives";
import { ClusterSuggestionCard } from "./cluster-suggestion-card";
import { ComplaintIntakeForm } from "./complaint-intake-form";
import { ComplaintList } from "./complaint-list";

/** Complaint desk: suggestions first (they are urgent), then intake, then the full list. */
export function ComplaintsPage() {
  const points = useDeliveryPoints();
  const suggestions = useClusterSuggestions();
  const allComplaints = useComplaints();
  const intake = canDo(currentSession().roles, "complaintIntake");

  return (
    <>
      <PageTitle hint="Phản ánh từ khách hàng. Khi nhiều điểm giao cùng phản ánh một mẻ, hệ thống gợi ý mở sự cố để QA xác nhận.">
        Phản ánh chất lượng
      </PageTitle>
      <QueryBoundary query={points}>
        {(pointList) => (
          <div className="space-y-4">
            <QueryBoundary query={suggestions}>
              {(list) =>
                list.length > 0 && (
                  <QueryBoundary query={allComplaints}>
                    {(complaints) => (
                      <div className="space-y-3">
                        {list.map((s) => (
                          <ClusterSuggestionCard key={s.batch_id} suggestion={s} complaints={complaints} />
                        ))}
                      </div>
                    )}
                  </QueryBoundary>
                )
              }
            </QueryBoundary>
            {intake ? <ComplaintIntakeForm points={pointList} /> : <RoleNotice>Chỉ CSKH và QA được ghi nhận phản ánh.</RoleNotice>}
            <ComplaintList points={pointList} />
          </div>
        )}
      </QueryBoundary>
    </>
  );
}
