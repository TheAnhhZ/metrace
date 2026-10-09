# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""platform baseline: audit chain, outbox, file objects, runtime grants

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "audit_event",
        sa.Column("seq", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("at", TS, nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("payload", pg.JSONB, nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False, unique=True),
    )
    op.create_index("ix_audit_event_entity", "audit_event", ["entity_type", "entity_id"])

    op.create_table(
        "outbox_event",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("lane", sa.String(20), nullable=False, server_default="fast"),
        sa.Column("aggregate_type", sa.String(60)),
        sa.Column("aggregate_id", pg.UUID(as_uuid=True)),
        sa.Column("payload", pg.JSONB, nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now()),
        sa.Column("next_attempt_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("claimed_until", TS),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("processed_at", TS),
        sa.Column("failed_at", TS),
        sa.Column("last_error", sa.Text),
    )
    op.create_index(
        "ix_outbox_event_due",
        "outbox_event",
        ["lane", "next_attempt_at"],
        postgresql_where=sa.text("processed_at IS NULL AND failed_at IS NULL"),
    )

    op.create_table(
        "file_object",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("storage_key", sa.String(80), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("owner_org_alias", sa.String(100)),
        sa.Column("uploaded_by", sa.String(100), nullable=False),
        sa.Column("uploaded_at", TS, server_default=sa.func.now()),
    )
    op.create_index("ix_file_object_sha256", "file_object", ["sha256"])
    op.create_index("ix_file_object_owner_org_alias", "file_object", ["owner_org_alias"])

    # Runtime role: full DML on business tables (now and future), but the audit
    # chain is append-only for it.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO metrace_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO metrace_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO metrace_app"
    )
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO metrace_app")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit_event FROM metrace_app")
    op.execute("REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON alembic_version FROM metrace_app")


def downgrade() -> None:
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM metrace_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM metrace_app"
    )
    op.drop_table("file_object")
    op.drop_table("outbox_event")
    op.drop_table("audit_event")
