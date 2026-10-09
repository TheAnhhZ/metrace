#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Regenerates the typed API schema from the OpenAPI document exported by the backend.
#   packages/api-client/openapi.json  ->  packages/api-client/src/schema.d.ts
set -euo pipefail
cd "$(dirname "$0")/.."

spec=packages/api-client/openapi.json
out=packages/api-client/src/schema.d.ts
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

[ -f "$spec" ] || { echo "generate-api-client: $spec not found" >&2; exit 1; }

npx --no-install openapi-typescript "$spec" --output "$tmp"
# The generated file carries this script's own two-line licence header (lines 2-3), as // comments.
{
  sed -n '2,3p' "$0" | sed 's|^#|//|'
  cat "$tmp"
} >"$out"
echo "generated $out"
