from unittest.mock import Mock

import pytest

from app.config import Settings
from tests import test_etl_database


@pytest.mark.parametrize(
    ("database", "project"),
    [
        ("companywatch", "companywatch-check-0000000000000000"),
        ("companywatch_test", "companywatch"),
    ],
)
def test_ingest_engine_rejects_unsafe_target_before_engine_creation(monkeypatch, database, project):
    settings = Settings(database=database, user="synthetic", password="synthetic")
    create_engine = Mock()
    monkeypatch.setattr(Settings, "from_env", lambda: settings)
    monkeypatch.setenv("ETL_TEST_PROJECT", project)
    monkeypatch.setattr(test_etl_database, "create_database_engine", create_engine)

    fixture = test_etl_database.ingest_engine.__wrapped__()
    try:
        with pytest.raises(pytest.fail.Exception, match="isolated verification project"):
            next(fixture)
    finally:
        fixture.close()
    create_engine.assert_not_called()
