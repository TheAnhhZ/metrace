// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { VerifyResult } from "@metrace/api-client";
import { useState } from "react";
import { useAuditHead, useVerifyAudit } from "../../api/coldchain-audit-api";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { AuditAnchor } from "../../components/audit-anchor";
import { QueryBoundary } from "../../components/query-boundary";
import { Button, Card, Field, PageTitle, RoleNotice, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { parseAnchor } from "../../lib/audit-anchor";
import { AUDIT_FAILURE_REASONS_VI } from "../../lib/labels-vi";

function VerifyResultPanel({ result }: { result: VerifyResult }) {
  if (result.ok) {
    return (
      <div role="status" className="rounded-xl border-2 border-green-600 bg-green-50 p-4 text-green-900">
        <h3 className="text-2xl font-bold">Nhật ký nguyên vẹn</h3>
        <p className="text-lg">
          Đã kiểm tra {result.checked} bản ghi liên tiếp, không có sai lệch.
          {result.head_seq !== null && <> Bản ghi cuối: #{result.head_seq}.</>}
        </p>
      </div>
    );
  }
  return (
    <div role="alert" className="rounded-xl border-2 border-red-600 bg-red-50 p-4 text-red-900">
      <h3 className="text-2xl font-bold">Phát hiện sai lệch tại bản ghi #{result.first_bad_seq}</h3>
      <p className="text-lg">{AUDIT_FAILURE_REASONS_VI[result.reason ?? ""] ?? "Chuỗi băm không khớp."}</p>
      <p className="mt-1 text-base">Đã kiểm tra {result.checked} bản ghi đầu tiên trước khi gặp sai lệch.</p>
    </div>
  );
}

/** Audit chain: show the head, check the chain, and check it against a code printed outside the database. */
export function AuditPage() {
  const head = useAuditHead();
  const verify = useVerifyAudit();
  const [text, setText] = useState("");
  const [localError, setLocalError] = useState<string>();
  const allowed = canDo(currentSession().roles, "viewAudit");

  if (!allowed) return <RoleNotice>Chỉ QA, giám đốc và người duyệt được xem nhật ký kiểm toán.</RoleNotice>;

  function checkAnchor() {
    const anchor = parseAnchor(text);
    if (!anchor) return setLocalError("Mã đối chiếu không đọc được. Dán đủ số thứ tự và 64 ký tự mã băm (nút Sao chép ở thông báo thu hồi).");
    setLocalError(undefined);
    verify.mutate(anchor);
  }

  return (
    <>
      <PageTitle hint="Nhật ký kiểm toán là chuỗi băm: sửa hoặc xóa một bản ghi cũ sẽ làm hỏng mọi bản ghi sau nó.">Kiểm toán</PageTitle>
      <div className="space-y-4">
        <Card title="Đầu chuỗi hiện tại">
          <QueryBoundary query={head}>
            {(h) => (h.seq !== null && h.hash !== null ? <AuditAnchor anchor={{ seq: h.seq, hash: h.hash }} /> : <p className="text-lg text-slate-600">Nhật ký còn trống.</p>)}
          </QueryBoundary>
        </Card>
        <Card title="Kiểm tra chuỗi">
          <div className="space-y-3">
            <Button variant="secondary" busy={verify.isPending} onClick={() => { setLocalError(undefined); verify.mutate(undefined); }}>
              Kiểm tra toàn bộ chuỗi
            </Button>
            <Field label="Hoặc đối chiếu với mã đã in ngoài hệ thống (thông báo thu hồi, báo cáo PDF)" hint="Dán dạng 'số:mã băm' hoặc '#số mã băm'. Hệ thống chứng minh lịch sử đến mốc đó chưa bị viết lại.">
              <input className={`${inputClass} font-mono`} value={text} onChange={(e) => setText(e.target.value)} placeholder="189:44aebcae..." />
            </Field>
            <Button busy={verify.isPending} disabled={text.trim() === ""} onClick={checkAnchor}>
              Đối chiếu mã
            </Button>
            {localError && <p role="alert" className="text-lg font-semibold text-red-800">{localError}</p>}
            {verify.data && <VerifyResultPanel result={verify.data} />}
            <ViolationBanner error={verify.error} />
          </div>
        </Card>
      </div>
    </>
  );
}
