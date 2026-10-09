// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { ApiError } from "@metrace/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";

/**
 * Mutation that refreshes every cached list afterwards: one write (a lot used up, a sample stored,
 * an incident locked) changes several screens at once, and the data is small.
 */
export function useWrite<TVars, TData>(run: (vars: TVars) => Promise<TData>) {
  const queryClient = useQueryClient();
  return useMutation<TData, ApiError, TVars>({
    mutationFn: run,
    onSuccess: () => queryClient.invalidateQueries(),
  });
}
