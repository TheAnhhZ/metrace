// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { ClusterSuggestion, Complaint, SuspectRef } from "@metrace/api-client";

export interface SuspectCandidate {
  type: SuspectRef["type"];
  id: string;
  label: string;
  locked: boolean;
}

const LOCKABLE = new Set<string>(["batch", "lot", "supplier"]);

/** The batch complained about first, then everything upstream of it that can be locked. */
export function candidateNodes(suggestion: ClusterSuggestion): SuspectCandidate[] {
  const seen = new Set<string>([suggestion.batch_id]);
  const candidates: SuspectCandidate[] = [
    { type: "batch", id: suggestion.batch_id, label: `${suggestion.batch_code} · ${suggestion.dish}`, locked: false },
  ];
  for (const node of suggestion.upstream) {
    if (!LOCKABLE.has(node.type) || seen.has(node.id)) continue;
    seen.add(node.id);
    candidates.push({ type: node.type as SuspectRef["type"], id: node.id, label: node.label, locked: node.locked });
  }
  return candidates;
}

/** The suggestion sharing the most complaints with an incident (undefined when none overlap). */
export function suggestionForComplaints(
  suggestions: ClusterSuggestion[],
  complaintIds: readonly string[],
): ClusterSuggestion | undefined {
  const mine = new Set(complaintIds);
  let best: ClusterSuggestion | undefined;
  let bestOverlap = 0;
  for (const s of suggestions) {
    const overlap = s.complaint_ids.filter((id) => mine.has(id)).length;
    if (overlap > bestOverlap) {
      best = s;
      bestOverlap = overlap;
    }
  }
  return best;
}

/** Complaints of a suggestion that are not yet attached to an incident. */
export function openComplaintIds(suggestion: ClusterSuggestion, complaints: readonly Complaint[]): string[] {
  const open = new Set(complaints.filter((c) => c.status === "open").map((c) => c.id));
  return suggestion.complaint_ids.filter((id) => open.has(id));
}
