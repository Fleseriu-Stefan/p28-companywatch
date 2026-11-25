from unittest.mock import patch

from app.config import Settings
from app.db import create_database_engine


def test_database_engine_keeps_short_default_timeouts():
    settings = Settings(database="companywatch_test", user="synthetic", password="synthetic")
    with patch("app.db.create_engine") as create_engine:
        create_database_engine(settings)

    assert create_engine.call_args.kwargs["connect_args"] == {
        "connect_timeout": 2,
        "read_timeout": 2,
        "write_timeout": 2,
    }
    assert create_engine.call_args.kwargs["pool_timeout"] == 2


def test_database_engine_accepts_ingest_read_timeout_without_changing_other_limits():
    settings = Settings(database="companywatch_test", user="synthetic", password="synthetic")
    with patch("app.db.create_engine") as create_engine:
        create_database_engine(settings, read_timeout=120)

    assert create_engine.call_args.kwargs["connect_args"] == {
        "connect_timeout": 2,
        "read_timeout": 120,
        "write_timeout": 2,
    }
    assert create_engine.call_args.kwargs["pool_timeout"] == 2
