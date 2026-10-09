// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0

export interface AuditAnchorValue {
  seq: number;
  hash: string;
}

const HASH = /^[0-9a-f]{64}$/;

/** Machine-friendly form, what the "copy" buttons put on the clipboard: `<seq>:<hash>`. */
export function formatAnchor(anchor: AuditAnchorValue): string {
  return `${anchor.seq}:${anchor.hash}`;
}

/** Human-friendly short form shown on screens: `#12 · 3fa9c1d0e5b2`. */
export function shortAnchor(anchor: AuditAnchorValue): string {
  return `#${anchor.seq} · ${anchor.hash.slice(0, 12)}`;
}

/**
 * Read an anchor pasted from a recall notice, PDF footer or drill result.
 * Accepts `12:<hash>`, `12 <hash>`, `#12 <hash>` and `seq=12 hash=<hash>`; the hash must be the full 64 hex chars.
 */
export function parseAnchor(text: string): AuditAnchorValue | undefined {
  const hash = text.toLowerCase().match(/[0-9a-f]{64}/)?.[0];
  if (!hash || !HASH.test(hash)) return undefined;
  const rest = text.toLowerCase().replace(hash, " ");
  const seq = rest.match(/\d+/)?.[0];
  if (!seq || Number(seq) < 1) return undefined;
  return { seq: Number(seq), hash };
}
