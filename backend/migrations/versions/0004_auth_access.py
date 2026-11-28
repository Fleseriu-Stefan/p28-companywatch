"""Add accounts, API key digests and request counters."""

from alembic import op
from sqlalchemy import (
    BINARY,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    inspect,
)
from sqlalchemy.schema import CreateTable

revision = "0004_auth_access"
down_revision = "0003_public_api_indexes"
branch_labels = None
depends_on = None

# Frozen schema for this revision.
metadata = MetaData()
options = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

users = Table(
    "users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(254, collation="utf8mb4_0900_bin"), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("role", Enum("curator", "admin"), nullable=False),
    Column("active", Boolean, nullable=False),
    **options,
)
api_keys = Table(
    "api_keys",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("owner_id", ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("name", String(120), nullable=False),
    Column("key_prefix", String(12), nullable=False),
    Column("key_hash", BINARY(32), nullable=False, unique=True),
    Column("daily_quota", Integer, nullable=False),
    Column("revoked_at", DateTime),
    CheckConstraint("daily_quota > 0", name="ck_api_keys_positive_quota"),
    **options,
)
api_usage = Table(
    "api_usage",
    metadata,
    Column("key_id", ForeignKey("api_keys.id", ondelete="CASCADE"), primary_key=True),
    Column("window", Enum("minute", "day"), primary_key=True),
    Column("window_start", DateTime, nullable=False),
    Column("count", Integer, nullable=False),
    **options,
)


def column_signature(name, column_type, nullable, dialect):
    rendered = column_type.compile(dialect=dialect).upper().replace(" CHARACTER SET UTF8MB4", "")
    if rendered in {"BOOLEAN", "BOOL"}:
        rendered = "TINYINT(1)"
    return name, rendered, nullable


def validate_existing(connection, inspector, table):
    expected = [
        column_signature(column.name, column.type, column.nullable, connection.dialect)
        for column in table.columns
    ]
    actual = [
        column_signature(column["name"], column["type"], column["nullable"], connection.dialect)
        for column in inspector.get_columns(table.name)
    ]
    if actual != expected:
        raise RuntimeError(f"Cannot resume 0004_auth_access: incompatible {table.name} columns.")
    primary_key = inspector.get_pk_constraint(table.name)["constrained_columns"]
    uniques = {
        tuple(index["column_names"])
        for index in inspector.get_indexes(table.name)
        if index["unique"]
    }
    foreign_keys = {
        (
            tuple(fk["constrained_columns"]),
            fk["referred_table"],
            tuple(fk["referred_columns"]),
            fk["options"].get("ondelete"),
        )
        for fk in inspector.get_foreign_keys(table.name)
    }
    expected_fks = {
        (
            tuple(fk.column_keys),
            fk.elements[0].column.table.name,
            tuple(element.column.name for element in fk.elements),
            fk.ondelete,
        )
        for fk in table.foreign_key_constraints
    }
    checks = {check["name"] for check in inspector.get_check_constraints(table.name)}
    if (
        primary_key != list(table.primary_key.columns.keys())
        or uniques != {(column.name,) for column in table.columns if column.unique}
        or foreign_keys != expected_fks
        or checks != ({"ck_api_keys_positive_quota"} if table is api_keys else set())
        or inspector.get_table_options(table.name).get("mysql_engine") != "InnoDB"
    ):
        raise RuntimeError(
            f"Cannot resume 0004_auth_access: incompatible {table.name} constraints."
        )


def upgrade() -> None:
    if op.get_context().as_sql:
        for table in metadata.sorted_tables:
            op.execute(CreateTable(table))
        return

    connection = op.get_bind()
    inspector = inspect(connection)
    existing = set(inspector.get_table_names())
    views = set(inspector.get_view_names())
    pending = []
    for table in metadata.sorted_tables:
        if table.name in views or (table.name in existing and pending):
            raise RuntimeError(f"Cannot resume 0004_auth_access: unexpected {table.name} object.")
        if table.name in existing:
            validate_existing(connection, inspector, table)
        else:
            pending.append(table)
    for table in pending:
        op.execute(CreateTable(table))


def downgrade() -> None:
    for table in reversed(metadata.sorted_tables):
        op.drop_table(table.name)
