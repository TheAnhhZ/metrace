#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# The clean-machine path starts with `make init`: check that the generated .env is
# parseable (only comments and KEY=value lines), quiet on stderr, and defines every
# key of .env.example with a value where the example says CHANGE_ME.
set -euo pipefail
cd "$(dirname "$0")/.."
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

scripts/generate-dev-secrets.sh >"$work/env" 2>"$work/stderr"
status=0
if [[ -s "$work/stderr" ]]; then
  echo "generator wrote to stderr:" >&2; cat "$work/stderr" >&2; status=1
fi
if bad=$(grep -vnE '^(#.*|[A-Z0-9_]+=[A-Za-z0-9]*)$' "$work/env"); then
  echo "lines that are neither comments nor KEY=value:" >&2; echo "$bad" >&2; status=1
fi
while IFS='=' read -r key value; do
  [[ -z "$key" || "$key" == \#* ]] && continue
  line=$(grep -E "^${key}=" "$work/env" || true)
  if [[ -z "$line" ]]; then
    echo "missing key: $key" >&2; status=1
  elif [[ "$value" == CHANGE_ME && ${#line} -lt $(( ${#key} + 17 )) ]]; then
    echo "secret too short or empty: $key" >&2; status=1
  fi
done < .env.example
[[ $status == 0 ]] && echo "dev secrets: OK ($(grep -c '=' "$work/env") keys)"
exit $status
