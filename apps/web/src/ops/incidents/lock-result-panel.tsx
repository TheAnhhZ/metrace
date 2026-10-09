// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { LockResult } from "@metrace/api-client";
import { AuditAnchor } from "../../components/audit-anchor";

/** What one confirmation of suspects did, measured by the server (it is a single transaction). */
export function LockResultPanel({ result }: { result: LockResult }) {
  const gone = result.already_dispatched.length;
  return (
    <div role="status" className="space-y-2 rounded-xl border-2 border-green-600 bg-green-50 p-4 text-green-900">
      <h3 className="text-2xl font-bold">Khóa trong {result.elapsed_ms} ms</h3>
      <ul className="list-inside list-disc text-lg">
        <li>Đã khóa {result.targets.length} đối tượng (mẻ, lô nguyên liệu, nhà cung cấp).</li>
        <li>Giữ lại {result.held_shipments.length} chuyến giao chưa xuất.</li>
        <li>Thông báo gửi tới {result.delivery_points.length} điểm giao.</li>
      </ul>
      {result.truncated && (
        <p role="alert" className="rounded-lg bg-amber-100 p-3 text-lg font-bold text-amber-900">
          Chuỗi truy xuất sâu hơn giới hạn: đã tạm giữ mọi chuyến chưa xuất từ hôm nay (an toàn trước).
        </p>
      )}
      {gone > 0 && (
        <p role="alert" className="rounded-lg bg-red-100 p-3 text-lg font-bold text-red-900">
          {gone} chuyến đã xuất xe hoặc đã giao: cần thu hồi.
        </p>
      )}
      <AuditAnchor anchor={result.audit_head} />
    </div>
  );
}
