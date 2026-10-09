// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import {
  type ClusterSuggestion,
  type Complaint,
  type ComplaintStatus,
  type Incident,
  type IncidentDetail,
  type Lineage,
  type LineageDirection,
  type LineageNodeType,
  asShape,
  unwrap,
} from "@metrace/api-client";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api-client-instance";

const LIVE = { staleTime: 5_000, refetchInterval: 15_000 } as const;

export const useComplaints = (status?: ComplaintStatus) =>
  useQuery({
    queryKey: ["complaints", status ?? "all"],
    queryFn: () => unwrap(api.GET("/api/v1/complaints", { params: { query: status ? { status } : {} } })),
    ...LIVE,
  });

/** "Several delivery points complained about the same batch": a suggestion QA confirms, never automatic. */
export const useClusterSuggestions = () =>
  useQuery({
    queryKey: ["cluster-suggestions"],
    queryFn: async () =>
      asShape<ClusterSuggestion[]>(
        await unwrap(
          api.GET("/api/v1/complaints/cluster-suggestions", { params: { query: { window_h: 48, min_points: 2 } } }),
        ),
      ),
    ...LIVE,
  });

export const useIncidents = () =>
  useQuery({ queryKey: ["incidents"], queryFn: () => unwrap(api.GET("/api/v1/incidents")), ...LIVE });

/** Incident detail; `pollMs` speeds refreshing up while waiting for the report draft. */
export const useIncident = (id: string, pollMs?: number) =>
  useQuery({
    queryKey: ["incident", id],
    queryFn: async () =>
      asShape<IncidentDetail>(
        await unwrap(api.GET("/api/v1/incidents/{incident_id}", { params: { path: { incident_id: id } } })),
      ),
    staleTime: 2_000,
    refetchInterval: pollMs ?? 15_000,
  });

export interface LineageParams {
  type: LineageNodeType;
  ref: string;
  direction: LineageDirection;
  maxDepth: number;
}

/** Trace a lot/batch/supplier/shipment/delivery point/asset by UUID or business code. */
export const useLineage = (params: LineageParams | undefined) =>
  useQuery({
    queryKey: ["lineage", params],
    enabled: params !== undefined,
    queryFn: async () => {
      const p = params as LineageParams;
      return asShape<Lineage>(
        await unwrap(
          api.GET("/api/v1/lineage/{node_type}/{ref}", {
            params: { path: { node_type: p.type, ref: p.ref }, query: { direction: p.direction, max_depth: p.maxDepth } },
          }),
        ),
      );
    },
    staleTime: 10_000,
    retry: false, // a 404 ("no such code") will not change by asking again
  });

export type { Complaint, Incident };
