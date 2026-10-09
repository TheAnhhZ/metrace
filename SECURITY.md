<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# Security policy

## Reporting a vulnerability

Please do **not** open a public issue. Use GitHub's
"Report a vulnerability" (private security advisory) on this repository.
We aim to answer within 7 days.

## Scope and design notes

- metrace is a demo-grade system meant to run on a single machine. All ports
  are bound to `127.0.0.1`; only the gateway (`:9080`) is published.
- Secrets live only in `.env`, generated per installation by `make init`.
- The API re-verifies every JWT (signature via JWKS, issuer, audience, expiry)
  behind the gateway and denies by default.
- The audit log is a hash chain: tamper-evident, not a digital signature.
