# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Simulated fridge thermometers (no real IoT). Posts readings through the gateway
with the `sensor-gateway` machine identity (client credentials).

    uv run simulate_fridge.py --asset TU-MAU-01 --mode breach
    modes: normal (inside the band), drift (slowly warms up), breach (out of band now)

Env: METRACE_URL (default http://localhost:9080), SENSOR_GATEWAY_CLIENT_SECRET.
"""

import argparse
import os
import random
import time
from datetime import UTC, datetime

import httpx

BASE = os.environ.get("METRACE_URL", "http://localhost:9080").rstrip("/")
TOKEN_URL = f"{BASE}/auth/realms/metrace/protocol/openid-connect/token"


def token() -> tuple[str, float]:
    res = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": "sensor-gateway",
            "client_secret": os.environ["SENSOR_GATEWAY_CLIENT_SECRET"],
        },
        timeout=10,
    )
    res.raise_for_status()
    body = res.json()
    return body["access_token"], time.monotonic() + body["expires_in"] - 30


def temperature(mode: str, step: int) -> float:
    if mode == "breach":
        return round(10.5 + random.uniform(0, 1.5), 1)
    if mode == "drift":
        return round(min(4.5 + 0.4 * step, 12.0) + random.uniform(-0.2, 0.2), 1)
    return round(4.5 + random.uniform(-1.0, 1.0), 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--asset", action="append", default=None, help="asset code (repeatable)")
    parser.add_argument("--mode", choices=["normal", "drift", "breach"], default="normal")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between readings")
    parser.add_argument("--count", type=int, default=0, help="stop after N rounds (0 = run forever)")
    args = parser.parse_args()
    assets = args.asset or ["TU-MAU-01"]

    access, expires = token()
    step = 0
    while args.count == 0 or step < args.count:
        if time.monotonic() > expires:
            access, expires = token()
        for asset in assets:
            temp = temperature(args.mode, step)
            res = httpx.post(
                f"{BASE}/api/v1/assets/{asset}/readings",
                timeout=10,
                headers={"Authorization": f"Bearer {access}"},
                json={"ts": datetime.now(UTC).isoformat(), "temp_c": temp},
            )
            flag = " BREACH -> alert opened" if res.status_code == 201 and res.json().get("breach") else ""
            print(f"{datetime.now():%H:%M:%S} {asset} {temp:5.1f}°C -> {res.status_code}{flag}", flush=True)
        step += 1
        if args.count == 0 or step < args.count:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
