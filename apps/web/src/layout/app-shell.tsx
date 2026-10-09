// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { NavLink, Outlet } from "react-router";
import { useWhoAmI } from "../api/read-queries";
import { type AppArea, roleLabelsVi } from "../auth/roles";
import { currentSession, logout } from "../auth/keycloak-session";
import { Badge, Button } from "../components/ui-primitives";
import { QueryBoundary } from "../components/query-boundary";
import { BusinessClockProvider } from "./business-clock";

const OPS_NAV = [
  { to: "/ops/receiving", label: "Nhận hàng" },
  { to: "/ops/cooking", label: "Chế biến" },
  { to: "/ops/samples", label: "Lưu mẫu" },
  { to: "/ops/dispatch", label: "Xuất hàng" },
] as const;

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return `flex min-h-12 items-center rounded-lg px-5 text-lg font-semibold ${
    isActive ? "bg-blue-700 text-white" : "text-slate-800 hover:bg-slate-200"
  }`;
}

/** Header (brand, screen navigation, who is signed in, logout) around the routed page. */
export function AppShell({ area }: { area: AppArea }) {
  const whoami = useWhoAmI();
  const { username, roles } = currentSession();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-slate-300 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2">
          <span className="text-2xl font-extrabold tracking-tight text-blue-800">metrace</span>
          {area === "ops" && (
            <nav aria-label="Màn hình chính" className="flex flex-wrap gap-1">
              {OPS_NAV.map((item) => (
                <NavLink key={item.to} to={item.to} className={navLinkClass}>
                  {item.label}
                </NavLink>
              ))}
            </nav>
          )}
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
      </header>
      <main className="mx-auto max-w-7xl p-4">
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
