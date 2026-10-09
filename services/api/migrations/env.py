# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Alembic environment. Runs as the schema owner (metrace_migrator), never as the app role."""

import os

from alembic import context
from sqlalchemy import create_engine

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.models.base import Base

target_metadata = Base.metadata


def _url() -> str:
    url = os.environ.get("MIGRATOR_DATABASE_URL")
    if not url:
        raise RuntimeError("MIGRATOR_DATABASE_URL is not set")
    return url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), connect_args={"options": "-c timezone=UTC"})
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
