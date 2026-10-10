<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# License policy

metrace is Apache-2.0. Everything it contains or links must be under an
[OSI-approved](https://opensource.org/licenses) license.

## Scope

Following the organisers' answer of 9 October 2026, licence compliance covers
**the code in this repository and the libraries it uses** (Python and npm
packages, fonts and other files committed here).

Standalone software that metrace only talks to over the network as a service
(Keycloak, Apache APISIX, PostgreSQL, SeaweedFS, Flowable, nginx, the optional
Ollama runtime and model weights) is **not** part of the project's licence
scope. It is still listed, one line each, in the declaration for transparency,
and every one of them is open source under an OSI license.

## Allowed

OSI-approved identifiers, including: MIT, MIT-0, MIT-CMU, ISC, 0BSD,
BSD-2-Clause, BSD-3-Clause, Apache-2.0, MPL-2.0, LGPL-2.1/3.0, PostgreSQL,
Zlib, EPL-2.0, OFL-1.1 (fonts), CC0-1.0, Unlicense, BlueOak-1.0.0.

Documented equivalents:
- `PSF-2.0` is the license text of `Python-2.0` (OSI-approved).
- `GPL-2.0-only WITH Classpath-exception-2.0` (OSI base license plus exception).
- Python packages that only declare the classifier "BSD License" are recorded as
  `BSD-3-Clause` after checking the package; any BSD variant is OSI-approved.

Expressions: `A OR B` is fine when one side is allowed; `A AND B` needs both.

## Denied

Source-available or non-OSI licenses are never accepted, even for dev tools that
end up in the repository or a release: BUSL-1.1, SSPL-1.0, Elastic-2.0, FSL
(including Liquibase 5.x), Commons Clause, CC-BY-4.0 for code or data shipped
in builds (for example `caniuse-lite`, kept out of the web build on purpose:
`scripts/check-caniuse-lite.sh`), and `bpmn-js` (bpmn.io license).

## How it is enforced

- Every file carries an SPDX header or a `REUSE.toml` annotation; CI runs `reuse lint`.
- `scripts/generate-license-inventory.sh` rebuilds
  [license-declaration.md](license-declaration.md) and `license-declaration.csv`
  from the lock files and **fails** when a dependency is outside the allow-list.
  CI runs it on every pull request. npm packages come from `package-lock.json`,
  not from the installed tree, so the result is the same on every OS; native
  builds per OS/CPU are listed individually.
- New dependencies are mentioned in the pull request description.
- Dev tools that are run but never shipped (for example `reuse`, GPL-3.0) are
  not dependencies of metrace.
