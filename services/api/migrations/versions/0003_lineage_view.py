# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""lineage view: every traceability edge as (from_type, from_id) -> (to_type, to_id)

Built from existing foreign keys only (no separate edge table, nothing to drift).
supplier -> lot, asset -> lot (stored in), lot -> batch, batch -> batch (intermediate),
batch -> shipment, shipment -> delivery_point.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIEW lineage_edge AS
              SELECT 'supplier'::text AS from_type, supplier_id AS from_id, 'lot'::text AS to_type, id AS to_id
                FROM ingredient_lot
        UNION ALL SELECT 'asset', storage_asset_id, 'lot', id FROM ingredient_lot WHERE storage_asset_id IS NOT NULL
        UNION ALL SELECT 'lot', lot_id, 'batch', batch_id FROM batch_input WHERE lot_id IS NOT NULL
        UNION ALL SELECT 'batch', input_batch_id, 'batch', batch_id FROM batch_input WHERE input_batch_id IS NOT NULL
        UNION ALL SELECT 'batch', batch_id, 'shipment', shipment_id FROM shipment_item
        UNION ALL SELECT 'shipment', id, 'delivery_point', delivery_point_id FROM shipment
        """
    )
    # The default privileges cover tables; views need an explicit grant.
    op.execute("GRANT SELECT ON lineage_edge TO metrace_app")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS lineage_edge")
