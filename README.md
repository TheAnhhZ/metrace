<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# metrace

> Working name. The digital operating system of a catering company that cooks
> meals for school canteens and factories. When children fall ill, metrace
> traces the **cooking batch** back to ingredient lots and suppliers, and locks
> that food at **every** delivery point within a second.

- **Poka-yoke, not paperwork:** a wrong step is impossible, not just recorded —
  expired supplier certificate, warm delivery, undercooked batch, missing
  retained sample or missing check form all block the action with the reason
  and its legal basis.
- **Trace and lock:** one lineage graph (lot → batch → intermediate batch →
  shipment → delivery point), recall locks that hold every pending truck in the
  same transaction, recall notices for food that already left, four-eyes close.
- **Headless core:** Keycloak (SSO), Apache APISIX (gateway), PostgreSQL +
  SeaweedFS (data), Flowable (workflow). One web app, a CLI and a sensor
  simulator all use the same API through the gateway.

All data in this repository is **synthetic** (names tagged DEMO).

## Quick start

Requirements: Docker with Compose v2 (on Apple Silicon: Colima with ≥6 GB),
GNU Make, Bash, curl, jq.

```bash
make init                   # writes .env with random secrets (never committed)
docker compose up -d --wait # builds, migrates, seeds; first run takes a few minutes
```

Open <http://localhost:9080> (bound to 127.0.0.1 only).

| Path      | Service |
|-----------|---------|
| `/`       | Web app: `/ops` for staff (tablet), `/portal` for customers (phone) |
| `/api/*`  | metrace API (JWT verified at the gateway and again in the API) |
| `/auth/*` | Keycloak login, token and device endpoints only |

Demo accounts (the password is `DEMO_USER_PASSWORD` in your `.env`):

| Username | Role |
|---|---|
| `procurement-mai` | Goods receipt |
| `chef-hung` | Cooking, shipments |
| `qa-lan` | Quality: samples, checks, incidents |
| `approver-ha` | Second approver (four-eyes close) |
| `driver-tuan` | Dispatch |
| `cskh-thu` | Customer care: complaints |
| `director-nam` | Director |
| `truong-a`, `truong-b`, `truong-c`, `nha-may-x` | Customer staff (schools, factory) |

Fresh demo data for "today" at any time:

```bash
make demo-reset                           # yesterday delivered, today's lunch ready to ship
scripts/demo-reset.sh baseline,outbreak   # plus two complaints about yesterday's lunch
```

## Command line

```bash
uv tool install ./cli
metrace login                                     # device flow in the browser, staff only
metrace trace lot LOT-20261008-XUONG-LON -d forward
metrace shipments list --status held
metrace drill run lot LOT-20261008-XUONG-LON      # recall drill, dry run
```

## Optional pieces

- **Sensors:** `cd tools/sensor-simulator && uv run simulate_fridge.py --asset TU-MAU-01 --mode breach`
  (needs `SENSOR_GATEWAY_CLIENT_SECRET` from `.env`).
- **AI report drafts:** `scripts/ai-up.sh` runs Ollama with Qwen3-4B on the host.
  Without it, drafts use a deterministic template. A draft never triggers
  anything; QA edits and approves it.

## Documentation

| Document | Content |
|---|---|
| [architecture.md](docs/architecture.md) | Tiers, data flow, identity model |
| [domain-model.md](docs/domain-model.md) | Entities, lineage view, demo data |
| [poka-yoke-rules.md](docs/poka-yoke-rules.md) | Every blocking rule, reason code and threshold basis |
| [bpmn.md](docs/bpmn.md) | The two workflows (incident recall, cold-chain alert) |
| [api.md](docs/api.md) | Authentication, authorization, errors, endpoints |
| [deployment.md](docs/deployment.md) | Configuration, operations, clean-machine check |
| [demo-guide.md](docs/demo-guide.md) | A 15-minute walkthrough |
| [license-policy.md](docs/license-policy.md), [license-declaration.md](docs/license-declaration.md) | Licensing |

## Development

```bash
make lint                # ruff + reuse
make test                # API unit tests
make test-integration    # starts the stack with dev ports and runs integration tests
npm ci && npm run typecheck && npm test && npm run build   # web app
make licenses            # regenerate the license declaration (fails outside the allow-list)
```

Building from source: the API, worker and web images are built from this
repository (`services/api`, `infra/web`); Keycloak is the publisher's image
with our build options (`infra/keycloak`); the other services are pulled by tag
from their publishers (see `compose.yaml`).

## License

Apache-2.0, see [LICENSE](LICENSE). Every file carries an SPDX header and
`reuse lint` passes. Contributors are listed in [AUTHORS](AUTHORS).
