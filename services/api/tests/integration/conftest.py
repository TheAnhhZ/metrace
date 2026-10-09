# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Integration fixtures: real PostgreSQL (dev port 127.0.0.1:5432), never mocks."""

import os

import pytest
from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def _url(role: str, password_env: str) -> URL:
    # URL objects mask the password in reprs and tracebacks.
    return URL.create(
        "postgresql+psycopg",
        username=role,
        password=os.environ[password_env],
        host=os.environ.get("PGHOST_FOR_TESTS", "localhost"),
        port=5432,
        database="metrace",
    )


@pytest.fixture(scope="session")
def app_engine():
    """Runtime role, same privileges as the API."""
    engine = create_engine(_url("metrace_app", "METRACE_APP_PASSWORD"), connect_args={"options": "-c timezone=UTC"})
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def owner_engine():
    """Schema owner, used only to clean up rows the app role may not delete."""
    engine = create_engine(
        _url("metrace_migrator", "METRACE_MIGRATOR_PASSWORD"), connect_args={"options": "-c timezone=UTC"}
    )
    yield engine
    engine.dispose()


@pytest.fixture
def app_session(app_engine):
    factory = sessionmaker(app_engine, expire_on_commit=False)
    with factory() as session:
        yield session


@pytest.fixture
def session_factory(app_engine):
    return sessionmaker(app_engine, expire_on_commit=False)


def owner_execute(owner_engine, sql: str, **params) -> None:
    with Session(owner_engine) as session, session.begin():
        session.execute(text(sql), params)
