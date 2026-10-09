# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Baseline scenario, always relative to `now` in BUSINESS_TZ:

- yesterday: full cycle, lunch (4 points) + factory dinner, all delivered;
- today: lunch cooked, sampled and checked, shipments READY (not dispatched);
- the broth bones and rice lots bought yesterday are reused today, so one lot
  links two days of meals (the core of the recall demo);
- menus from yesterday to today + 3.

Idempotent per day: a day whose batches already exist is skipped.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_time import local_datetime, service_date
from app.models.cooking import CookingBatch, Menu, MenuItem
from app.models.enums import LotStatus
from app.models.supplier_and_lots import Ingredient, IngredientLot
from app.seed.kitchen_day_builder import INTERMEDIATE, KitchenDayBuilder
from app.seed.master_data_loader import MasterData

MENU_DAYS_AHEAD = 3


def _meal_ends(master: MasterData, day: date) -> dict[str, datetime]:
    return {
        slot: local_datetime(day, time.fromisoformat(plan["end"])) for slot, plan in master.raw["meal_plan"].items()
    }


def ensure_menus(session: Session, master: MasterData, first: date, last: date) -> int:
    created = 0
    day = first
    while day <= last:
        for slot, plan in master.raw["meal_plan"].items():
            customers = plan["customers"] or [None]
            for alias in customers:
                org_id = master.customers[alias].id if alias else None
                exists = session.scalar(
                    select(Menu.id).where(
                        Menu.kitchen_id == master.kitchen.id,
                        Menu.service_date == day,
                        Menu.meal_slot == slot,
                        Menu.customer_org_id.is_(None) if org_id is None else Menu.customer_org_id == org_id,
                    )
                )
                if exists:
                    continue
                menu = Menu(
                    kitchen_id=master.kitchen.id,
                    service_date=day,
                    meal_slot=slot,
                    meal_end_at=_meal_ends(master, day)[slot],
                    customer_org_id=org_id,
                )
                session.add(menu)
                session.flush()
                session.add_all(MenuItem(menu_id=menu.id, dish_id=master.dishes[code].id) for code in plan["dishes"])
                created += 1
        day += timedelta(days=1)
    session.flush()
    return created


def _day_exists(session: Session, day: date) -> bool:
    prefix = f"B-{day.strftime('%Y%m%d')}-"
    return (
        session.scalar(select(CookingBatch.id).where(CookingBatch.batch_code.startswith(prefix)).limit(1)) is not None
    )


def _latest_lot(session: Session, ingredient_code: str) -> IngredientLot | None:
    return session.scalar(
        select(IngredientLot)
        .join(Ingredient)
        .where(Ingredient.code == ingredient_code, IngredientLot.status == LotStatus.IN_STOCK)
        .order_by(IngredientLot.created_at.desc())
        .limit(1)
    )


def _seed_yesterday(session: Session, master: MasterData, day: date, today_needs: dict) -> None:
    anchor = local_datetime(day, time(10, 30))  # lunch dispatch
    b = KitchenDayBuilder(session, master, day, lambda m: anchor + timedelta(minutes=m), _meal_ends(master, day))
    needs = b.ingredient_needs(["lunch", "dinner"])
    for code in master.raw["multi_day_lots"]:
        needs[code] += today_needs.get(code, 0)
    lots = b.receive(needs, at_min=-300)
    broth = b.cook("lunch", INTERMEDIATE, b.broth_kg(["lunch", "dinner"]), -240, -150, lots)
    for slot, (start, finish, sample, check, dispatch, delivered) in {
        "lunch": (-150, -60, -30, -15, 0, 30),
        "dinner": (300, 390, 400, 405, 420, 450),
    }.items():
        for code in master.raw["meal_plan"][slot]["dishes"]:
            batch = b.cook(slot, code, sum(b.portions(slot).values()), start, finish, lots, broth)
            b.sample(slot, batch, code, sample)
        b.ship(slot, check, dispatch, delivered)


def _seed_today(session: Session, master: MasterData, day: date, now: datetime) -> None:
    b = KitchenDayBuilder(session, master, day, lambda m: now + timedelta(minutes=m), _meal_ends(master, day))
    needs = b.ingredient_needs(["lunch"])
    reused = {code: _latest_lot(session, code) for code in master.raw["multi_day_lots"]}
    fresh = {code: kg for code, kg in needs.items() if reused.get(code) is None}
    lots = {**b.receive(fresh, at_min=-240), **{c: lot for c, lot in reused.items() if lot is not None}}
    broth = b.cook("lunch", INTERMEDIATE, b.broth_kg(["lunch"]), -210, -120, lots)
    for code in master.raw["meal_plan"]["lunch"]["dishes"]:
        batch = b.cook("lunch", code, sum(b.portions("lunch").values()), -90, -30, lots, broth)
        b.sample("lunch", batch, code, -25)
    b.ship("lunch", check_min=-20, dispatch_min=None, delivered_min=None)


def seed_baseline(session: Session, master: MasterData, now: datetime) -> dict[str, object]:
    today = service_date(now)
    yesterday = today - timedelta(days=1)
    menus = ensure_menus(session, master, yesterday, today + timedelta(days=MENU_DAYS_AHEAD))
    seeded = []
    if not _day_exists(session, yesterday):
        probe = KitchenDayBuilder(session, master, today, lambda m: now, _meal_ends(master, today))
        _seed_yesterday(session, master, yesterday, probe.ingredient_needs(["lunch"]))
        seeded.append(yesterday.isoformat())
    if not _day_exists(session, today):
        _seed_today(session, master, today, now)
        seeded.append(today.isoformat())
    return {"menus_created": menus, "days_seeded": seeded, "service_date": today.isoformat()}
