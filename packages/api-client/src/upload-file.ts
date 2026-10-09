// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type ApiClient, unwrap } from "./client";
import type { FileOut } from "./types";

/** Document types the API accepts (it also sniffs the content, see FILE_TYPE_MISMATCH). */
export const ACCEPTED_DOCUMENT_TYPES = ["image/jpeg", "image/png", "application/pdf"] as const;

/** The generated schema types the binary part as string; the serializer sends the real File. */
function multipartFile(file: File): FormData {
  const form = new FormData();
  form.append("file", file);
  return form;
}

/** Upload a delivery document (JPEG/PNG/PDF) as multipart field `file`. */
export function uploadCompanyFile(client: ApiClient, file: File): Promise<FileOut> {
  return unwrap(
    client.POST("/api/v1/files", { body: { file: file as unknown as string }, bodySerializer: () => multipartFile(file) }),
  );
}

/** Customer portal upload (e.g. a photo for a complaint); the file belongs to the caller's organization. */
export function uploadCustomerFile(client: ApiClient, file: File): Promise<FileOut> {
  return unwrap(
    client.POST("/api/v1/portal/files", {
      body: { file: file as unknown as string },
      bodySerializer: () => multipartFile(file),
    }),
  );
}
