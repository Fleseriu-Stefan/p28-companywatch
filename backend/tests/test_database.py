import pytest
from alembic import command
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.config import Settings
from app.db import create_database_engine, is_database_ready, migration_config
from app.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def engine():
    database_engine = create_database_engine(Settings.from_env())
    yield database_engine
    database_engine.dispose()


def test_baseline_and_repeated_migration(engine):
    config = migration_config()
    command.upgrade(config, "head")
    with engine.connect() as connection:
        first = MigrationContext.configure(connection).get_current_heads()
    command.upgrade(config, "head")
    with engine.connect() as connection:
        second = MigrationContext.configure(connection).get_current_heads()
    assert first == second == ("0001_baseline",)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    assert is_database_ready(engine)


def test_real_mysql_readiness_and_schema_mismatch(engine):
    with TestClient(create_app(engine)) as client:
        assert client.get("/health/ready").status_code == 200
        with engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num = 'outdated'"))
        try:
            response = client.get("/health/ready")
            assert response.status_code == 503
            assert response.json() == {"status": "not_ready"}
        finally:
            with engine.begin() as connection:
                connection.execute(text("UPDATE alembic_version SET version_num = '0001_baseline'"))
