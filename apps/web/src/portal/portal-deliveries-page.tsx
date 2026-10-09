// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { PortalDelivery } from "@metrace/api-client";
import { Link } from "react-router";
import { usePortalDeliveries } from "../api/portal-api";
import { QueryBoundary } from "../components/query-boundary";
import { Badge, Card, PageTitle } from "../components/ui-primitives";
import { PORTAL_SHIPMENT_STATUS_LABELS_VI, mealSlotLabel } from "../lib/labels-vi";

function DeliveryCard({ delivery }: { delivery: PortalDelivery }) {
  const tone = delivery.status === "held" ? "red" : delivery.status === "delivered" ? "green" : delivery.status === "dispatched" ? "blue" : "yellow";
  const complain = `/portal/complaints?date=${delivery.service_date}&slot=${delivery.meal_slot}&point=${encodeURIComponent(delivery.delivery_point)}`;
  return (
    <Card
      title={
        <>
          {delivery.service_date} - {mealSlotLabel(delivery.meal_slot)}
        </>
      }
      actions={<Badge tone={tone}>{PORTAL_SHIPMENT_STATUS_LABELS_VI[delivery.status] ?? delivery.status}</Badge>}
    >
      <p className="mb-2 text-lg text-slate-700">{delivery.delivery_point}</p>
      <ul className="divide-y divide-slate-200">
        {delivery.items.map((item) => (
          <li key={item.batch_code} className="flex flex-wrap items-center justify-between gap-2 py-2 text-lg">
            <span>
              <span className="font-semibold">{item.dish}</span> - {item.portions} suất
            </span>
            {item.sample_sealed ? <Badge tone="green">Có mẫu lưu</Badge> : <Badge>Chưa có mẫu lưu</Badge>}
          </li>
        ))}
      </ul>
      <Link to={complain} className="mt-3 flex min-h-12 items-center justify-center rounded-lg border border-slate-400 bg-white px-5 text-lg font-semibold hover:bg-slate-50">
        Phản ánh về chuyến này
      </Link>
    </Card>
  );
}

/** What was delivered to the customer's own sites in the last few days. */
export function PortalDeliveriesPage() {
  const deliveries = usePortalDeliveries(3);
  return (
    <>
      <PageTitle hint="Suất ăn giao tới đơn vị của bạn trong 3 ngày gần nhất.">Giao hàng</PageTitle>
      <QueryBoundary query={deliveries}>
        {(list) =>
          list.length === 0 ? (
            <p className="p-4 text-lg text-slate-600">Chưa có chuyến giao nào trong 3 ngày qua.</p>
          ) : (
            <div className="space-y-4">
              {list.map((d) => (
                <DeliveryCard key={d.id} delivery={d} />
              ))}
            </div>
          )
        }
      </QueryBoundary>
    </>
  );
}
