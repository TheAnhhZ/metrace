# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""A small, isolated lineage graph for tests (unique codes, caller rolls back).

S ── L1 ── BROTH ──┬── B1 ── SH1 ── DP1
└─── L2 ───────────┘
                   └── B2 ── SH2 ── DP2
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.cooking import BatchInput, CookingBatch, Dish
from app.models.kitchen_and_customers import CustomerOrg, DeliveryPoint, Kitchen
from app.models.shipment import Shipment, ShipmentItem
from app.models.supplier_and_lots import Ingredient, IngredientLot, Receiving, Supplier
from app.services.lineage_query import NodeRef


@dataclass
class Graph:
    s: NodeRef
    l1: NodeRef
    l2: NodeRef
    broth: NodeRef
    b1: NodeRef
    b2: NodeRef
    sh1: NodeRef
    sh2: NodeRef
    dp1: NodeRef
    dp2: NodeRef


def build_graph(session: Session) -> Graph:
    tag = uuid.uuid4().hex[:8].upper()
    now = datetime.now(UTC)

    def add(row):
        session.add(row)
        session.flush()
        return row

    kitchen = add(Kitchen(code=f"K-{tag}", name="Test kitchen"))
    org = add(CustomerOrg(kc_org_alias=f"org-{tag}", name="Test org", kind="school", profile={}))
    dp1 = add(DeliveryPoint(customer_org_id=org.id, code=f"DP1-{tag}", name="DP1"))
    dp2 = add(DeliveryPoint(customer_org_id=org.id, code=f"DP2-{tag}", name="DP2"))
    supplier = add(Supplier(code=f"S-{tag}", name="Test supplier"))
    ingredient = add(Ingredient(code=f"I-{tag}", name="Test ingredient", category="meat", storage="chilled"))
    dish = add(Dish(code=f"D-{tag}", name="Test dish", kind="solid"))
    receiving = add(
        Receiving(kitchen_id=kitchen.id, supplier_id=supplier.id, code=f"R-{tag}", received_at=now, received_by="t")
    )

    def lot(n: int) -> IngredientLot:
        return add(
            IngredientLot(
                kitchen_id=kitchen.id,
                receiving_id=receiving.id,
                ingredient_id=ingredient.id,
                supplier_id=supplier.id,
                lot_code=f"L{n}-{tag}",
                qty_kg=Decimal(10),
            )
        )

    def batch(name: str) -> CookingBatch:
        return add(
            CookingBatch(
                kitchen_id=kitchen.id,
                dish_id=dish.id,
                batch_code=f"{name}-{tag}",
                service_date=date.today(),
                meal_slot="lunch",
                owner="t",
            )
        )

    def ship(name: str, point: DeliveryPoint, source: CookingBatch) -> Shipment:
        shipment = add(
            Shipment(
                kitchen_id=kitchen.id,
                code=f"{name}-{tag}",
                delivery_point_id=point.id,
                service_date=date.today(),
                meal_slot="lunch",
            )
        )
        add(ShipmentItem(shipment_id=shipment.id, batch_id=source.id, portions=10))
        return shipment

    l1, l2 = lot(1), lot(2)
    broth, b1, b2 = batch("BROTH"), batch("B1"), batch("B2")
    add(BatchInput(batch_id=broth.id, lot_id=l1.id, qty_kg=Decimal(1)))
    add(BatchInput(batch_id=b1.id, lot_id=l2.id, qty_kg=Decimal(1)))
    add(BatchInput(batch_id=b1.id, input_batch_id=broth.id, qty_kg=Decimal(1)))
    add(BatchInput(batch_id=b2.id, input_batch_id=broth.id, qty_kg=Decimal(1)))
    sh1, sh2 = ship("SH1", dp1, b1), ship("SH2", dp2, b2)
    return Graph(
        s=NodeRef("supplier", supplier.id),
        l1=NodeRef("lot", l1.id),
        l2=NodeRef("lot", l2.id),
        broth=NodeRef("batch", broth.id),
        b1=NodeRef("batch", b1.id),
        b2=NodeRef("batch", b2.id),
        sh1=NodeRef("shipment", sh1.id),
        sh2=NodeRef("shipment", sh2.id),
        dp1=NodeRef("delivery_point", dp1.id),
        dp2=NodeRef("delivery_point", dp2.id),
    )
