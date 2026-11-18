from unittest.mock import MagicMock

import pytest
from pymysql.err import OperationalError as MySQLOperationalError
from sqlalchemy import Insert
from sqlalchemy.exc import OperationalError

from app.etl.errors import ETLError
from app.etl.models import staging
from app.etl.service import Pipeline, ingest_operation, ingest_transaction
from tests.etl_fixtures import csv_file, row, source

FAKE_SECRET = "FAKE_SECRET_ETL_DIAGNOSTIC"


@pytest.mark.parametrize(
    ("operation", "driver_only", "invalidated", "expected"),
    [
        ("acquire_lock", False, False, "database_error"),
        ("acquire_lock", True, False, "database_error"),
        ("commit_lock_acquisition", False, False, "database_error"),
        ("prepare_attempt", False, False, "database_error"),
        ("stage_batch", True, False, "database_error"),
        ("stage_batch", False, True, "ingest_lock_lost"),
        ("commit_transaction", False, False, "database_error"),
        ("rollback_transaction", False, False, "database_error"),
    ],
)
def test_ingest_database_failure_is_safe_in_pytest_output(
    tmp_path, caplog, operation, driver_only, invalidated, expected
):
    driver_code = 2013 if invalidated else 1205
    driver_error = MySQLOperationalError(driver_code, FAKE_SECRET)
    failure = (
        driver_error
        if driver_only
        else OperationalError(FAKE_SECRET, {"value": FAKE_SECRET}, driver_error, invalidated)
    )
    engine = MagicMock()
    engine.url.database = "companywatch_test"
    connection = engine.connect.return_value.__enter__.return_value
    connection.invalidated = False
    connection.scalar.return_value = 1
    connection.execute.return_value.mappings.return_value.one.return_value = {
        "id": "synthetic-version",
        "state": "loading",
    }

    def execute(statement, *args):
        if operation == "prepare_attempt":
            raise failure
        if operation == "rollback_transaction":
            raise ETLError("synthetic_transaction_body_failure")
        if (
            operation == "stage_batch"
            and isinstance(statement, Insert)
            and statement.table is staging
        ):
            connection.invalidated = invalidated
            raise failure
        return connection.execute.return_value

    connection.execute.side_effect = execute
    if operation == "acquire_lock":
        connection.scalar.side_effect = failure
    elif operation == "commit_lock_acquisition":
        connection.commit.side_effect = failure
    elif operation in {"commit_transaction", "rollback_transaction"}:
        connection.begin.return_value.__exit__.side_effect = failure

    path = csv_file(tmp_path / "synthetic.csv", [row(1)])
    with pytest.raises((ETLError, OperationalError, MySQLOperationalError)) as raised:
        Pipeline(engine, allow_synthetic=True).ingest(path, source())

    assert FAKE_SECRET not in str(raised.getrepr(style="long", chain=True))
    assert isinstance(raised.value, ETLError)
    assert str(raised.value) == expected
    outcome = "connection_invalidated" if invalidated else "sql_operation_failed"
    assert f"operation={operation} outcome={outcome} elapsed_ms=" in caplog.text
    assert f"driver_code={driver_code}" in caplog.text
    assert FAKE_SECRET not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_ingest_reports_ownership_loss_before_yielding(caplog):
    connection = MagicMock(invalidated=False)
    connection.scalar.return_value = 0

    with pytest.raises(ETLError, match="^ingest_lock_lost$"):
        with ingest_transaction(connection, "SYNTHETIC_PRIVATE_LOCK"):
            pytest.fail("A transaction without the advisory lock must not write")

    assert len(caplog.records) == 1
    assert "operation=check_lock outcome=lock_ownership_lost" in caplog.text
    assert "elapsed_ms=" in caplog.text
    assert "SYNTHETIC_PRIVATE_LOCK" not in caplog.text


@pytest.mark.parametrize("invalidated", [False, True])
def test_ingest_reports_sql_failure_and_disconnect_without_driver_text(caplog, invalidated):
    connection = MagicMock(invalidated=invalidated)
    error = OperationalError(
        "SYNTHETIC_PRIVATE_SQL",
        {"data": "SYNTHETIC_PRIVATE_PARAMETER"},
        RuntimeError(2013 if invalidated else 1205, "SYNTHETIC_PRIVATE_DRIVER_MESSAGE"),
        connection_invalidated=invalidated,
    )
    with pytest.raises(OperationalError) as raised:
        with ingest_operation(connection, "count_accepted_forms"):
            raise error

    assert raised.value is error
    assert len(caplog.records) == 1
    expected = "connection_invalidated" if invalidated else "sql_operation_failed"
    assert f"operation=count_accepted_forms outcome={expected}" in caplog.text
    assert "elapsed_ms=" in caplog.text
    assert f"driver_code={error.orig.args[0]}" in caplog.text
    assert "SYNTHETIC_PRIVATE" not in caplog.text
    assert caplog.records[0].exc_info is None


def test_ingest_refuses_an_invalidated_connection_without_starting_transaction(caplog):
    connection = MagicMock(invalidated=True)

    with pytest.raises(ETLError, match="^ingest_lock_lost$"):
        with ingest_transaction(connection, "SYNTHETIC_PRIVATE_LOCK"):
            pytest.fail("An invalidated connection must not write")

    connection.begin.assert_not_called()
    assert "operation=check_lock outcome=connection_invalidated" in caplog.text
    assert "driver_code=" not in caplog.text


@pytest.mark.parametrize("body_fails", [False, True])
def test_transaction_exit_identifies_commit_or_rollback_failure(caplog, body_fails):
    connection = MagicMock(invalidated=False)
    connection.scalar.return_value = 1

    def disconnect(*args):
        connection.invalidated = True
        raise OperationalError(None, None, RuntimeError(2013), connection_invalidated=True)

    connection.begin.return_value.__exit__.side_effect = disconnect
    with pytest.raises(ETLError, match="^ingest_lock_lost$"):
        with ingest_transaction(connection, "SYNTHETIC_PRIVATE_LOCK"):
            if body_fails:
                raise ETLError("synthetic_parser_failure")

    operation = "rollback_transaction" if body_fails else "commit_transaction"
    assert f"operation={operation} outcome=connection_invalidated" in caplog.text
    assert "driver_code=2013" in caplog.text
    assert "SYNTHETIC_PRIVATE_LOCK" not in caplog.text
