#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Licensing guard: caniuse-lite (CC-BY-4.0, not an OSI license) must never enter
# the dependency tree. Fails (exit 1) if any package pulls it in.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d node_modules ]; then
  echo "check-caniuse-lite: node_modules missing, run 'npm ci' first" >&2
  exit 2
fi

# `npm ls <pkg>` exits 0 when found, 1 when absent ("(empty)"). Capture output instead of
# relying on the exit code alone so a broken npm run is not mistaken for "absent".
if out=$(npm ls caniuse-lite --all 2>&1); then
  echo "FAIL: caniuse-lite (CC-BY-4.0) is in the dependency tree:" >&2
  echo "$out" >&2
  exit 1
fi
if grep -q "caniuse-lite" <<<"$out"; then
  echo "FAIL: caniuse-lite (CC-BY-4.0) is in the dependency tree:" >&2
  echo "$out" >&2
  exit 1
fi
echo "OK: caniuse-lite not in the dependency tree"
