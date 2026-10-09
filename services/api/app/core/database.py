# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""SQLAlchemy engine and session handling.

Write paths commit explicitly (`session.commit()` in the service function), so
a failed commit always surfaces as an error response, never after the fact.
"""

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import not_found
from app.core.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"options": "-c timezone=UTC"},
    )


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(get_engine(), expire_on_commit=False)


def new_session() -> Session:
    return _session_factory()()


def get_session() -> Iterator[Session]:
    session = new_session()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_session)]


def get_or_404(session: Session, model, ident, entity: str, *, for_update: bool = False):
    """Load by primary key or raise the common 404 envelope."""
    row = session.get(model, ident, with_for_update=for_update)
    if row is None:
        raise not_found(entity)
    return row
