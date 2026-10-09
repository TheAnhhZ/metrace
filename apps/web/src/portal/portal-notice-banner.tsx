// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { Link } from "react-router";
import { usePortalNotices } from "../api/portal-api";

/** Red strip under the portal header while any hold/recall notice has not been acknowledged. */
export function PortalNoticeBanner() {
  const notices = usePortalNotices();
  const pending = notices.data?.filter((n) => n.acknowledged_at === null).length ?? 0;
  if (pending === 0) return null;
  return (
    <section role="alert" className="border-t-4 border-red-700 bg-red-600 text-white">
      <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-3 px-4 py-2">
        <strong className="text-lg">Có {pending} thông báo giữ/thu hồi suất ăn chưa xác nhận</strong>
        <Link to="/portal/notices" className="ml-auto flex min-h-11 items-center rounded-lg bg-white px-4 text-base font-semibold text-red-800">
          Xem ngay
        </Link>
      </div>
    </section>
  );
}
