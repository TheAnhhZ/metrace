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
