// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { areaForRoles, canDo, homePathForRoles, roleLabelsVi } from "./roles";

describe("role routing", () => {
  it("sends internal roles to /ops and customer staff to /portal", () => {
    expect(areaForRoles(["offline_access", "qa"])).toBe("ops");
    expect(areaForRoles(["customer_staff"])).toBe("portal");
    expect(areaForRoles(["offline_access"])).toBeNull();
  });

  it("picks a home screen per role", () => {
    expect(homePathForRoles(["procurement"])).toBe("/ops/receiving");
    expect(homePathForRoles(["chef"])).toBe("/ops/cooking");
    expect(homePathForRoles(["qa"])).toBe("/ops/samples");
    expect(homePathForRoles(["driver"])).toBe("/ops/dispatch");
    expect(homePathForRoles(["director"])).toBe("/ops/receiving");
    expect(homePathForRoles(["customer_staff"])).toBe("/portal");
    expect(homePathForRoles([])).toBeNull();
  });

  it("mirrors the who-may-do-what table", () => {
    expect(canDo(["qa"], "discardSample")).toBe(true);
    expect(canDo(["chef"], "discardSample")).toBe(false);
    expect(canDo(["chef"], "cook")).toBe(true);
    expect(canDo(["driver"], "dispatch")).toBe(true);
    expect(canDo(["driver"], "addShipmentItem")).toBe(false);
    expect(canDo(["procurement"], "receive")).toBe(true);
  });

  it("gates the incident, cold-chain and audit actions", () => {
    expect(canDo(["cskh"], "complaintIntake")).toBe(true);
    expect(canDo(["cskh"], "openIncident")).toBe(false);
    expect(canDo(["qa"], "confirmSuspects")).toBe(true);
    expect(canDo(["qa"], "approveClose")).toBe(false);
    expect(canDo(["approver"], "approveClose")).toBe(true);
    expect(canDo(["qa"], "acknowledgeAlert")).toBe(true);
    expect(canDo(["director"], "viewAudit")).toBe(true);
    expect(canDo(["chef"], "viewAudit")).toBe(false);
  });

  it("hides Keycloak default roles in the header", () => {
    expect(roleLabelsVi(["default-roles-metrace", "chef", "uma_authorization"])).toEqual(["Bếp trưởng"]);
  });
});
