// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type LockResult, type Schemas, asShape, unwrap } from "@metrace/api-client";
import { api } from "./api-client-instance";
import { useWrite } from "./use-write";

export const useCreateComplaint = () =>
  useWrite((body: Schemas["ComplaintIn"]) => unwrap(api.POST("/api/v1/complaints", { body })));

export const useOpenIncident = () =>
  useWrite((body: Schemas["IncidentIn"]) => unwrap(api.POST("/api/v1/incidents", { body })));

/** Lock the confirmed suspects and everything downstream in one server transaction. */
export const useConfirmSuspects = () =>
  useWrite(
    async (v: { incidentId: string; body: Schemas["ConfirmSuspectsIn"] }) =>
      asShape<LockResult>(
        await unwrap(
          api.POST("/api/v1/incidents/{incident_id}/confirm-suspects", {
            params: { path: { incident_id: v.incidentId } },
            body: v.body,
          }),
        ),
      ),
  );

export const useRequestClose = () =>
  useWrite((v: { incidentId: string; note: string }) =>
    unwrap(
      api.POST("/api/v1/incidents/{incident_id}/close-requests", {
        params: { path: { incident_id: v.incidentId } },
        body: { note: v.note },
      }),
    ),
  );

/** Four-eyes: the server refuses (422 P5_SAME_PERSON) when the approver is also the requester. */
export const useApproveClose = () =>
  useWrite((requestId: string) =>
    unwrap(api.POST("/api/v1/close-requests/{request_id}/approve", { params: { path: { request_id: requestId } } })),
  );

export const useRequestReportDraft = () =>
  useWrite((incidentId: string) =>
    unwrap(api.POST("/api/v1/incidents/{incident_id}/report-draft", { params: { path: { incident_id: incidentId } } })),
  );

export const useSaveReport = () =>
  useWrite((v: { incidentId: string; text: string }) =>
    unwrap(
      api.PUT("/api/v1/incidents/{incident_id}/report", {
        params: { path: { incident_id: v.incidentId } },
        body: { text: v.text },
      }),
    ),
  );

export const useApproveReport = () =>
  useWrite((incidentId: string) =>
    unwrap(api.POST("/api/v1/incidents/{incident_id}/report/approve", { params: { path: { incident_id: incidentId } } })),
  );
