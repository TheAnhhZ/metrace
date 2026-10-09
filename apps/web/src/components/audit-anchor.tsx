// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { type AuditAnchorValue, formatAnchor, shortAnchor } from "../lib/audit-anchor";

/**
 * "Mã đối chiếu: #12 · 3fa9c1d0e5b2": the audit-chain position printed outside the database, so
 * anyone can later check the chain against it (audit screen). The button copies the full value.
 */
export function AuditAnchor({ anchor }: { anchor: AuditAnchorValue }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(formatAnchor(anchor));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false); // clipboard blocked (insecure origin): the short code is still readable on screen
    }
  }
  return (
    <p className="flex flex-wrap items-center gap-2 text-base">
      <span>Mã đối chiếu:</span>
      <code className="rounded bg-slate-100 px-2 py-1 font-mono text-base font-semibold">{shortAnchor(anchor)}</code>
      <button type="button" onClick={() => void copy()} className="min-h-11 rounded-lg border border-slate-400 bg-white px-4 text-base font-semibold hover:bg-slate-50">
        {copied ? "Đã sao chép" : "Sao chép"}
      </button>
    </p>
  );
}
