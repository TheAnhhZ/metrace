# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Import every model module so Base.metadata knows all tables."""

from app.models import (  # noqa: F401
    cooking,
    incident,
    kitchen_and_customers,
    platform,
    rules,
    shipment,
    supplier_and_lots,
)
