#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Sample container memory during a rehearsal and print peak RSS and a suggested
# mem_limit (peak x 1.3) per service.   scripts/measure-ram.sh [seconds=120]
set -euo pipefail
cd "$(dirname "$0")/.."
seconds="${1:-120}"
samples=$(mktemp); trap 'rm -f "$samples"' EXIT
end=$(( $(date +%s) + seconds ))
while [[ $(date +%s) -lt $end ]]; do
  docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' >> "$samples"
  sleep 2
done
awk '{ split($2, a, /[A-Za-z]+/); v = a[1]; u = $2; gsub(/[0-9.]/, "", u);
       mib = (u == "GiB") ? v * 1024 : (u == "KiB") ? v / 1024 : v;
       if (mib > peak[$1]) peak[$1] = mib }
     END { printf "%-28s %10s %14s\n", "container", "peak MiB", "mem_limit MiB";
           for (c in peak) printf "%-28s %10.0f %14.0f\n", c, peak[c], peak[c] * 1.3 }' "$samples" | sort
