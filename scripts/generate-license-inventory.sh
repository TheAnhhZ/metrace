#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Regenerate docs/license-declaration.{md,csv} and fail on licenses outside the allow-list.
# Needs: uv and python3. Tools used: pip-licenses (MIT). npm packages are read
# from package-lock.json, so the result is the same on every OS/CPU.
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

python3 scripts/license_inventory.py "$work"
