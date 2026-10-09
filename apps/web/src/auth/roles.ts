// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0

export const INTERNAL_ROLES = ["qa", "procurement", "chef", "driver", "cskh", "director", "approver"] as const;
export const CUSTOMER_ROLE = "customer_staff";

export type AppArea = "ops" | "portal";
export type ActionName =
  | "receive"
  | "cook"
  | "storeSample"
  | "discardSample"
  | "portionCheck"
  | "planShipment"
  | "addShipmentItem"
  | "dispatch"
  | "complaintIntake"
  | "openIncident"
  | "confirmSuspects"
  | "requestClose"
  | "approveClose"
  | "editReport"
  | "acknowledgeAlert"
  | "viewAudit";

/** Who may do what; mirrors the "Who may do what" table in docs/poka-yoke-rules.md. */
const ACTION_ROLES: Readonly<Record<ActionName, readonly string[]>> = {
  receive: ["procurement", "qa"],
  cook: ["chef"],
  storeSample: ["chef", "qa"],
  discardSample: ["qa"],
  portionCheck: ["qa", "chef"],
  planShipment: ["chef", "driver"],
  addShipmentItem: ["chef"],
  dispatch: ["chef", "driver"],
  complaintIntake: ["cskh", "qa"],
  openIncident: ["qa"],
  confirmSuspects: ["qa"],
  requestClose: ["qa"],
  approveClose: ["approver"],
  editReport: ["qa"],
  acknowledgeAlert: ["qa"],
  viewAudit: ["qa", "director", "approver"],
};

const ROLE_LABELS_VI: Readonly<Record<string, string>> = {
  qa: "QA",
  procurement: "Thu mua",
  chef: "Bếp trưởng",
  driver: "Tài xế",
  cskh: "CSKH",
  director: "Giám đốc",
  approver: "Người duyệt",
  customer_staff: "Khách hàng",
};

/** The first ops screen each role works in; the root redirect uses the first matching role. */
const OPS_HOME_BY_ROLE: ReadonlyArray<readonly [string, string]> = [
  ["procurement", "/ops/receiving"],
  ["chef", "/ops/cooking"],
  ["qa", "/ops/samples"],
  ["driver", "/ops/dispatch"],
];

export function areaForRoles(roles: readonly string[]): AppArea | null {
  if (INTERNAL_ROLES.some((r) => roles.includes(r))) return "ops";
  if (roles.includes(CUSTOMER_ROLE)) return "portal";
  return null;
}

/** Where `/` sends a user; null when the account has no metrace role at all. */
export function homePathForRoles(roles: readonly string[]): string | null {
  const area = areaForRoles(roles);
  if (area === "portal") return "/portal";
  if (area === null) return null;
  return OPS_HOME_BY_ROLE.find(([role]) => roles.includes(role))?.[1] ?? "/ops/receiving";
}

export function canDo(roles: readonly string[], action: ActionName): boolean {
  return ACTION_ROLES[action].some((r) => roles.includes(r));
}

/** Only metrace roles, in display order, as Vietnamese labels (hides Keycloak defaults). */
export function roleLabelsVi(roles: readonly string[]): string[] {
  return Object.keys(ROLE_LABELS_VI)
    .filter((r) => roles.includes(r))
    .map((r) => ROLE_LABELS_VI[r] as string);
}
