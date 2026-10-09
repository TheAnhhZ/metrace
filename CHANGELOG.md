<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Repository skeleton: Apache-2.0, REUSE metadata, AUTHORS, CI (ruff, reuse lint, gitleaks, unit tests).
- `make init` generates local secrets into `.env`; compose refuses to start without it.
- Keycloak 26.8 image built from the upstream distribution on an OSI base, admin/account consoles disabled.
- Realm `metrace`: roles, clients (web PKCE, CLI device flow, sensor client credentials), customer organizations.
- APISIX standalone gateway: `/auth` allowlist, `/api` JWT verification (JWKS), per-token rate limits.
- API: JWT re-verification, `GET /api/v1/whoami`.
- Flowable 8 REST client: idempotent deploy, idempotent start by business key, external-worker jobs, tasks.
- Compose stack with SeaweedFS (S3), one-shot `migrate` (Alembic + bucket), outbox `worker`, static `web`.
- Common error envelope with reason codes and request id; default-deny routers (internal, portal, sensor)
  enforced by a test that walks every route.
- Tamper-evident audit hash chain with anchor verification; runtime DB role cannot UPDATE/DELETE it.
- Transactional outbox and worker loop (claim, handle outside the transaction, mark; backoff; failure cap),
  heartbeat healthcheck, reconciler loop, idempotent BPMN deployment.
- File upload/download through the API only: magic-byte allow-list (JPEG, PNG, PDF), size cap,
  content-addressed storage, ownership per customer organization (other org gets 404).
- `scripts/smoke-core.sh` and a compose-smoke CI workflow (every PR, nightly, fresh volumes).
