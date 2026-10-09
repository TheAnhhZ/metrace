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

Early development: core platform up (SSO, gateway, data, workflow, worker). See [CHANGELOG.md](CHANGELOG.md).

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
| `/auth/*` | Keycloak, login/token/device endpoints only |
| `/api/*`  | metrace API (JWT required, default deny)  |
| `/*`      | Web app                                   |

`docker compose up` runs three one-shot jobs before the API starts:
`migrate` (database schema + S3 bucket), `kc-bootstrap` (organizations,
memberships, overlays) and, later, `seed` (demo data). All are idempotent.

Check a running stack with `scripts/smoke-core.sh`.

Demo accounts (password is `DEMO_USER_PASSWORD` in your `.env`):
`qa-lan`, `approver-ha`, `procurement-mai`, `chef-hung`, `driver-tuan`,
`cskh-thu`, `director-nam` (internal) and `truong-a`, `truong-b`, `truong-c`,
`nha-may-x` (customer staff, one per customer organization).

## Command line

```bash
uv tool install ./cli
metrace login                       # device flow: approve in the browser (staff accounts only)
metrace trace lot LOT-20261008-XUONG-LON --direction forward
metrace shipments list --status held
metrace incidents list
```

`METRACE_URL` (default `http://localhost:9080`) points the CLI at another gateway.
Tokens are cached in `~/.config/metrace/token.json` (mode 600).

## Demo data

```bash
make demo-reset                     # fresh "today": yesterday delivered, today's lunch ready
scripts/demo-reset.sh baseline,outbreak   # plus two complaints about yesterday's lunch
```

## Development

```bash
make lint               # ruff + reuse
make test               # unit tests
make test-integration   # needs the stack (uses compose.dev-ports.yaml)
```

## License

Apache-2.0. See [LICENSE](LICENSE). Every file carries an SPDX header;
`reuse lint` must pass.
