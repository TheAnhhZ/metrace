#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Back to a fresh "today" in under a minute: stop worker -> clear Flowable
# instances -> truncate transactional tables -> reseed -> start worker -> warm up.
# Usage: scripts/demo-reset.sh [scenario,...]   (default: baseline)
set -euo pipefail
cd "$(dirname "$0")/.."
scenario="${1:-baseline}"
started=$(date +%s)

docker compose stop worker >/dev/null
docker compose run --rm --no-deps migrate python -m app.bootstrap.demo_reset --scenario "$scenario"
docker compose start worker >/dev/null

for _ in $(seq 1 30); do
  [[ "$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q worker)")" == healthy ]] && break
  sleep 1
done

# Warm-up: first requests after a reset should not pay JIT/connection costs on stage.
curl -s -o /dev/null http://localhost:9080/auth/realms/metrace/.well-known/openid-configuration || true
echo "demo-reset done in $(( $(date +%s) - started ))s (scenario: $scenario)"
