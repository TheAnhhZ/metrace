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
- Keycloak 26.8 (official image) with admin/account consoles disabled at build time.
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
- Domain model (migrations 0002–0003): suppliers and certificates, receiving (Mẫu 1), lots, dishes,
  menus, cooking batches (Mẫu 2) with lot or intermediate-batch inputs, portion checks (Mẫu 3),
  retained samples, shipments, complaints, incidents, per-incident locks, four-eyes close requests,
  recall notices, Poka-yoke thresholds with their basis.
- `lineage_edge` view and `GET /api/v1/lineage/{type}/{id}?direction=forward|backward|both`
  (recursive CTE, cycle guard, depth/node caps, `truncated` flag, lock state, portions per point).
- Read-only master data endpoints (suppliers with certificate state, ingredients, dishes,
  delivery points, assets, menus, thresholds).
- One-shot `seed`: synthetic DEMO master data and two service days relative to now.
- `docs/domain-model.md`, `make openapi`.

- Poka-yoke rules P1–P4 as pure functions with thresholds that carry their basis
  (law/guidance/field/internal); every block answers 422 with all violations and is logged.
- Kitchen flow API: receiving (Mẫu 1), cooking batches with inputs and finish (Mẫu 2), retained
  samples with QR seal, portion checks (Mẫu 3), shipments with live blockers, dispatch,
  meal-service checklist (state machine in the API, no BPMN).
- Lock guards (one advisory lock, lineage-based, fail closed) wired into inputs, finish, add-item,
  dispatch and sample discard.
- `make demo-reset`: fresh "today" in about 10 seconds; seeded receivings carry delivery notes.
- `docs/poka-yoke-rules.md`.
- Incidents: complaints (internal channel), #3 cluster suggestions (SQL, QA confirms), incidents,
  confirm suspects => per-incident locks applied in one transaction (pending shipments held,
  fail closed on incomplete lineage), four-eyes close (approver role, different person),
  each incident releases only its own locks.
- Worker: BPMN `incident-recall` (triage SLA timer escalates to the director), idempotent process
  start by business key, recall notices per delivery point carrying the audit anchor,
  reconcilers for missing processes, escalation flags and missed notices.
- `outbreak` seed scenario; `GET /api/v1/lots`.
- Customer portal API (`/api/v1/portal/*`): deliveries, complaints (create/list), recall notices
  (list/acknowledge), scoped by the organizations in the token; references to another
  organization's delivery point or file answer 404.
- P6: complaint answer deadline from the customer profile (`sla_hours`), worker sweep flags
  overdue complaints (no BPMN).
- Customer differences (school vs factory) are profile data, not code branches.
- CLI `metrace` (device-flow login, staff only, `whoami`, `trace`, `shipments list`, `incidents list`);
  lineage accepts business codes as well as UUIDs.
- Cold chain: sensor gateway machine identity may only report its own assets (claim), device clock
  skew is rejected, N consecutive out-of-band readings open one alert per asset and start the
  `cold-chain-alert` process (QA check, director escalation); alert shows lots and retained samples
  in that fridge. `tools/sensor-simulator` (normal/drift/breach).
- #6 audit verification: `GET /api/v1/audit/verify?anchor_seq=&anchor_hash=` and `GET /api/v1/audit/head`.

### Fixed
- Receiving and incident codes no longer collide under concurrent requests.

### Security
- The CI-only `metrace-test` client only exists when `KC_OVERLAYS=test`; demos remove it.
