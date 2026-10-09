// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
/** Friendly names for the generated schema plus the hand-written Poka-yoke shapes. */
import type { components } from "./schema";

export type Schemas = components["schemas"];

export type WhoAmI = Schemas["WhoAmI"];
export type Supplier = Schemas["SupplierOut"];
export type Certificate = Schemas["CertificateOut"];
export type Ingredient = Schemas["IngredientOut"];
export type Dish = Schemas["DishOut"];
export type DeliveryPoint = Schemas["DeliveryPointOut"];
export type Asset = Schemas["AssetOut"];
export type Lot = Schemas["LotListOut"];
export type Batch = Schemas["BatchOut"];
export type Sample = Schemas["SampleOut"];
export type SampleList = Schemas["SampleListOut"];
export type Shipment = Schemas["ShipmentOut"];
export type ShipmentItem = Schemas["ShipmentItemOut"];
export type MealServiceStatus = Schemas["MealServiceStatusOut"];
export type MealStep = Schemas["MealStepOut"];
export type ReceivingIn = Schemas["ReceivingIn"];
export type ReceivingOut = Schemas["ReceivingOut"];
export type FileOut = Schemas["FileOut"];
export type MealSlot = Schemas["MealSlot"];

export type BasisType = "law" | "guidance" | "field" | "internal";
export type CertState = "valid" | "expiring" | "expired";

/** One lock hit reported by the lineage walk (`target` = "lot:<uuid>" etc., `incident` = code). */
export interface LockHit {
  target: string;
  incident: string;
}

/**
 * A Poka-yoke violation or warning. `rule` and `code` are always present; the rest
 * depends on the code (see docs/poka-yoke-rules.md), hence all optional.
 */
export interface PokaYokeFinding {
  rule: string;
  code: string;
  measured?: string | number | null;
  limit?: string | number | null;
  unit?: string;
  basis?: string;
  basis_type?: BasisType | string;
  batch?: string;
  supplier?: string;
  ingredient?: string;
  shipment?: string;
  portions?: number;
  days_left?: number;
  expired_on?: string | null;
  remaining_minutes?: number;
  eligible_discard_at?: string;
  held_minutes?: number;
  locks?: LockHit[];
  open_incidents?: string[];
}
