from alembic import context

from app.config import Settings
from app.db import create_database_engine
from app.etl.models import metadata

target_metadata = metadata


def run_migrations() -> None:
    settings = Settings.from_env()
    if context.is_offline_mode():
        context.configure(
            url=settings.url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    # Index builds on populated snapshots run longer than normal API reads.
    engine = create_database_engine(settings, read_timeout=120)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


run_migrations()
