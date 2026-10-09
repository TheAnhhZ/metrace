<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# Poka-yoke rules

A wrong step is not warned about after the fact; it is **impossible**. The
P1–P4 rules are pure functions in `services/api/app/rules/`: each receives a
snapshot and the thresholds and returns blocking violations and non-blocking
warnings. The lock guards (`services/api/app/services/lock_guard.py`) and the
four-eyes close (`services/api/app/services/incident_service.py`) apply the
incident rules. The API answers `422` with every violation at once, and logs
each block in `poka_yoke_event`.

```json
{"error": {"code": "P1_SUPPLIER_CERT_EXPIRED", "rule": "P1", "message": "Blocked by Poka-yoke rule P1",
           "details": {"violations": [{"rule": "P1", "code": "P1_SUPPLIER_CERT_EXPIRED", "supplier": "NCC-06"}],
                       "warnings": []},
           "request_id": "…"}}
```

There is no switch to turn a rule off at runtime and no API that writes
thresholds. Changing a threshold is a reviewed migration or seed change.

## Basis of each threshold

Every threshold carries its basis so screens can show *why*:

| basis_type | Meaning |
|---|---|
| `law` | Binding legal text, verified |
| `guidance` | Official guidance (e.g. Quyết định 1246/QĐ-BYT), pending verification of current validity |
| `field` | Values used by interviewed kitchens (anonymised) |
| `internal` | Company policy, no external source yet |

| Code | Default | Unit | Basis type |
|---|---|---|---|
| `receiving_chilled_max_c` | 4 | °C | internal |
| `receiving_frozen_max_c` | -18 | °C | internal |
| `core_temp_min_c` | 75 | °C | internal |
| `dispatch_hold_max_min` | 120 | min | internal |
| `sample_min_solid_g` / `sample_min_liquid_ml` | 100 / 150 | g / ml | guidance |
| `sample_required_min_portions` | 30 | portions | guidance |
| `sample_retention_h` | 24 | h | guidance |
| `cert_warn_days` | 30 | days | internal |

Defaults are the seed values (`services/api/app/seed/master-data.yaml`).

## Rules

### P1 — Goods receipt (Mẫu 1)
| Code | Blocks when |
|---|---|
| `P1_MISSING_DOCUMENTS` | No delivery document attached |
| `P1_SUPPLIER_BLOCKED` | Supplier is blocked, or locked by an open incident |
| `P1_SUPPLIER_CERT_EXPIRED` | No food-safety certificate valid today |
| `P1_TEMP_OUT_OF_RANGE` | A chilled/frozen line is above its limit, or has no temperature |
| `P1_SUPPLIER_CERT_EXPIRING` | *Warning*: certificate expires within `cert_warn_days` |

### P2 — Cooking (Mẫu 2)
| Code | Blocks when |
|---|---|
| `P2_MISSING_TIMESTAMPS` | Start or finish time missing, or finish before start |
| `P2_MISSING_INPUTS` | Finish with no input recorded (traceability) |
| `P2_CORE_TEMP_BELOW_MIN` | Core temperature below `core_temp_min_c`, or not recorded |
| `P2_INPUT_LOCKED` | An input, or anything upstream of the batch, is locked by an incident; also when the lineage cannot be walked (fail closed) |

An input batch (e.g. a broth) must be another finished batch cooked for the
same service day, otherwise `409`: cooked food is not carried over to another day.

### P3 — Dispatch
| Code | Blocks when |
|---|---|
| `P3_MISSING_FORM_1` | A lot behind a batch lacks an accepted receiving with documents |
| `P3_MISSING_FORM_2` | A batch on the truck is not finished |
| `P3_MISSING_FORM_3` | No portion check (Mẫu 3) for a batch on this shipment |
| `P3_DISH_NOT_IN_MENU` | The dish is not on that customer's menu for that meal |
| `P3_HOLD_TIME_EXCEEDED` | Cooked more than `dispatch_hold_max_min` ago |
| `P3_SAMPLE_MISSING` | Meal of `sample_required_min_portions`+ portions without a retained sample |
| `P3_SHIPMENT_HELD` / `P3_UPSTREAM_LOCKED` | Shipment held, or anything upstream locked by an incident |
| `P3_LINEAGE_TRUNCATED` | Lineage could not be walked completely (fail closed) |
| `P3_SHIPMENT_EMPTY` | Nothing on the truck |

Closing an incident releases its locks but **does not** release held shipments:
the food on them was part of a recall. The safe default is to plan a new
shipment with freshly cooked food.

`GET /api/v1/shipments` shows each open shipment's current blockers, so the
dispatch screen can explain what is missing before anyone presses the button.

### P4 — Retained samples
| Code | Blocks when |
|---|---|
| `P4_SAMPLE_UNDER_MINIMUM` | Less than 100 g (solid) / 150 ml (liquid) |
| `P4_DISCARD_BEFORE_RETENTION` | Before `max(stored_at, meal_end_at) + 24 h` |
| `P4_DISCARD_DURING_INCIDENT` | The batch is locked, suspected, or its service day is under an open incident |

### P5 — Four-eyes incident close
| Code | Blocks when |
|---|---|
| `P5_SAME_PERSON` | The approver is the person who requested the close (`422`) |

Requesting a close needs `qa`; approving or rejecting needs `approver`. These
state conflicts are `409`, not rule violations: `CLOSE_REQUEST_PENDING` (a
request is already open), `INCIDENT_CLOSED`, and `CONFLICT` (request already decided).

### P6 — Complaint answer deadline (flag, not a block)
A worker sweep every 30 s sets `complaint.sla_breached` once `sla_due_at` has
passed, and writes a `complaint.sla_breached` audit event. There is no reason
code. The deadline comes from the customer profile (`sla_hours`; 24 for schools
and 12 for the factory in the demo) or from `COMPLAINT_SLA_OVERRIDE_MINUTES`.

## Who may do what

| Step | Roles |
|---|---|
| Receiving | `procurement`, `qa` |
| Start batch, add input, finish | `chef` |
| Store sample | `chef`, `qa` |
| Discard sample | `qa` |
| Portion check (Mẫu 3) | `qa`, `chef` |
| Create shipment, dispatch | `chef`, `driver` |
| Add batch to shipment | `chef` |
| Complaint intake (internal channel) | `cskh`, `qa` |
| Open incident, confirm suspects (lock), request close | `qa` |
| Incident report: draft, edit, approve | `qa` |
| Approve or reject close request | `approver` |
| Cold-chain alert: acknowledge | `qa` |
| Recall drill | `qa`, `director` |
| Audit head and verify | `qa`, `director`, `approver` |
| Any other internal read (master data, lineage, shipments, samples) | any internal role |

The meal checklist `GET /api/v1/meal-services/{day}/{meal_slot}/status`
(menu → received → cooked → samples → Mẫu 3 → dispatched) is computed from
data; the kitchen flow has no BPMN process.
