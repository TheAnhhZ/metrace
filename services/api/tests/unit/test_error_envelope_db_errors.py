# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Database errors map to the envelope: 409 for constraints (logged with the name), 422 for bad values."""

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import DataError, IntegrityError

from app.core.errors import install_error_handlers


class _Diag:
    constraint_name = "uq_shipment_item_batch"


class _DriverError(Exception):
    """Shape of a psycopg error: the server's diagnostics travel in `.diag`."""

    diag = _Diag()


app = FastAPI()
install_error_handlers(app)


@app.post("/duplicate")
def _duplicate():
    raise IntegrityError("INSERT INTO shipment_item ...", {}, _DriverError("duplicate key"))


@app.post("/out-of-range")
def _out_of_range():
    raise DataError("INSERT INTO lot ...", {}, Exception("numeric field overflow"))


client = TestClient(app)


def test_integrity_error_is_409_and_names_the_constraint_in_the_log(caplog):
    with caplog.at_level(logging.WARNING, logger="metrace.errors"):
        res = client.post("/duplicate", headers={"x-request-id": "req-42"})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CONFLICT"
    assert "uq_shipment_item_batch" not in res.text  # internals stay in the log
    assert "constraint=uq_shipment_item_batch" in caplog.text and "req-42" in caplog.text


def test_data_error_is_422_without_internals():
    res = client.post("/out-of-range")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "overflow" not in res.text
