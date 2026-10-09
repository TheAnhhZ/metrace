// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { ApiError } from "@metrace/api-client";
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { AppRoutes } from "./app-routes";
import { forceLogin, initSession } from "./auth/keycloak-session";
import "./index.css";

/** A 401 from the API means the token was rejected: log in again instead of showing a dead screen. */
function onApiError(error: unknown): void {
  if (error instanceof ApiError && error.status === 401) void forceLogin();
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: onApiError }),
  mutationCache: new MutationCache({ onError: onApiError }),
  defaultOptions: {
    queries: {
      // A 4xx answer will not change by asking again; transient failures get two retries.
      retry: (failures, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && failures < 2,
      refetchOnWindowFocus: true,
    },
  },
});

const root = createRoot(document.getElementById("root") as HTMLElement);

function StartupError() {
  return (
    <main className="mx-auto mt-24 max-w-xl space-y-4 rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-slate-200">
      <h1 className="text-3xl font-bold">Không đăng nhập được</h1>
      <p className="text-lg text-slate-700">
        Không kết nối được dịch vụ đăng nhập. Kiểm tra mạng rồi tải lại trang.
      </p>
      <button
        type="button"
        className="min-h-12 rounded-lg bg-blue-700 px-5 text-lg font-semibold text-white"
        onClick={() => window.location.reload()}
      >
        Tải lại trang
      </button>
    </main>
  );
}

// Keycloak must finish its redirect/PKCE handshake before React renders (and only once, so not inside an effect).
initSession().then(
  () =>
    root.render(
      <StrictMode>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </QueryClientProvider>
      </StrictMode>,
    ),
  (error: unknown) => {
    console.error("login failed", error);
    root.render(<StartupError />);
  },
);
