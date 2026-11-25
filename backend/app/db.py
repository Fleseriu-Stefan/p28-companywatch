from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, text

from app.config import Settings

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def migration_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


def create_database_engine(settings: Settings, *, read_timeout: int = 2) -> Engine:
    return create_engine(
        settings.url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
        pool_timeout=2,
        hide_parameters=True,
        connect_args={"connect_timeout": 2, "read_timeout": read_timeout, "write_timeout": 2},
    )


def is_database_ready(engine: Engine) -> bool:
    expected = set(ScriptDirectory.from_config(migration_config()).get_heads())
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        current = set(MigrationContext.configure(connection).get_current_heads())
    return bool(expected) and current == expected
