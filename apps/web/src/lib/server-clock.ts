// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
/**
 * Time rules for food-safety screens: never trust the tablet clock.
 * offset = server_now - Date.now() captured when the response arrived;
 * "server time now" = Date.now() + offset.
 */

/**
 * Parse an ISO timestamp from the API. The server sends microseconds ("...:42.964105Z"); only
 * milliseconds are standard, so extra fraction digits are cut before parsing (Safari on tablets).
 */
export function parseInstant(iso: string): number {
  return Date.parse(iso.replace(/(\.\d{3})\d+/, "$1"));
}

export function computeOffsetMs(serverNowIso: string, clientNowMs: number): number {
  const server = parseInstant(serverNowIso);
  if (Number.isNaN(server)) throw new Error(`invalid server_now: ${serverNowIso}`);
  return server - clientNowMs;
}

/** Milliseconds until `targetIso` on the server's clock (negative when already past). */
export function remainingMs(targetIso: string, clientNowMs: number, offsetMs: number): number {
  return parseInstant(targetIso) - (clientNowMs + offsetMs);
}

/** HH:MM:SS (hours can exceed 24 because samples are retained for a day or more). */
export function formatCountdown(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

/** The business day (YYYY-MM-DD) an instant belongs to in the company time zone. */
export function businessDay(instantMs: number, timeZone: string): string {
  // en-CA formats as YYYY-MM-DD
  return new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).format(
    new Date(instantMs),
  );
}

export function formatTime(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat("vi-VN", { timeZone, hour: "2-digit", minute: "2-digit", hour12: false }).format(
    new Date(parseInstant(iso)),
  );
}

export function formatDateTime(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone,
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(parseInstant(iso)));
}
