// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type FileOut, type ReceivingIn, plainNumber } from "@metrace/api-client";
import { useState } from "react";
import { useCreateReceiving } from "../../api/mutations";
import { useIngredients, useThresholds } from "../../api/read-queries";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { QueryBoundary } from "../../components/query-boundary";
import { Button, Card, Field, PageTitle, RoleNotice, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { parseDecimal } from "../../lib/decimal";
import { DocumentUploader } from "./document-uploader";
import { type LineDraft, ReceivingLinesEditor, newLine } from "./receiving-lines-editor";
import { ReceivingResult } from "./receiving-result";
import { SupplierPicker } from "./supplier-picker";

/** Turn the drafts into the API body, or return a Vietnamese message about what is missing. */
function buildRequest(supplierId: string, lines: LineDraft[], rest: Omit<ReceivingIn, "supplier_id" | "lines">) {
  if (!supplierId) return "Chọn nhà cung cấp.";
  const out: ReceivingIn["lines"] = [];
  for (const [i, l] of lines.entries()) {
    const qty = parseDecimal(l.qtyKg);
    if (!l.ingredientId || qty === undefined || qty <= 0) return `Dòng ${i + 1}: chọn nguyên liệu và nhập khối lượng lớn hơn 0.`;
    if (l.tempC.trim() !== "" && parseDecimal(l.tempC) === undefined) return `Dòng ${i + 1}: nhiệt độ không hợp lệ.`;
    out.push({ ingredient_id: l.ingredientId, qty_kg: qty, temp_c: parseDecimal(l.tempC) ?? null });
  }
  return { supplier_id: supplierId, lines: out, ...rest } satisfies ReceivingIn;
}

/** Mẫu 1: goods receipt. The server applies Poka-yoke P1; its answer is shown as-is. */
export function ReceivingFormPage() {
  const ingredients = useIngredients();
  const thresholds = useThresholds();
  const create = useCreateReceiving();
  const [supplierId, setSupplierId] = useState("");
  const [files, setFiles] = useState<FileOut[]>([]);
  const [lines, setLines] = useState<LineDraft[]>([newLine()]);
  const [sensoryOk, setSensoryOk] = useState(true);
  const [quickTest, setQuickTest] = useState("");
  const [note, setNote] = useState("");
  const [formError, setFormError] = useState<string>();
  const allowed = canDo(currentSession().roles, "receive");

  function submit() {
    const request = buildRequest(supplierId, lines, {
      document_file_ids: files.map((f) => f.id),
      sensory_ok: sensoryOk,
      quick_test: quickTest,
      note,
    });
    if (typeof request === "string") return setFormError(request);
    setFormError(undefined);
    create.mutate(request, {
      onSuccess: () => {
        setSupplierId("");
        setFiles([]);
        setLines([newLine()]);
        setSensoryOk(true);
        setQuickTest("");
        setNote("");
      },
    });
  }

  const limits = {
    chilled: plainNumber(thresholds.data?.receiving_chilled_max_c?.value ?? "4"),
    frozen: plainNumber(thresholds.data?.receiving_frozen_max_c?.value ?? "-18"),
  };

  return (
    <>
      <PageTitle hint="Mẫu 1 - kiểm tra chứng từ, nhà cung cấp và nhiệt độ trước khi nhập kho.">Nhận hàng</PageTitle>
      {!allowed && <RoleNotice>Vai trò của bạn chỉ được xem. Nhận hàng do thu mua hoặc QA thực hiện.</RoleNotice>}
      <QueryBoundary query={ingredients}>
        {(ingredientList) => (
          <div className="space-y-4">
            {create.data && (
              <ReceivingResult result={create.data} ingredients={ingredientList} onClose={() => create.reset()} />
            )}
            <Card title="1. Nhà cung cấp">
              <SupplierPicker value={supplierId} onChange={setSupplierId} />
            </Card>
            <Card title="2. Chứng từ giao hàng">
              <DocumentUploader files={files} onChange={setFiles} />
            </Card>
            <Card title="3. Hàng nhận">
              <ReceivingLinesEditor lines={lines} onChange={setLines} ingredients={ingredientList} limits={limits} />
            </Card>
            <Card title="4. Kiểm tra cảm quan">
              <div className="grid items-end gap-3 md:grid-cols-2">
                <label className="flex min-h-12 items-center gap-3 text-lg font-semibold">
                  <input type="checkbox" className="size-6" checked={sensoryOk} onChange={(e) => setSensoryOk(e.target.checked)} />
                  Cảm quan đạt (màu, mùi, bao bì)
                </label>
                <Field label="Test nhanh (nếu có)">
                  <input className={inputClass} value={quickTest} onChange={(e) => setQuickTest(e.target.value)} />
                </Field>
                <div className="md:col-span-2">
                  <Field label="Ghi chú">
                    <input className={inputClass} value={note} onChange={(e) => setNote(e.target.value)} />
                  </Field>
                </div>
              </div>
            </Card>
            {formError && (
              <p role="alert" className="rounded-lg bg-red-50 p-3 text-lg font-semibold text-red-800">
                {formError}
              </p>
            )}
            <ViolationBanner error={create.error} />
            <Button className="w-full md:w-auto" busy={create.isPending} disabled={!allowed} onClick={submit}>
              Xác nhận nhận hàng
            </Button>
          </div>
        )}
      </QueryBoundary>
    </>
  );
}
