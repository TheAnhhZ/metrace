// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type MealSlot, unwrap } from "@metrace/api-client";
import { useQuery } from "@tanstack/react-query";
import { computeOffsetMs } from "../lib/server-clock";
import { api } from "./api-client-instance";

/** Master data changes through seeds/migrations only, so it can be cached for a while. */
const MASTER_DATA = { staleTime: 5 * 60_000 } as const;
/** Operational lists are refreshed in the background so a second tablet's work shows up. */
const LIVE = { staleTime: 5_000, refetchInterval: 15_000 } as const;

/** whoami plus the offset between the server clock and this tablet's clock at response time. */
export const whoAmIQueryOptions = {
  queryKey: ["whoami"],
  queryFn: async () => {
    const data = await unwrap(api.GET("/api/v1/whoami"));
    return { ...data, offsetMs: computeOffsetMs(data.server_now, Date.now()) };
  },
  staleTime: 5 * 60_000,
} as const;

export const useWhoAmI = () => useQuery(whoAmIQueryOptions);

export const useSuppliers = () =>
  useQuery({ queryKey: ["suppliers"], queryFn: () => unwrap(api.GET("/api/v1/suppliers")), staleTime: 30_000 });

export const useIngredients = () =>
  useQuery({ queryKey: ["ingredients"], queryFn: () => unwrap(api.GET("/api/v1/ingredients")), ...MASTER_DATA });

export const useDishes = () =>
  useQuery({ queryKey: ["dishes"], queryFn: () => unwrap(api.GET("/api/v1/dishes")), ...MASTER_DATA });

export const useDeliveryPoints = () =>
  useQuery({ queryKey: ["delivery-points"], queryFn: () => unwrap(api.GET("/api/v1/delivery-points")), ...MASTER_DATA });

/** Thresholds keyed by code, e.g. thresholds.receiving_chilled_max_c.value === "4". */
export const useThresholds = () =>
  useQuery({
    queryKey: ["rule-thresholds"],
    queryFn: async () => {
      const rows = await unwrap(api.GET("/api/v1/rule-thresholds"));
      return Object.fromEntries(rows.map((t) => [t.code, t]));
    },
    ...MASTER_DATA,
  });

/** Lots in stock, newest first; `locked` lots must not be offered as batch inputs. */
export const useLots = () =>
  useQuery({
    queryKey: ["lots", "in_stock"],
    queryFn: () => unwrap(api.GET("/api/v1/lots", { params: { query: { status: "in_stock" } } })),
    staleTime: 5_000,
  });

export const useBatches = (day: string) =>
  useQuery({
    queryKey: ["batches", day],
    queryFn: () => unwrap(api.GET("/api/v1/batches", { params: { query: { day } } })),
    ...LIVE,
  });

/** Samples of the day plus the server-vs-tablet clock offset captured when they arrived. */
export const useSamples = (day: string) =>
  useQuery({
    queryKey: ["samples", day],
    queryFn: async () => {
      const data = await unwrap(api.GET("/api/v1/samples", { params: { query: { day } } }));
      return { ...data, offsetMs: computeOffsetMs(data.server_now, Date.now()) };
    },
    ...LIVE,
  });

export const useShipments = (day: string, slot: MealSlot) =>
  useQuery({
    queryKey: ["shipments", day, slot],
    queryFn: () => unwrap(api.GET("/api/v1/shipments", { params: { query: { day, meal_slot: slot } } })),
    ...LIVE,
  });

export const useMealStatus = (day: string, slot: MealSlot) =>
  useQuery({
    queryKey: ["meal-status", day, slot],
    queryFn: () =>
      unwrap(api.GET("/api/v1/meal-services/{day}/{meal_slot}/status", { params: { path: { day, meal_slot: slot } } })),
    ...LIVE,
  });

/** Inputs already recorded on a batch (lots and intermediate batches), straight from the server. */
export const useBatchInputs = (batchId: string) =>
  useQuery({
    queryKey: ["batch-inputs", batchId],
    queryFn: () => unwrap(api.GET("/api/v1/batches/{batch_id}/inputs", { params: { path: { batch_id: batchId } } })),
    staleTime: 2_000,
  });
