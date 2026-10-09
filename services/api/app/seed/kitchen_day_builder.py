# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Build one service day of kitchen records: receiving -> lots -> batches (broth
first) -> samples -> shipments + Mẫu 3. Times come from a `clock(minutes)` that the
scenario anchors either to a fixed past day or to `now()`."""

from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models.cooking import BatchInput, CookingBatch, PortionCheck, RetainedSample
from app.models.enums import BatchStatus, ShipmentStatus
from app.models.shipment import Shipment, ShipmentItem
from app.models.supplier_and_lots import IngredientLot, Receiving
from app.seed.master_data_loader import MasterData

Clock = Callable[[int], datetime]  # minutes relative to the day's anchor -> UTC instant
INTERMEDIATE = "NUOC-DUNG"
SEED_ACTOR = "seed"


class KitchenDayBuilder:
    def __init__(self, session, master: MasterData, day: date, clock: Clock, meal_ends: dict[str, datetime]):
        self.s, self.m, self.day, self.clock, self.meal_ends = session, master, day, clock, meal_ends
        self.stamp = day.strftime("%Y%m%d")
        self.dishes = {d["code"]: d for d in master.raw["dishes"]}
        self.batches: dict[tuple[str, str], CookingBatch] = {}

    # -- portions -------------------------------------------------------------
    def portions(self, slot: str) -> dict[str, int]:
        """Portions per customer alias for a slot."""
        return {c["alias"]: c["portions"][slot] for c in self.m.raw["customers"] if slot in c["portions"]}

    def ingredient_needs(self, slots: list[str]) -> dict[str, Decimal]:
        needs: dict[str, Decimal] = {}
        broth_kg = Decimal(0)
        for slot in slots:
            total = sum(self.portions(slot).values())
            for code in self.m.raw["meal_plan"][slot]["dishes"]:
                dish = self.dishes[code]
                for ing, kg in dish.get("recipe", {}).items():
                    needs[ing] = needs.get(ing, Decimal(0)) + Decimal(str(kg)) * total
                broth_kg += Decimal(str(dish.get("components", {}).get(INTERMEDIATE, 0))) * total
        # Intermediate dish: its "portions" are kilograms of broth.
        for ing, kg in self.dishes[INTERMEDIATE]["recipe"].items():
            needs[ing] = needs.get(ing, Decimal(0)) + Decimal(str(kg)) * broth_kg
        return needs

    def broth_kg(self, slots: list[str]) -> int:
        kg = Decimal(0)
        for slot in slots:
            total = sum(self.portions(slot).values())
            for code in self.m.raw["meal_plan"][slot]["dishes"]:
                kg += Decimal(str(self.dishes[code].get("components", {}).get(INTERMEDIATE, 0))) * total
        return int(kg.to_integral_value()) + 1

    # -- receiving ------------------------------------------------------------
    def receive(
        self, needs: dict[str, Decimal], at_min: int, scale: Decimal = Decimal("1.1")
    ) -> dict[str, IngredientLot]:
        by_code = {i["code"]: i for i in self.m.raw["ingredients"]}
        receivings: dict[str, Receiving] = {}
        lots = {}
        for code, kg in sorted(needs.items()):
            spec = by_code[code]
            supplier = self.m.suppliers[spec["supplier"]]
            if spec["supplier"] not in receivings:
                receivings[spec["supplier"]] = self._add(
                    Receiving(
                        kitchen_id=self.m.kitchen.id,
                        supplier_id=supplier.id,
                        code=f"RCV-{self.stamp}-{spec['supplier']}",
                        received_at=self.clock(at_min),
                        received_by="procurement-mai",
                        document_file_ids=[],
                        sensory_ok=True,
                        quick_test="Đạt",
                        extra={"seeded": True},
                    )
                )
            storage = "TU-DONG-01" if spec["storage"] == "frozen" else "TU-MAT-01"
            lots[code] = self._add(
                IngredientLot(
                    kitchen_id=self.m.kitchen.id,
                    receiving_id=receivings[spec["supplier"]].id,
                    ingredient_id=self.m.ingredients[code].id,
                    supplier_id=supplier.id,
                    lot_code=f"LOT-{self.stamp}-{code}",
                    qty_kg=(kg * scale).quantize(Decimal("0.001")),
                    temp_c=spec["temp_c"],
                    expiry=self.day + timedelta(days=3),
                    storage_asset_id=None if spec["storage"] == "dry" else self.m.assets[storage].id,
                )
            )
        return lots

    # -- cooking ----------------------------------------------------------------
    def cook(self, slot: str, code: str, portions: int, start: int, finish: int, lots, broth=None) -> CookingBatch:
        dish = self.dishes[code]
        batch = self._add(
            CookingBatch(
                kitchen_id=self.m.kitchen.id,
                dish_id=self.m.dishes[code].id,
                batch_code=f"B-{self.stamp}-{slot}-{code}",
                service_date=self.day,
                meal_slot=slot,
                started_at=self.clock(start),
                finished_at=self.clock(finish),
                core_temp_c=Decimal("82.5"),
                owner="chef-hung",
                portions_planned=portions,
                portions_produced=portions,
                status=BatchStatus.FINISHED,
            )
        )
        for ing, kg in dish.get("recipe", {}).items():
            self._add(
                BatchInput(
                    batch_id=batch.id,
                    lot_id=lots[ing].id,
                    qty_kg=Decimal(str(kg)) * portions,
                    added_by="chef-hung",
                    added_at=self.clock(start),
                )
            )
        if broth is not None and INTERMEDIATE in dish.get("components", {}):
            kg = Decimal(str(dish["components"][INTERMEDIATE])) * portions
            self._add(
                BatchInput(
                    batch_id=batch.id,
                    input_batch_id=broth.id,
                    qty_kg=kg,
                    added_by="chef-hung",
                    added_at=self.clock(start),
                )
            )
        self.batches[(slot, code)] = batch
        return batch

    def sample(self, slot: str, batch: CookingBatch, code: str, at_min: int) -> None:
        stored_at = self.clock(at_min)
        meal_end = self.meal_ends[slot]
        liquid = self.dishes[code]["kind"] == "liquid"
        self._add(
            RetainedSample(
                batch_id=batch.id,
                qty_g=None if liquid else 150,
                qty_ml=200 if liquid else None,
                seal_code=f"SEAL-{self.stamp}-{slot}-{code}",
                fridge_asset_id=self.m.assets["TU-MAU-01"].id,
                stored_at=stored_at,
                stored_by="qa-lan",
                meal_end_at=meal_end,
                eligible_discard_at=max(stored_at, meal_end) + timedelta(hours=24),
            )
        )

    def ship(self, slot: str, check_min: int, dispatch_min: int | None, delivered_min: int | None) -> None:
        dishes = [c for c in self.m.raw["meal_plan"][slot]["dishes"]]
        for alias, portions in self.portions(slot).items():
            dp = self.m.points[alias]
            status = ShipmentStatus.DELIVERED if delivered_min is not None else ShipmentStatus.READY
            truck = "XE-02" if alias == "nha-may-x" else "XE-01"
            shipment = self._add(
                Shipment(
                    kitchen_id=self.m.kitchen.id,
                    code=f"SHP-{self.stamp}-{slot}-{dp.code}",
                    delivery_point_id=dp.id,
                    vehicle_asset_id=self.m.assets[truck].id,
                    service_date=self.day,
                    meal_slot=slot,
                    status=status,
                    dispatched_at=self.clock(dispatch_min) if dispatch_min is not None else None,
                    dispatched_by="driver-tuan" if dispatch_min is not None else None,
                    delivered_at=self.clock(delivered_min) if delivered_min is not None else None,
                )
            )
            for code in dishes:
                batch = self.batches[(slot, code)]
                self._add(ShipmentItem(shipment_id=shipment.id, batch_id=batch.id, portions=portions))
                self._add(
                    PortionCheck(
                        batch_id=batch.id,
                        shipment_id=shipment.id,
                        checked_at=self.clock(check_min),
                        checked_by="qa-lan",
                        portions=portions,
                        menu_match=True,
                        sensory_ok=True,
                    )
                )

    def _add(self, row):
        self.s.add(row)
        self.s.flush()
        return row
