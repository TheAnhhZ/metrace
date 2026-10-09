<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# API

The full contract is OpenAPI: [`packages/api-client/openapi.json`](../packages/api-client/openapi.json)
(`make openapi` regenerates it). The web app, the CLI and the sensor simulator
all use this same API through the gateway at `http://localhost:9080/api/v1`.

## Authentication

Bearer access tokens from Keycloak realm `metrace` (issuer
`http://localhost:9080/auth/realms/metrace`, audience `metrace-api`). The gateway
verifies the token (JWKS) and the API verifies it again. Request
`scope=openid organization` so customer tokens carry their organization.

| Client | Flow | Used by |
|---|---|---|
| `metrace-web` | Authorization code + PKCE | Web app |
| `metrace-cli` | Device authorization grant | `metrace` CLI (staff only) |
| `sensor-gateway` | Client credentials (claim `asset_codes`) | Sensor simulator |
| `metrace-test` | Password grant | CI only, exists only with `KC_OVERLAYS=test` |

## Authorization

Default deny. Every operation belongs to exactly one audience, enforced by a
test that calls every OpenAPI operation with the wrong roles:

| Prefix | Audience |
|---|---|
| `/api/v1/portal/*` | `customer_staff`, scoped to the organizations in the token |
| `/api/v1/assets/{code}/readings` | `sensor` (machine identity) |
| everything else | internal staff roles; some steps need a specific role (see [poka-yoke-rules.md](poka-yoke-rules.md)) |

Another organization's resource answers `404`, never `403`, so its existence is not revealed.

## Errors

```json
{"error": {"code": "P3_MISSING_FORM_3", "rule": "P3", "message": "...",
           "details": {"violations": [...], "warnings": [...]}, "request_id": "..."}}
```

`422` = Poka-yoke block or validation, `401/403` = auth, `404` = not found or not
yours, `409` = state conflict, `503` = a dependency is down. Reason codes are
listed in `services/api/app/core/reason_codes.py`; the web app maps each to a
Vietnamese message.

## Main resources

| Area | Endpoints |
|---|---|
| Identity | `GET /whoami` (includes `server_now`) |
| Master data (read only) | `/suppliers`, `/ingredients`, `/dishes`, `/lots`, `/delivery-points`, `/assets`, `/menus`, `/rule-thresholds` |
| Kitchen | `/receivings`, `/batches` (+`/inputs`, `/finish`), `/samples` (+`/seal.svg`, `/discard`), `/portion-checks`, `/shipments` (+`/items`, `/dispatch`), `/meal-services/{date}/{slot}/status` |
| Traceability | `GET /lineage/{type}/{id or code}?direction=forward\|backward\|both` |
| Incidents | `/complaints`, `/complaints/cluster-suggestions`, `/incidents` (+`/confirm-suspects`, `/close-requests`, `/report-draft`, `/report`, `/report/approve`), `/close-requests/{id}/approve` |
| Customer portal | `/portal/deliveries`, `/portal/delivery-points`, `/portal/complaints`, `/portal/notices` (+`/acknowledge`), `/portal/files` |
| Cold chain | `POST /assets/{code}/readings` (sensor), `/coldchain/alerts`, `/coldchain/assets/{code}/readings` |
| Evidence | `/audit/head`, `/audit/verify?anchor_seq=&anchor_hash=`, `/forms/2/{batch_id}.pdf`, `POST /recall-drills` |
| Files | `/files` (company), `/portal/files` (customer) — JPEG/PNG/PDF, streamed through the API only |
