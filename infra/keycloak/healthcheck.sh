#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Container healthcheck without curl: query the management port over /dev/tcp.
set -euo pipefail
exec 3<>/dev/tcp/127.0.0.1/9000
printf 'GET /auth/health/ready HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' >&3
grep -q '"status": *"UP"' <&3
