<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# API

The full contract is OpenAPI: [`packages/api-client/openapi.json`](../packages/api-client/openapi.json)
(`make openapi` regenerates it). The web app, the CLI and the sensor simulator
all use this same API through the gateway at `http://localhost:9080/api/v1`.
Paths below are relative to `/api/v1`.

## Authentication

Bearer access tokens from Keycloak realm `metrace` (issuer
`http://localhost:9080/auth/realms/metrace`, audience `metrace-api`). The gateway
verifies the token (JWKS) and the API verifies it again (signature, issuer,
audience, expiry). Request `scope=openid organization` so customer tokens carry their organization.

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
| `/api/v1/assets/{asset_code}/readings` | `sensor`, only for the assets listed in its `asset_codes` claim |
| `/api/v1/whoami` | Any valid token |
| everything else | internal staff roles; some steps need a specific role (see [poka-yoke-rules.md](poka-yoke-rules.md#who-may-do-what)) |

Another organization's resource answers `404`, never `403`, so its existence is not revealed.

## Errors

```json
{"error": {"code": "P3_MISSING_FORM_3", "rule": "P3", "message": "...",
           "details": {"violations": [...], "warnings": [...]}, "request_id": "..."}}
```

| Status | Meaning |
|---|---|
| `422` | Poka-yoke block (`rule` is set) or request validation (`details.errors`) |
| `401` / `403` | Missing or invalid token / missing role |
| `404` | Not found, or not yours |
| `409` | State conflict, for example a close request is already pending |
| `413` / `415` | Upload larger than 10 MiB / file type not allowed |
| `429` | Gateway rate limit reached (per token, per minute) |
| `503` | A dependency is down |

Reason codes are listed in `services/api/app/core/reason_codes.py`; the web app
maps each one to a Vietnamese message.

## Main resources

| Area | Endpoints |
|---|---|
| Identity | `GET /whoami` (roles, organizations, `server_now`) |
| Master data (read only) | `GET /suppliers`, `/ingredients`, `/dishes`, `/lots`, `/delivery-points`, `/assets`, `/menus`, `/rule-thresholds` |
| Kitchen | `POST /receivings`; `/batches` (`POST`, `GET`; `/{batch_id}/inputs` `POST`, `GET`; `/{batch_id}/finish`); `/samples` (`POST`, `GET`; `/{sample_id}/seal.svg`, `/{sample_id}/discard`); `POST /portion-checks`; `/shipments` (`POST`, `GET` with live `blockers`; `/{shipment_id}/items`, `/{shipment_id}/dispatch`); `GET /meal-services/{day}/{meal_slot}/status` |
| Traceability | `GET /lineage/{node_type}/{ref}?direction=forward\|backward\|both&max_depth=1..12` (`node_type`: `supplier`, `lot`, `batch`, `shipment`, `delivery_point`, `asset`) |
| Incidents | `POST`, `GET /complaints`; `GET /complaints/cluster-suggestions`; `POST`, `GET /incidents`; `GET /incidents/{incident_id}`; `POST /incidents/{incident_id}/confirm-suspects`; `POST /incidents/{incident_id}/close-requests`; `POST /incidents/{incident_id}/report-draft` (`202`, drafted by the worker); `PUT /incidents/{incident_id}/report`; `POST /incidents/{incident_id}/report/approve`; `POST /close-requests/{request_id}/approve`; `POST /close-requests/{request_id}/reject` |
| Customer portal | `GET`, `POST /portal/complaints`; `GET /portal/deliveries`; `GET /portal/delivery-points`; `GET /portal/notices`; `POST /portal/notices/{notice_id}/acknowledge` |
| Cold chain | `POST /assets/{asset_code}/readings` (sensor); `GET /coldchain/alerts`; `POST /coldchain/alerts/{alert_id}/acknowledge` (qa); `GET /coldchain/assets/{asset_code}/readings` |
| Evidence | `GET /audit/head`; `GET /audit/verify?anchor_seq=&anchor_hash=` (qa, director, approver); `GET /forms/2/{batch_id}.pdf` (Mẫu 2); `POST /recall-drills` (qa, director) |
| Files | `POST /files`, `GET /files/{file_id}` (company); `POST /portal/files`, `GET /portal/files/{file_id}` (customer). JPEG, PNG or PDF, checked by content (magic bytes), max 10 MiB, streamed through the API only |

`POST /recall-drills` is a dry run: it previews the lock inside a savepoint that
is rolled back, so nothing is locked and no notice is sent. The drill itself is
written to the audit chain.
