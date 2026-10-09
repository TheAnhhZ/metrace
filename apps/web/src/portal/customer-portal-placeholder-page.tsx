// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { Badge, Card, PageTitle } from "../components/ui-primitives";
import { useBusinessClock } from "../layout/business-clock";

/** Placeholder until the customer portal screens (complaints, delivery history) are built. */
export function CustomerPortalPlaceholderPage() {
  const { whoami } = useBusinessClock();
  return (
    <>
      <PageTitle hint="Màn hình dành cho nhân viên đơn vị đặt suất ăn.">Cổng khách hàng</PageTitle>
      <Card title="Đơn vị của bạn">
        {whoami.organizations.length === 0 ? (
          <p className="text-lg text-slate-700">Tài khoản chưa được gắn với đơn vị nào.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {whoami.organizations.map((org) => (
              <Badge key={org} tone="blue">
                {org}
              </Badge>
            ))}
          </div>
        )}
        <p className="mt-4 text-lg text-slate-600">Các chức năng phản ánh chất lượng và tra cứu giao hàng sẽ sớm có mặt.</p>
      </Card>
    </>
  );
}
