// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { fetchBlob } from "@metrace/api-client";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getAccessToken } from "../auth/keycloak-session";

/**
 * The seal SVG needs the bearer header, so an <img src> cannot load it directly:
 * fetch it as a blob and show it through an object URL (revoked on unmount).
 */
export function useSealImageUrl(sampleId: string): { url?: string; error: boolean } {
  const blob = useQuery({
    queryKey: ["seal", sampleId],
    queryFn: () => fetchBlob(`/api/v1/samples/${sampleId}/seal.svg`, getAccessToken),
    staleTime: Number.POSITIVE_INFINITY, // the seal code of a sample never changes
  });
  const [url, setUrl] = useState<string>();
  useEffect(() => {
    if (!blob.data) return;
    const objectUrl = URL.createObjectURL(blob.data);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [blob.data]);
  return { url, error: blob.isError };
}
