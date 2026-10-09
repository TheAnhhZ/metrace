# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Web app image. Build context = repository root:
#   docker build -f infra/web/Dockerfile .
# (compose: build: { context: ., dockerfile: infra/web/Dockerfile })

# ---- build: npm workspaces at the repo root, then the Vite production build ----
FROM node:24-bookworm-slim AS build
WORKDIR /repo

# Manifests first so the dependency layer is cached until a dependency changes.
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/api-client/package.json packages/api-client/package.json
RUN npm ci --no-audit --no-fund

COPY apps/web apps/web
COPY packages/api-client packages/api-client
RUN npm run build

# ---- serve: static files behind the gateway (same origin, SPA fallback in nginx.conf) ----
FROM nginx:1.29-bookworm
COPY infra/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/apps/web/dist /usr/share/nginx/html
