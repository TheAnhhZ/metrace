// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0

/**
 * Parse a number typed on a tablet keyboard. Vietnamese users type "4,5" as often as "4.5".
 * Returns undefined for empty or invalid input so callers can tell "not entered" from 0.
 */
export function parseDecimal(text: string): number | undefined {
  const normalized = text.trim().replace(",", ".");
  if (normalized === "") return undefined;
  if (!/^-?\d+(\.\d+)?$/.test(normalized)) return undefined;
  return Number(normalized);
}

/** Positive whole number (portions, grams), or undefined. */
export function parsePositiveInt(text: string): number | undefined {
  const n = parseDecimal(text);
  return n !== undefined && Number.isInteger(n) && n > 0 ? n : undefined;
}
