<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# metrace

> Working name. Digital operating system for a school/factory catering company:
> trace a cooking batch back to ingredient lots and suppliers, and lock it at
> every delivery point within seconds when something goes wrong.

Built on a headless open-source core (Tier 1): **Keycloak** (SSO),
**Apache APISIX** (gateway), **PostgreSQL + SeaweedFS** (data),
**Flowable** (workflow). Everything is Apache-2.0 or another OSI license.

## Status

Early development (W0). See [CHANGELOG.md](CHANGELOG.md).

## Quick start

Requirements: Docker with Compose v2 (Colima works on Apple Silicon, give it ≥6 GB),
GNU Make, Bash.

```bash
make init                 # writes .env with random secrets (never committed)
docker compose up -d --wait
```

The single public origin is <http://localhost:9080> (bound to 127.0.0.1 only).

| Path      | Service                                   |
|-----------|-------------------------------------------|
| `/auth/*` | Keycloak, login/token endpoints only      |
| `/api/*`  | metrace API (JWT required)                |

Demo accounts (password is `DEMO_USER_PASSWORD` in your `.env`):
`qa-lan`, `approver-ha`, `procurement-mai`, `chef-hung`, `driver-tuan`,
`cskh-thu`, `director-nam` (internal) and `truong-a`, `truong-b`, `truong-c`,
`nha-may-x` (customer staff, one per customer organization).

## Development

```bash
make lint               # ruff + reuse
make test               # unit tests
make test-integration   # needs the stack (uses compose.dev-ports.yaml)
```

## License

Apache-2.0. See [LICENSE](LICENSE). Every file carries an SPDX header;
`reuse lint` must pass.
