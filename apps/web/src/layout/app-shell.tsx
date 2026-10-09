// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { NavLink, Outlet } from "react-router";
import { useWhoAmI } from "../api/read-queries";
import { type AppArea, canDo, roleLabelsVi } from "../auth/roles";
import { currentSession, logout } from "../auth/keycloak-session";
import { Badge, Button } from "../components/ui-primitives";
import { QueryBoundary } from "../components/query-boundary";
import { ColdChainAlertBanner } from "../ops/coldchain/coldchain-alert-banner";
import { PortalNoticeBanner } from "../portal/portal-notice-banner";
import { BusinessClockProvider } from "./business-clock";

interface NavItem {
  to: string;
  label: string;
  /** Match only the exact path (for index routes). */
  end?: boolean;
  /** Hide the link from roles that may not use the screen. */
  needs?: "viewAudit";
}

const OPS_NAV: readonly NavItem[] = [
  { to: "/ops/receiving", label: "Nhận hàng" },
  { to: "/ops/cooking", label: "Chế biến" },
  { to: "/ops/samples", label: "Lưu mẫu" },
  { to: "/ops/dispatch", label: "Xuất hàng" },
  { to: "/ops/complaints", label: "Phản ánh" },
  { to: "/ops/incidents", label: "Sự cố" },
  { to: "/ops/trace", label: "Truy vết" },
  { to: "/ops/audit", label: "Kiểm toán", needs: "viewAudit" },
];

const PORTAL_NAV: readonly NavItem[] = [
  { to: "/portal", label: "Giao hàng", end: true },
  { to: "/portal/complaints", label: "Phản ánh" },
  { to: "/portal/notices", label: "Thông báo" },
];

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return `flex min-h-12 items-center rounded-lg px-3 text-base font-semibold sm:px-5 sm:text-lg ${
    isActive ? "bg-blue-700 text-white" : "text-slate-800 hover:bg-slate-200"
  }`;
}

/** Header (brand, screen navigation, who is signed in, logout) around the routed page. */
export function AppShell({ area }: { area: AppArea }) {
  const whoami = useWhoAmI();
  const { username, roles } = currentSession();
  const nav = (area === "ops" ? OPS_NAV : PORTAL_NAV).filter((item) => !item.needs || canDo(roles, item.needs));

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-slate-300 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2">
          <span className="text-2xl font-extrabold tracking-tight text-blue-800">metrace</span>
          <nav aria-label="Màn hình chính" className="flex flex-wrap gap-1">
            {nav.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={navLinkClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <span className="text-lg font-semibold">{username}</span>
            {roleLabelsVi(roles).map((label) => (
              <Badge key={label} tone="blue">
                {label}
              </Badge>
            ))}
            <Button variant="secondary" onClick={() => void logout()}>
              Đăng xuất
            </Button>
          </div>
        </div>
        {area === "ops" ? <ColdChainAlertBanner /> : <PortalNoticeBanner />}
      </header>
      <main className={`mx-auto p-3 sm:p-4 ${area === "portal" ? "max-w-3xl" : "max-w-7xl"}`}>
        <QueryBoundary query={whoami}>
          {(data) => (
            <BusinessClockProvider whoami={data} offsetMs={data.offsetMs}>
              <Outlet />
            </BusinessClockProvider>
          )}
        </QueryBoundary>
      </main>
    </div>
  );
}
