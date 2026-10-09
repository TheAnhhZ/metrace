// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { ACCEPTED_DOCUMENT_TYPES, type FileOut } from "@metrace/api-client";
import { type Dispatch, type SetStateAction, useRef } from "react";
import { useUploadDocument } from "../../api/mutations";
import { ViolationBanner } from "../../components/violation-banner";
import { Button } from "../../components/ui-primitives";

function formatSize(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/** Photo/PDF of the delivery note. Each file is uploaded as soon as it is picked. */
export function DocumentUploader(props: { files: FileOut[]; onChange: Dispatch<SetStateAction<FileOut[]>> }) {
  const upload = useUploadDocument();
  const input = useRef<HTMLInputElement>(null);

  async function onPick(picked: File[]) {
    for (const file of picked) {
      try {
        const uploaded = await upload.mutateAsync(file);
        props.onChange((prev) => [...prev, uploaded]);
      } catch {
        return; // the error is shown by the banner below; stop at the first failed file
      }
    }
  }

  return (
    <div className="space-y-3">
      <input
        ref={input}
        type="file"
        multiple
        accept={ACCEPTED_DOCUMENT_TYPES.join(",")}
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(e) => {
          const picked = Array.from(e.target.files ?? []);
          e.target.value = ""; // allow picking the same file again after a failure
          void onPick(picked);
        }}
      />
      <Button variant="secondary" busy={upload.isPending} onClick={() => input.current?.click()}>
        Chụp ảnh / chọn chứng từ (JPEG, PNG, PDF)
      </Button>
      {props.files.length === 0 ? (
        <p className="text-base text-slate-600">Chưa có chứng từ nào. Cần ít nhất một phiếu giao hàng.</p>
      ) : (
        <ul className="space-y-2">
          {props.files.map((f) => (
            <li key={f.id} className="flex items-center justify-between gap-3 rounded-lg bg-slate-100 p-2 pl-3">
              <span className="text-lg">
                {f.original_name} <span className="text-base text-slate-600">({formatSize(f.size_bytes)})</span>
              </span>
              <Button variant="secondary" onClick={() => props.onChange((prev) => prev.filter((x) => x.id !== f.id))}>
                Bỏ
              </Button>
            </li>
          ))}
        </ul>
      )}
      <ViolationBanner error={upload.error} />
    </div>
  );
}
