import pytest
from alembic import command
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, inspect, text

from app.db import is_database_ready, migration_config
from app.main import create_app

pytestmark = pytest.mark.integration


def test_baseline_and_repeated_migration(engine):
    config = migration_config()
    command.upgrade(config, "0001_baseline")
    with engine.connect() as connection:
        first = MigrationContext.configure(connection).get_current_heads()
    command.upgrade(config, "0001_baseline")
    with engine.connect() as connection:
        second = MigrationContext.configure(connection).get_current_heads()
    assert first == second == ("0001_baseline",)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    assert not is_database_ready(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE m1_upgrade_marker (id INT PRIMARY KEY, value INT)"))
        connection.execute(text("INSERT INTO m1_upgrade_marker VALUES (1, 42)"))
    check_partial_migration_recovery(engine, config)
    check_company_index_migration(engine, config)
    check_auth_migration(engine, config)
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT value FROM m1_upgrade_marker WHERE id=1")) == 42
        assert MigrationContext.configure(connection).get_current_heads() == ("0004_auth_access",)
    assert is_database_ready(engine)


def check_partial_migration_recovery(engine, config):
    def interrupt_before(prefix):
        def interrupt(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().startswith(prefix):
                raise RuntimeError("synthetic_migration_interruption")

        event.listen(Engine, "before_cursor_execute", interrupt)
        try:
            with pytest.raises(RuntimeError, match="synthetic_migration_interruption"):
                command.upgrade(config, "head")
        finally:
            event.remove(Engine, "before_cursor_execute", interrupt)

    interrupt_before("CREATE INDEX ix_etl_staging_version_key")
    partial_tables = inspect(engine).get_table_names()
    assert "etl_staging_rows" in partial_tables
    assert "company_version_rows" not in partial_tables
    with engine.begin() as connection:
        assert MigrationContext.configure(connection).get_current_heads() == ("0001_baseline",)
        connection.execute(text("ALTER TABLE etl_staging_rows ADD COLUMN unexpected INT"))
    with pytest.raises(RuntimeError, match="etl_staging_rows"):
        command.upgrade(config, "head")
    assert inspect(engine).get_table_names() == partial_tables
    assert "unexpected" in {c["name"] for c in inspect(engine).get_columns("etl_staging_rows")}
    assert "ix_etl_staging_version_key" not in {
        index["name"] for index in inspect(engine).get_indexes("etl_staging_rows")
    }
    with engine.begin() as connection:
        assert MigrationContext.configure(connection).get_current_heads() == ("0001_baseline",)
        connection.execute(text("ALTER TABLE etl_staging_rows DROP COLUMN unexpected"))

    interrupt_before("UPDATE alembic_version")
    with engine.begin() as connection:
        assert MigrationContext.configure(connection).get_current_heads() == ("0001_baseline",)
        seed = "SELECT current_version_id FROM dataset_publications WHERE dataset = 'onrc-firme-pj'"
        if connection.execute(text(seed)).first() is None:
            connection.execute(
                text("INSERT INTO dataset_publications (dataset) VALUES ('onrc-firme-pj')")
            )
    command.upgrade(config, "0002_etl")
    assert set(inspect(engine).get_table_names()) == {
        "alembic_version",
        "m1_upgrade_marker",
        "etl_versions",
        "etl_attempts",
        "etl_staging_rows",
        "company_version_rows",
        "dataset_publications",
    }
    with engine.connect() as connection:
        assert connection.execute(text(seed)).all() == [(None,)]


def check_company_index_migration(engine, config):
    def interrupt(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("UPDATE alembic_version"):
            raise RuntimeError("synthetic_index_migration_interruption")

    event.listen(Engine, "before_cursor_execute", interrupt)
    try:
        with pytest.raises(RuntimeError, match="synthetic_index_migration_interruption"):
            command.upgrade(config, "head")
    finally:
        event.remove(Engine, "before_cursor_execute", interrupt)

    indexes = {
        index["name"]: index["column_names"]
        for index in inspect(engine).get_indexes("company_version_rows")
    }
    assert indexes == {
        "ix_company_version_name": ["version_id", "name"],
        "ix_company_version_cui": ["version_id", "cui"],
        "ix_company_version_county_locality": ["version_id", "county", "locality"],
    }
    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_heads() == ("0002_etl",)


def check_auth_migration(engine, config):
    command.upgrade(config, "0003_public_api_indexes")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO etl_versions "
                "(id, edition, resource_id, source_url, license, source_kind, sha256, profile, "
                "schema_hash, state, created_at, manifest) VALUES "
                "('upgrade-test', '2026-11-04', 'fixture', 'https://example.test', "
                "'CC-BY', 'real', "
                "REPEAT('0',64), 'test', REPEAT('1',64), 'published', NOW(), JSON_OBJECT())"
            )
        )
        connection.execute(
            text(
                "UPDATE dataset_publications SET current_version_id = 'upgrade-test' "
                "WHERE dataset = 'onrc-firme-pj'"
            )
        )

    def interrupt(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("CREATE TABLE api_usage"):
            raise RuntimeError("synthetic_auth_migration_interruption")

    event.listen(Engine, "before_cursor_execute", interrupt)
    try:
        with pytest.raises(RuntimeError, match="synthetic_auth_migration_interruption"):
            command.upgrade(config, "head")
    finally:
        event.remove(Engine, "before_cursor_execute", interrupt)
    assert {"users", "api_keys"} <= set(inspect(engine).get_table_names())
    assert "api_usage" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    with engine.begin() as connection:
        pointer = connection.scalar(
            text(
                "SELECT current_version_id FROM dataset_publications "
                "WHERE dataset = 'onrc-firme-pj'"
            )
        )
        assert pointer == "upgrade-test"
        connection.execute(text("UPDATE dataset_publications SET current_version_id = NULL"))
        connection.execute(text("DELETE FROM etl_versions WHERE id = 'upgrade-test'"))


def test_real_mysql_readiness_and_schema_mismatch(engine):
    with TestClient(create_app(engine)) as client:
        assert client.get("/health/ready").status_code == 200
        with engine.begin() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            connection.execute(text("UPDATE alembic_version SET version_num = 'outdated'"))
        try:
            response = client.get("/health/ready")
            assert response.status_code == 503
            assert response.json() == {"status": "not_ready"}
        finally:
            with engine.begin() as connection:
                connection.execute(
                    text("UPDATE alembic_version SET version_num = :revision"),
                    {"revision": revision},
                )
