// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type ApiError, uploadCompanyFile, unwrap } from "@metrace/api-client";
import type { Schemas } from "@metrace/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./api-client-instance";

/**
 * Mutation that refreshes every cached list afterwards: one write (a lot used up, a sample stored,
 * a Mẫu 3 recorded) changes several screens at once, and the data is small.
 */
function useWrite<TVars, TData>(run: (vars: TVars) => Promise<TData>) {
  const queryClient = useQueryClient();
  return useMutation<TData, ApiError, TVars>({
    mutationFn: run,
    onSuccess: () => queryClient.invalidateQueries(),
  });
}

export const useUploadDocument = () => useWrite((file: File) => uploadCompanyFile(api, file));

export const useCreateReceiving = () =>
  useWrite((body: Schemas["ReceivingIn"]) => unwrap(api.POST("/api/v1/receivings", { body })));

export const useStartBatch = () =>
  useWrite((body: Schemas["BatchIn"]) => unwrap(api.POST("/api/v1/batches", { body })));

export const useAddBatchInput = () =>
  useWrite((v: { batchId: string; body: Schemas["BatchInputIn"] }) =>
    unwrap(api.POST("/api/v1/batches/{batch_id}/inputs", { params: { path: { batch_id: v.batchId } }, body: v.body })),
  );

export const useFinishBatch = () =>
  useWrite((v: { batchId: string; body: Schemas["BatchFinishIn"] }) =>
    unwrap(api.POST("/api/v1/batches/{batch_id}/finish", { params: { path: { batch_id: v.batchId } }, body: v.body })),
  );

export const useStoreSample = () =>
  useWrite((body: Schemas["SampleIn"]) => unwrap(api.POST("/api/v1/samples", { body })));

export const useDiscardSample = () =>
  useWrite((sampleId: string) =>
    unwrap(api.POST("/api/v1/samples/{sample_id}/discard", { params: { path: { sample_id: sampleId } } })),
  );

export const useCreateShipment = () =>
  useWrite((body: Schemas["ShipmentIn"]) => unwrap(api.POST("/api/v1/shipments", { body })));

export const useAddShipmentItem = () =>
  useWrite((v: { shipmentId: string; body: Schemas["ShipmentItemIn"] }) =>
    unwrap(
      api.POST("/api/v1/shipments/{shipment_id}/items", {
        params: { path: { shipment_id: v.shipmentId } },
        body: v.body,
      }),
    ),
  );

export const useRecordPortionCheck = () =>
  useWrite((body: Schemas["PortionCheckIn"]) => unwrap(api.POST("/api/v1/portion-checks", { body })));

export const useDispatchShipment = () =>
  useWrite((shipmentId: string) =>
    unwrap(api.POST("/api/v1/shipments/{shipment_id}/dispatch", { params: { path: { shipment_id: shipmentId } } })),
  );
