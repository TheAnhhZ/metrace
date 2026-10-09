// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { formatCountdown, remainingMs } from "../lib/server-clock";
import { useNowMs } from "../lib/use-now-ms";

/**
 * Counts down to `target` on the SERVER's clock: now = tablet clock + offsetMs, where
 * offsetMs = server_now - Date.now() was captured when the data was fetched. Changing the
 * tablet's date/time therefore cannot make a retained sample look discardable early.
 */
export function CountdownTimer(props: { target: string; offsetMs: number; doneLabel?: string }) {
  const { target, offsetMs, doneLabel = "Đã đủ thời gian" } = props;
  const remaining = remainingMs(target, useNowMs(), offsetMs);
  if (remaining <= 0) {
    return <span className="text-xl font-bold text-green-700">{doneLabel}</span>;
  }
  return (
    <time dateTime={target} role="timer" className="font-mono text-3xl font-bold tabular-nums text-amber-700">
      {formatCountdown(remaining)}
    </time>
  );
}
