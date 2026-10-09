<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# Architecture

metrace is the digital operating system of **one** catering company that cooks
meals for school canteens and factories. The central entity is the
**cooking batch**: every batch knows which ingredient lots went in and which
delivery points received it, so an incident can be traced back to suppliers and
the affected food can be locked everywhere within seconds.

## Tiers

| Tier | What | Components |
|---|---|---|
| 1. Headless core (platform) | Generic services, no business logic | Keycloak (SSO), Apache APISIX (gateway), PostgreSQL + SeaweedFS (data), Flowable REST (workflow), plus generic API building blocks: audit hash chain, transactional outbox, file service |
| 2. Domain | Catering business rules | metrace API (FastAPI) + outbox worker |
| 3. Clients | People and machines | One web SPA (`/ops/*` for staff, `/portal/*` for customers), CLI, sensor simulator |

Tier 2 talks to Tier 1 only through documented interfaces: OIDC/JWKS
(Keycloak), SQL (PostgreSQL), S3 (SeaweedFS) and REST (Flowable). Clients
reach the system **only** through the gateway.

## Data flow

```
SPA (/ops, /portal) ─┐
CLI (device flow) ───┼─► APISIX 127.0.0.1:9080 ─┬─ /auth/* (allowlist) ─► Keycloak ─► PG db keycloak
sensor (client cred) ┘   OIDC/JWKS, rate limit  ├─ /api/*  ─► metrace API ─► PG db metrace, SeaweedFS
                         per token, request id  └─ /       ─► web (static SPA)
                                                             │ outbox_event (same transaction)
                                                             ▼
                                         worker (claim → HTTP → mark) ─► Flowable REST ─► PG db flowable
```

- **One public origin.** Keycloak is served under `/auth` behind the gateway,
  so every token carries the same issuer (`http://localhost:9080/auth/realms/metrace`)
  whether it was obtained by a browser, the CLI or a test. Services inside
  docker fetch keys from `http://keycloak:8080/auth/...` (back-channel).
- **Gateway allowlist.** Only login, token, device and discovery endpoints of
  realm `metrace` are routed. Admin, master realm and account console paths
  have no route (404). The admin and account consoles are also disabled in
  the Keycloak build (`infra/keycloak/Dockerfile`: the official
  `quay.io/keycloak` image with build options).
- **Zero trust.** APISIX verifies the JWT, and the API verifies it again
  (signature via JWKS, issuer, audience `metrace-api`, expiry). The API never
  trusts identity headers added by the gateway. Every route denies by default
  and requires an internal role, `customer_staff` or the `sensor` role
  (`/api/v1/whoami` accepts any valid token).
- **Synchronous business actions.** The API changes state inside one
  PostgreSQL transaction and writes an outbox row in the same transaction.
  Only the worker calls Flowable, outside any database transaction.
- **Workflow scope.** Flowable runs only processes that need timers and human
  steps: incident recall and cold-chain alerts. The kitchen flow is a state
  machine in the API.

## Identity model

- Realm roles (internal): `qa`, `procurement`, `chef`, `driver`, `cskh`,
  `director`, `approver`. Customer role: `customer_staff`. Machine: `sensor`.
- Customers are Keycloak **Organizations** keyed by alias (`truong-a`,
  `truong-b`, `truong-c`, `nha-may-x`). Tokens carry an `organization` claim
  when the client requests `scope=openid organization`.
- Clients: `metrace-web` (public, PKCE), `metrace-cli` (public, device flow),
  `sensor-gateway` (client credentials), `metrace-api` (audience). The client
  `metrace-test` (direct access grants) exists only when the `test` overlay is
  applied, never in a demo.

## Time

The database stores `timestamptz` in UTC. Business dates (service day, meal
time) are computed in `BUSINESS_TZ=Asia/Ho_Chi_Minh`. The API returns
`server_now` so countdowns in the UI do not depend on the client clock.

## Machines and evidence

- **Sensors** use their own machine identity (`sensor-gateway`, client
  credentials) with a claim listing the assets they may report for, through a
  separate gateway route with its own rate-limit bucket.
- **Audit chain:** every business change appends a hash-chained audit event in
  the same transaction. The chain head (seq, hash) is printed outside the
  database (recall notices, PDF footers, drill results) and can be verified
  against it later. This is tamper-evidence, not a digital signature.

## Tier boundary

Tier 2 reaches PostgreSQL, SeaweedFS and Flowable directly on the internal
docker network (PostgreSQL cannot sit behind an HTTP gateway). If all Tier 1
access had to go through the gateway, Flowable and S3 traffic would move to
internal APISIX routes with a service token.
