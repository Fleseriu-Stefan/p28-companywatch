import os

import pytest

from app.config import Settings
from app.db import create_database_engine


def isolated_test_settings():
    """Integration tests refuse the development database, even when selected manually."""
    settings = Settings.from_env()
    if not (
        settings.database.endswith("_test")
        and os.environ.get("ETL_TEST_PROJECT", "").startswith("companywatch-check-")
    ):
        pytest.fail("Integration tests require the isolated verification project")
    return settings


@pytest.fixture
def engine():
    database_engine = create_database_engine(isolated_test_settings())
    yield database_engine
    database_engine.dispose()
