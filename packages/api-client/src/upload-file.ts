// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type ApiClient, unwrap } from "./client";
import type { FileOut } from "./types";

/** Document types the API accepts (it also sniffs the content, see FILE_TYPE_MISMATCH). */
export const ACCEPTED_DOCUMENT_TYPES = ["image/jpeg", "image/png", "application/pdf"] as const;

/** Upload a delivery document (JPEG/PNG/PDF) as multipart field `file`. */
export function uploadCompanyFile(client: ApiClient, file: File): Promise<FileOut> {
  return unwrap(
    client.POST("/api/v1/files", {
      // The generated schema types the binary part as string; the serializer sends the real File.
      body: { file: file as unknown as string },
      bodySerializer: () => {
        const form = new FormData();
        form.append("file", file);
        return form;
      },
    }),
  );
}
