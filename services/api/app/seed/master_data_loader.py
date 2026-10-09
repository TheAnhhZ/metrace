# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Upsert master data from master-data.yaml, keyed by business code (idempotent)."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.cooking import Dish
from app.models.kitchen_and_customers import Asset, CustomerOrg, DeliveryPoint, Kitchen
from app.models.rules import RuleThreshold
from app.models.supplier_and_lots import Ingredient, Supplier, SupplierCertificate

MASTER_FILE = Path(__file__).with_name("master-data.yaml")


@dataclass
class MasterData:
    """Loaded rows by code, plus the raw YAML for recipes and the meal plan."""

    raw: dict[str, Any]
    kitchen: Kitchen
    customers: dict[str, CustomerOrg]
    points: dict[str, DeliveryPoint]
    suppliers: dict[str, Supplier]
    ingredients: dict[str, Ingredient]
    dishes: dict[str, Dish]
    assets: dict[str, Asset]


def _upsert(session: Session, model: type[Base], key: str, key_value: Any, /, **fields: Any):
    row = session.scalar(select(model).where(getattr(model, key) == key_value))
    if row is None:
        row = model(**{key: key_value}, **fields)
        session.add(row)
    else:
        for name, field_value in fields.items():
            setattr(row, name, field_value)
    session.flush()
    return row


def load_master_data(session: Session, today: date, path: Path = MASTER_FILE) -> MasterData:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    kitchen = _upsert(session, Kitchen, "code", raw["kitchen"]["code"], name=raw["kitchen"]["name"])

    customers, points = {}, {}
    for c in raw["customers"]:
        org = _upsert(
            session, CustomerOrg, "kc_org_alias", c["alias"], name=c["name"], kind=c["kind"], profile=c["profile"]
        )
        dp = c["delivery_point"]
        customers[c["alias"]] = org
        points[c["alias"]] = _upsert(
            session, DeliveryPoint, "code", dp["code"], customer_org_id=org.id, name=dp["name"], address=dp["address"]
        )

    suppliers = {}
    for s in raw["suppliers"]:
        supplier = _upsert(session, Supplier, "code", s["code"], name=s["name"])
        expires = today + timedelta(days=s["cert"]["expires_in_days"])
        _upsert(
            session,
            SupplierCertificate,
            "number",
            s["cert"]["number"],
            supplier_id=supplier.id,
            issued_on=expires - timedelta(days=3 * 365),
            expires_on=expires,
        )
        suppliers[s["code"]] = supplier

    ingredients = {
        i["code"]: _upsert(
            session, Ingredient, "code", i["code"], name=i["name"], category=i["category"], storage=i["storage"]
        )
        for i in raw["ingredients"]
    }
    dishes = {
        d["code"]: _upsert(
            session, Dish, "code", d["code"], name=d["name"], kind=d["kind"], portion_size_g=d["portion_size_g"]
        )
        for d in raw["dishes"]
    }
    assets = {
        a["code"]: _upsert(
            session,
            Asset,
            "code",
            a["code"],
            kitchen_id=kitchen.id,
            type=a["type"],
            name=a["name"],
            min_c=a["min_c"],
            max_c=a["max_c"],
        )
        for a in raw["assets"]
    }
    for t in raw["thresholds"]:
        _upsert(
            session,
            RuleThreshold,
            "code",
            t["code"],
            value=Decimal(str(t["value"])),
            unit=t["unit"],
            basis=t["basis"],
            basis_type=t["basis_type"],
            enabled=True,
        )
    return MasterData(raw, kitchen, customers, points, suppliers, ingredients, dishes, assets)
