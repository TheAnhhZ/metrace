// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type ReactElement, Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router";
import { type AppArea, areaForRoles, homePathForRoles } from "./auth/roles";
import { currentSession } from "./auth/keycloak-session";
import { AppShell } from "./layout/app-shell";
import { NoAccessPage } from "./layout/no-access-page";
import { AuditPage } from "./ops/audit/audit-page";
import { BatchBoardPage } from "./ops/cooking/batch-board-page";
import { DispatchPage } from "./ops/dispatch/dispatch-page";
import { ComplaintsPage } from "./ops/incidents/complaints-page";
import { IncidentDetailPage } from "./ops/incidents/incident-detail-page";
import { IncidentsPage } from "./ops/incidents/incidents-page";
import { ReceivingFormPage } from "./ops/receiving/receiving-form-page";
import { SampleLockerPage } from "./ops/samples/sample-locker-page";
import { PortalComplaintsPage } from "./portal/portal-complaints-page";
import { PortalDeliveriesPage } from "./portal/portal-deliveries-page";
import { PortalNoticesPage } from "./portal/portal-notices-page";

// The trace screen pulls in the graph library, so it is loaded on first visit only.
const TracePage = lazy(() => import("./ops/trace/trace-page").then((m) => ({ default: m.TracePage })));

/** `/` and any URL outside the user's area lead to the user's own home screen. */
function GoHome(): ReactElement {
  const home = homePathForRoles(currentSession().roles);
  return home ? <Navigate to={home} replace /> : <NoAccessPage />;
}

/** Only users whose roles belong to `area` get through (internal staff vs customer staff). */
function RequireArea({ area, children }: { area: AppArea; children: ReactElement }): ReactElement {
  return areaForRoles(currentSession().roles) === area ? children : <GoHome />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<GoHome />} />
      <Route
        path="/ops"
        element={
          <RequireArea area="ops">
            <AppShell area="ops" />
          </RequireArea>
        }
      >
        <Route index element={<GoHome />} />
        <Route path="receiving" element={<ReceivingFormPage />} />
        <Route path="cooking" element={<BatchBoardPage />} />
        <Route path="samples" element={<SampleLockerPage />} />
        <Route path="dispatch" element={<DispatchPage />} />
        <Route path="complaints" element={<ComplaintsPage />} />
        <Route path="incidents" element={<IncidentsPage />} />
        <Route path="incidents/:id" element={<IncidentDetailPage />} />
        <Route
          path="trace"
          element={
            <Suspense fallback={<p className="p-4 text-lg text-slate-600">Đang tải màn hình truy vết...</p>}>
              <TracePage />
            </Suspense>
          }
        />
        <Route path="audit" element={<AuditPage />} />
        <Route path="*" element={<Navigate to="/ops/receiving" replace />} />
      </Route>
      <Route
        path="/portal"
        element={
          <RequireArea area="portal">
            <AppShell area="portal" />
          </RequireArea>
        }
      >
        <Route index element={<PortalDeliveriesPage />} />
        <Route path="complaints" element={<PortalComplaintsPage />} />
        <Route path="notices" element={<PortalNoticesPage />} />
        <Route path="*" element={<Navigate to="/portal" replace />} />
      </Route>
      <Route path="*" element={<GoHome />} />
    </Routes>
  );
}
