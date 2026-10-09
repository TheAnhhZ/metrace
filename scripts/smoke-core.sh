#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Smoke test of a running stack (after `docker compose up -d --wait`).
# Needs .env (make init) and the `test` Keycloak overlay for a password-grant token.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

GW="${GATEWAY_URL:-http://localhost:9080}"
fail=0
check() { # name expected actual
  if [[ "$2" == "$3" ]]; then printf '  ok   %s\n' "$1"; else printf '  FAIL %s (expected %s, got %s)\n' "$1" "$2" "$3"; fail=1; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

echo "services:"
unhealthy=$(docker compose ps --format '{{.Service}} {{.Health}}' | awk '$2 != "healthy" {print $1}' | tr '\n' ' ')
check "all long-running services healthy" "" "${unhealthy% }"
for job in migrate kc-bootstrap; do
  check "one-shot $job exited 0" "0" "$(docker compose ps -a --format '{{.Service}} {{.ExitCode}}' | awk -v j="$job" '$1 == j {print $2}')"
done

echo "gateway:"
check "discovery" 200 "$(code "$GW/auth/realms/metrace/.well-known/openid-configuration")"
check "admin console blocked" 404 "$(code "$GW/auth/admin/")"
check "master realm blocked" 404 "$(code "$GW/auth/realms/master/.well-known/openid-configuration")"
check "web app" 200 "$(code "$GW/")"
check "web app deep link" 200 "$(code "$GW/ops/anything")"
check "api without token" 401 "$(code "$GW/api/v1/whoami")"

echo "identity:"
token=$(curl -s -X POST "$GW/auth/realms/metrace/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=metrace-test -d username=truong-a \
  --data-urlencode "password=$DEMO_USER_PASSWORD" -d "scope=openid organization" | jq -r '.access_token // empty')
check "token for truong-a" "yes" "$([[ -n "$token" ]] && echo yes || echo no)"
whoami=$(curl -s -H "Authorization: Bearer $token" "$GW/api/v1/whoami")
check "whoami roles" '["customer_staff"]' "$(jq -c .roles <<<"$whoami")"
check "whoami organizations" '["truong-a"]' "$(jq -c .organizations <<<"$whoami")"

[[ $fail == 0 ]] && echo "smoke: PASS" || { echo "smoke: FAIL"; exit 1; }
