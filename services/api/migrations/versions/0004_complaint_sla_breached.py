# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""complaint.sla_breached for the P6 SLA sweep

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("complaint", sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default="false"))
    op.create_index(
        "ix_complaint_sla_open",
        "complaint",
        ["sla_due_at"],
        postgresql_where=sa.text("NOT sla_breached AND status <> 'resolved'"),
    )


def downgrade() -> None:
    op.drop_index("ix_complaint_sla_open", table_name="complaint")
    op.drop_column("complaint", "sla_breached")
