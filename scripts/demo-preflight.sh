#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Before going on stage: keep the laptop awake, check clocks and health,
# reset the demo data and warm the stack up.
set -euo pipefail
cd "$(dirname "$0")/.."
ok() { printf '  ok   %s\n' "$1"; }
warn() { printf '  WARN %s\n' "$1"; }

if command -v caffeinate >/dev/null; then
  caffeinate -dims -w $$ & ok "caffeinate (display and system stay awake)"
fi

host=$(date -u +%s)
vm=$(docker run --rm --entrypoint date postgres:17-bookworm -u +%s 2>/dev/null || echo 0)
skew=$(( host > vm ? host - vm : vm - host ))
[[ $skew -lt 2 ]] && ok "host and container clocks agree (${skew}s)" || warn "clock skew ${skew}s (restart the VM)"

unhealthy=$(docker compose ps --format '{{.Service}} {{.Health}}' | awk '$2 != "healthy" {print $1}' | tr '\n' ' ')
[[ -z "${unhealthy// }" ]] && ok "all services healthy" || { warn "unhealthy: $unhealthy"; exit 1; }

scripts/demo-reset.sh baseline,outbreak | tail -1

curl -fsS -o /dev/null http://localhost:9080/ && ok "web app answers"
curl -fsS -o /dev/null http://localhost:9080/auth/realms/metrace/.well-known/openid-configuration && ok "login answers"
if curl -fsS -m 2 -o /dev/null http://127.0.0.1:11434/api/tags; then ok "local LLM up"; else warn "no local LLM: drafts use the template"; fi
echo "Preflight done. Open each persona's browser profile and log in before starting."
