#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Regenerate docs/license-declaration.{md,csv} and fail on licenses outside the allow-list.
# Needs: uv, npm (after `npm ci`). Tools used: pip-licenses (MIT), npm ls.
set -euo pipefail
cd "$(dirname "$0")/.."
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

for project in services/api cli tools/sensor-simulator; do
  name=$(basename "$project")
  (cd "$project" && uv sync -q --python 3.12 && \
    uv run -q --with pip-licenses pip-licenses --from=mixed --with-urls --format=json) > "$work/$name.pip.json"
  (cd "$project" && uv export -q --no-dev --no-hashes --format requirements-txt) \
    | sed -nE 's/^([A-Za-z0-9_.-]+)(\[.*\])?==.*/\1/p' | tr '_' '-' > "$work/$name.runtime.txt"
done

npm ls --omit=dev --all --json 2>/dev/null \
  | python3 -c 'import json,sys
def walk(d, out):
    for name, dep in (d.get("dependencies") or {}).items():
        out.add(name); walk(dep, out)
    return out
print(json.dumps(sorted(walk(json.load(sys.stdin), set()))))' > "$work/npm-runtime.json"

python3 scripts/license_inventory.py "$work" "$work/npm-runtime.json"
