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

// ---- incidents, lineage, portal, cold chain, audit -------------------------------------------
// The OpenAPI models several payloads as open objects (`{[key: string]: unknown}`); the shapes
// below are what the backend actually sends (services/api/app/services/*_view.py, lineage_presenter.py).

export type Complaint = Schemas["ComplaintOut"];
export type ComplaintIn = Schemas["ComplaintIn"];
export type ComplaintChannel = Schemas["ComplaintChannel"];
export type ComplaintStatus = Schemas["ComplaintStatus"];
export type Incident = Schemas["IncidentOut"];
export type CloseRequest = Schemas["CloseRequestOut"];
export type Lock = Schemas["LockOut"];
export type SuspectRef = Schemas["SuspectRef"];
export type VerifyResult = Schemas["VerifyOut"];
export type PortalPoint = Schemas["PortalPointOut"];
export type PortalDelivery = Schemas["DeliveryOut"];
export type PortalComplaintIn = Schemas["PortalComplaintIn"];
export type PortalComplaints = Schemas["PortalComplaintsOut"];

export type LineageNodeType = Schemas["LineageNodeType"];
export type LineageDirection = Schemas["LineageDirection"];
export type LineageEdge = Schemas["LineageEdge"];

/** A lineage node; delivery points carry `portions` and `org`, shipments `service_date`/`meal_slot`. */
export type LineageNode = Schemas["LineageNode"] & {
  org?: string;
  service_date?: string;
  meal_slot?: string;
  asset_type?: string;
};

export interface Lineage {
  root: string;
  direction: LineageDirection;
  nodes: LineageNode[];
  edges: LineageEdge[];
  truncated: boolean;
}

/** Suggestion that several delivery points complained about the same batch. QA confirms it. */
export type ClusterSuggestion = Omit<Schemas["ClusterSuggestion"], "upstream"> & { upstream: LineageNode[] };

/** A shipment touched by an incident's locks (status held = stopped, dispatched/delivered = recall). */
export interface IncidentShipment {
  id: string;
  code: string;
  status: string;
  service_date: string;
  meal_slot: string;
  delivery_point: string;
  org: string;
}

export interface IncidentNoticeSummary {
  id: string;
  delivery_point: string;
  created_at: string;
  acknowledged_at: string | null;
  audit_seq: number;
}

export type IncidentDetail = Omit<Schemas["IncidentDetailOut"], "shipments" | "notices"> & {
  shipments: IncidentShipment[];
  notices: IncidentNoticeSummary[];
};

export interface AuditHead {
  seq: number;
  hash: string;
}

export type LockResult = Omit<Schemas["LockResultOut"], "audit_head"> & { audit_head: AuditHead };

export interface NoticeShipment {
  shipment: string;
  service_date: string;
  meal_slot: string;
  status: string;
  /** hold = not yet gone, keep it; recall = already dispatched/delivered, take it back. */
  action: "hold" | "recall";
  items: { dish: string; batch: string; portions: number }[];
}

export interface NoticeContent {
  incident: string;
  title: string;
  delivery_point: string;
  shipments: NoticeShipment[];
}

export type Notice = Omit<Schemas["NoticeOut"], "content"> & { content: NoticeContent };

export interface ColdChainAlert {
  id: string;
  asset_code: string;
  asset_name: string;
  opened_at: string;
  max_temp_c: number | string;
  min_c: number | string | null;
  max_c: number | string | null;
  /** Lots and batches that sat in the fridge. */
  nodes: LineageNode[];
  /** Seal codes of retained samples stored in it. */
  samples: string[];
}

export interface ColdChainReadings {
  asset_code: string;
  min_c: number | string | null;
  max_c: number | string | null;
  server_now: string;
  readings: { at: string; temp_c: number | string }[];
}

/**
 * The OpenAPI schema models some payloads as open objects. This is the single, greppable place
 * where the shape the backend actually sends (documented above) is asserted for those payloads.
 */
export function asShape<T>(value: unknown): T {
  return value as T;
}
