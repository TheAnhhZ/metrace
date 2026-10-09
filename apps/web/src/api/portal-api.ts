// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type Notice, type Schemas, asShape, unwrap, uploadCustomerFile } from "@metrace/api-client";
import { useQuery } from "@tanstack/react-query";
import { computeOffsetMs } from "../lib/server-clock";
import { api } from "./api-client-instance";
import { useWrite } from "./use-write";

// Everything here is answered from the organizations in the caller's token; the SPA never sends an org.

export const usePortalDeliveries = (days = 3) =>
  useQuery({
    queryKey: ["portal-deliveries", days],
    queryFn: () => unwrap(api.GET("/api/v1/portal/deliveries", { params: { query: { days } } })),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });

export const usePortalPoints = () =>
  useQuery({
    queryKey: ["portal-points"],
    queryFn: () => unwrap(api.GET("/api/v1/portal/delivery-points")),
    staleTime: 5 * 60_000,
  });

/** The caller's complaints with the offset to the server clock, for the SLA countdowns. */
export const usePortalComplaints = () =>
  useQuery({
    queryKey: ["portal-complaints"],
    queryFn: async () => {
      const data = await unwrap(api.GET("/api/v1/portal/complaints"));
      return { ...data, offsetMs: computeOffsetMs(data.server_now, Date.now()) };
    },
    staleTime: 10_000,
    refetchInterval: 30_000,
  });

/** Recall/hold notices; polled so a notice sent while the page is open shows up quickly. */
export const usePortalNotices = () =>
  useQuery({
    queryKey: ["portal-notices"],
    queryFn: async () => asShape<Notice[]>(await unwrap(api.GET("/api/v1/portal/notices"))),
    staleTime: 5_000,
    refetchInterval: 15_000,
  });

export const useCreatePortalComplaint = () =>
  useWrite((body: Schemas["PortalComplaintIn"]) => unwrap(api.POST("/api/v1/portal/complaints", { body })));

export const useAcknowledgeNotice = () =>
  useWrite((noticeId: string) =>
    unwrap(api.POST("/api/v1/portal/notices/{notice_id}/acknowledge", { params: { path: { notice_id: noticeId } } })),
  );

export const useUploadPortalFile = () => useWrite((file: File) => uploadCustomerFile(api, file));
