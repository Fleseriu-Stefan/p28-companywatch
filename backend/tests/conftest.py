import os

import pytest

from app.config import Settings
from app.db import create_database_engine


@pytest.fixture
def engine():
    """Integration tests refuse the development database, even when selected manually."""
    settings = Settings.from_env()
    if not (
        settings.database.endswith("_test")
        and os.environ.get("ETL_TEST_PROJECT", "").startswith("companywatch-check-")
    ):
        pytest.fail("Integration tests require the isolated verification project")
    database_engine = create_database_engine(settings)
    yield database_engine
    database_engine.dispose()
