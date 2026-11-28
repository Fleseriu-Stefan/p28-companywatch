"""Index published company search and filters without changing snapshot rows."""

from alembic import op
from sqlalchemy import text

revision = "0003_public_api_indexes"
down_revision = "0002_etl"
branch_labels = None
depends_on = None

TABLE = "company_version_rows"
INDEXES = {
    "ix_company_version_name": (("version_id", None), ("name", 191)),
    "ix_company_version_cui": (("version_id", None), ("cui", None)),
    "ix_company_version_county_locality": (
        ("version_id", None),
        ("county", 191),
        ("locality", 191),
    ),
}


def upgrade() -> None:
    # MySQL commits DDL separately from the Alembic revision. One atomic ALTER
    # and a catalog check let the migration resume after an interrupted stamp.
    if not op.get_context().as_sql:
        rows = op.get_bind().execute(
            text(
                "SELECT INDEX_NAME, COLUMN_NAME, SUB_PART, NON_UNIQUE "
                "FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name "
                "ORDER BY INDEX_NAME, SEQ_IN_INDEX"
            ),
            {"table_name": TABLE},
        )
        existing = {}
        for index, column, length, non_unique in rows:
            if index in INDEXES:
                if not non_unique:
                    raise RuntimeError(f"Unexpected unique company index: {index}")
                existing.setdefault(index, []).append((column, length))
        if existing:
            if {name: tuple(columns) for name, columns in existing.items()} != INDEXES:
                raise RuntimeError("Unexpected company search index definitions")
            return

    additions = []
    for name, columns in INDEXES.items():
        indexed = ", ".join(
            f"{column}({length})" if length else column for column, length in columns
        )
        additions.append(f"ADD INDEX {name} ({indexed})")
    op.execute(f"ALTER TABLE {TABLE} " + ", ".join(additions))


def downgrade() -> None:
    op.execute(f"ALTER TABLE {TABLE} " + ", ".join(f"DROP INDEX {name}" for name in INDEXES))
