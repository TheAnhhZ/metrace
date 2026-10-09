// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type ColdChainAlert, plainNumber } from "@metrace/api-client";
import { useState } from "react";
import { Link } from "react-router";
import { useAcknowledgeAlert, useColdChainAlerts } from "../../api/coldchain-audit-api";
import { useWhoAmI } from "../../api/read-queries";
import { canDo } from "../../auth/roles";
import { currentSession } from "../../auth/keycloak-session";
import { Badge, Button, Field, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { formatDateTime } from "../../lib/server-clock";
import { NODE_TYPE_LABELS_VI } from "../../lib/labels-vi";
import { TemperatureSparkline } from "./temperature-sparkline";

function AlertDetail({ alert }: { alert: ColdChainAlert }) {
  const ack = useAcknowledgeAlert();
  const [note, setNote] = useState("");
  const mayAck = canDo(currentSession().roles, "acknowledgeAlert");
  return (
    <div className="space-y-3 rounded-xl bg-white p-3 text-slate-900">
      <TemperatureSparkline assetCode={alert.asset_code} />
      <div>
        <h3 className="text-lg font-bold">Hàng đang để trong {alert.asset_name}</h3>
        {alert.nodes.length === 0 ? (
          <p className="text-base text-slate-600">Không có lô nguyên liệu hoặc mẻ nào gắn với thiết bị này.</p>
        ) : (
          <ul className="space-y-1">
            {alert.nodes.map((n) => (
              <li key={`${n.type}:${n.id}`} className="flex flex-wrap items-center gap-2 text-lg">
                <Badge>{NODE_TYPE_LABELS_VI[n.type] ?? n.type}</Badge>
                <Link to={`/ops/trace?type=${n.type}&ref=${n.id}&direction=both`} className="font-semibold underline">
                  {n.label}
                </Link>
                {n.locked && <Badge tone="red">Đang bị khóa</Badge>}
              </li>
            ))}
          </ul>
        )}
        {alert.samples.length > 0 && <p className="mt-2 text-lg">Mẫu lưu trong thiết bị: {alert.samples.join(", ")}</p>}
      </div>
      {mayAck ? (
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-64 flex-1">
            <Field label="Ghi chú xử lý (đã kiểm tra, di chuyển hàng, sửa tủ...)">
              <input className={inputClass} value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />
            </Field>
          </div>
          <Button busy={ack.isPending} onClick={() => ack.mutate({ alertId: alert.id, note })}>
            Xác nhận đã xử lý
          </Button>
        </div>
      ) : (
        <p className="text-base text-slate-700">Chỉ QA được xác nhận đã xử lý cảnh báo.</p>
      )}
      <ViolationBanner error={ack.error} />
    </div>
  );
}

/**
 * Red banner under the header of every /ops page while any cold-chain alert is open (polled every
 * 10 s by the query). Collapsed by default so it never hides the screen the user is working on.
 */
export function ColdChainAlertBanner() {
  const alerts = useColdChainAlerts();
  const whoami = useWhoAmI();
  const [open, setOpen] = useState<string>();
  if (!alerts.data || alerts.data.length === 0) return null;
  const tz = whoami.data?.business_tz ?? "Asia/Ho_Chi_Minh";

  return (
    <section role="alert" aria-label="Cảnh báo kho lạnh" className="border-t-4 border-red-700 bg-red-600 text-white">
      <div className="mx-auto max-w-7xl space-y-2 px-4 py-2">
        {alerts.data.map((a) => {
          const expanded = open === a.id;
          return (
            <div key={a.id}>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <strong className="text-lg">Cảnh báo kho lạnh: {a.asset_name}</strong>
                <span className="text-lg">
                  Cao nhất {plainNumber(a.max_temp_c)} °C{a.max_c !== null && <> (tối đa cho phép {plainNumber(a.max_c)} °C)</>}, từ {formatDateTime(a.opened_at, tz)}
                </span>
                <button
                  type="button"
                  aria-expanded={expanded}
                  onClick={() => setOpen(expanded ? undefined : a.id)}
                  className="ml-auto min-h-11 rounded-lg bg-white px-4 text-base font-semibold text-red-800 hover:bg-red-50"
                >
                  {expanded ? "Thu gọn" : "Xem chi tiết"}
                </button>
              </div>
              {expanded && (
                <div className="mt-2 max-h-[60vh] overflow-y-auto">
                  <AlertDetail alert={a} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
