// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import {
  type ApiError,
  type AuditHead,
  type ColdChainAlert,
  type ColdChainReadings,
  type VerifyResult,
  asShape,
  unwrap,
} from "@metrace/api-client";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "./api-client-instance";
import { useWrite } from "./use-write";

/** Open cold-chain alerts, polled every 10 s so a breach shows on every ops screen quickly. */
export const useColdChainAlerts = () =>
  useQuery({
    queryKey: ["coldchain-alerts"],
    queryFn: async () => asShape<ColdChainAlert[]>(await unwrap(api.GET("/api/v1/coldchain/alerts"))),
    staleTime: 5_000,
    refetchInterval: 10_000,
  });

export const useAssetReadings = (assetCode: string, minutes = 60) =>
  useQuery({
    queryKey: ["coldchain-readings", assetCode, minutes],
    queryFn: async () =>
      asShape<ColdChainReadings>(
        await unwrap(
          api.GET("/api/v1/coldchain/assets/{asset_code}/readings", {
            params: { path: { asset_code: assetCode }, query: { minutes } },
          }),
        ),
      ),
    staleTime: 5_000,
    refetchInterval: 10_000,
  });

export const useAcknowledgeAlert = () =>
  useWrite((v: { alertId: string; note: string }) =>
    unwrap(
      api.POST("/api/v1/coldchain/alerts/{alert_id}/acknowledge", {
        params: { path: { alert_id: v.alertId } },
        body: { note: v.note },
      }),
    ),
  );

export const useAuditHead = () =>
  useQuery({
    queryKey: ["audit-head"],
    queryFn: async () => asShape<{ seq: number | null; hash: string | null }>(await unwrap(api.GET("/api/v1/audit/head"))),
    staleTime: 5_000,
  });

export type { AuditHead };

/** Verify the whole hash chain, optionally against an anchor printed outside the database (read-only: no refetch of other data). */
export const useVerifyAudit = () =>
  useMutation<VerifyResult, ApiError, { seq: number; hash: string } | undefined>({
    mutationFn: (anchor) =>
      unwrap(
        api.GET("/api/v1/audit/verify", {
          params: { query: anchor ? { anchor_seq: anchor.seq, anchor_hash: anchor.hash } : {} },
        }),
      ),
  });
