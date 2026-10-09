// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { ApiError, messageForCode } from "@metrace/api-client";
import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Button } from "./ui-primitives";

/** Loading / error / content switch for a query, all in Vietnamese. */
export function QueryBoundary<T>(props: { query: UseQueryResult<T>; children: (data: T) => ReactNode }) {
  const { query } = props;
  if (query.isPending) {
    return <p className="p-4 text-lg text-slate-600">Đang tải dữ liệu...</p>;
  }
  if (query.isError) {
    const code = query.error instanceof ApiError ? query.error.code : "";
    return (
      <div role="alert" className="flex flex-wrap items-center gap-3 rounded-xl bg-red-50 p-4 text-red-900">
        <p className="text-lg">{messageForCode(code)}</p>
        <Button variant="secondary" onClick={() => void query.refetch()}>
          Tải lại
        </Button>
      </div>
    );
  }
  return <>{props.children(query.data)}</>;
}
