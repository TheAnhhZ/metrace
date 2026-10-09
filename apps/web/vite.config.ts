// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vitest/config";

// Dev: the SPA runs on :5173 and proxies /api to the APISIX gateway on :9080.
// keycloak-js talks to the gateway (/auth) directly; Keycloak allows CORS for registered origins.
// Prod: nginx serves the SPA behind the gateway on the same origin, so no proxy is needed.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:9080", changeOrigin: true },
    },
  },
  build: { sourcemap: false },
  test: { environment: "node", include: ["src/**/*.test.{ts,tsx}"] },
});
