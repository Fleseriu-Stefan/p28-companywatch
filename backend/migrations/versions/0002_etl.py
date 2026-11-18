"""Add versioned ETL tables without changing existing M1 data."""

import sqlalchemy as sa
from alembic import op

revision = "0002_etl"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def fields(key_primary=False):
    # Frozen migration snapshot: future application model edits cannot rewrite history.
    binary = "utf8mb4_0900_bin"
    return [
        sa.Column("euid", sa.String(255, collation=binary), primary_key=key_primary),
        sa.Column("cui", sa.String(64, collation=binary)),
        sa.Column("registration", sa.String(255, collation=binary)),
        *(
            sa.Column(name, sa.Text(collation=binary))
            for name in ("name", "legal_form", "county", "locality")
        ),
        sa.Column("registration_date", sa.String(64, collation=binary)),
    ]


def migration_schema():
    metadata = sa.MetaData()
    options = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    sa.Table(
        "etl_versions",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("edition", sa.String(10), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("license", sa.String(32), nullable=False),
        sa.Column("source_kind", sa.String(16), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("profile", sa.String(64), nullable=False),
        sa.Column("schema_hash", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("manifest", sa.JSON, nullable=False),
        sa.Column("report", sa.JSON),
        sa.Column("report_hash", sa.String(64)),
        sa.Column("prepared_hash", sa.String(64)),
        sa.Column("approval", sa.String(64)),
        sa.UniqueConstraint("source_kind", "resource_id", "sha256", "profile", name="uq_etl_input"),
        **options,
    )
    sa.Table(
        "etl_attempts",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("etl_versions.id"), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("failure_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime, nullable=False),
        **options,
    )
    sa.Table(
        "etl_staging_rows",
        metadata,
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("etl_versions.id"), nullable=False),
        sa.Column("source_line", sa.BigInteger, nullable=False),
        sa.Column("valid", sa.Boolean, nullable=False),
        sa.Column("excluded", sa.Boolean, nullable=False),
        sa.Column("key_digest", sa.String(64)),
        sa.Column("errors", sa.JSON, nullable=False),
        *fields(),
        **options,
    )
    sa.Table(
        "company_version_rows",
        metadata,
        sa.Column("version_id", sa.String(36), sa.ForeignKey("etl_versions.id"), primary_key=True),
        *fields(key_primary=True),
        **options,
    )
    sa.Table(
        "dataset_publications",
        metadata,
        sa.Column("dataset", sa.String(64), primary_key=True),
        sa.Column("current_version_id", sa.String(36), sa.ForeignKey("etl_versions.id")),
        **options,
    )
    staging = metadata.tables["etl_staging_rows"]
    staging_index = sa.Index(
        "ix_etl_staging_version_key", staging.c.version_id, staging.c.key_digest
    )
    return metadata, staging_index


def incompatible(table, detail):
    raise RuntimeError(f"Cannot resume 0002_etl: {table} has incompatible {detail}")


def column_type(column_type, dialect):
    # Reflection can spell out the inherited charset on columns with a collation.
    rendered = column_type.compile(dialect=dialect).upper().replace(" CHARACTER SET UTF8MB4", "")
    return "TINYINT(1)" if rendered in {"BOOL", "BOOLEAN"} else rendered


def validate_table(connection, inspector, table, staging_index):
    name = table.name
    storage = connection.execute(
        sa.text(
            "SELECT ENGINE, TABLE_COLLATION FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :name"
        ),
        {"name": name},
    ).one()
    if storage[0] != "InnoDB" or not (storage[1] or "").startswith("utf8mb4_"):
        incompatible(name, "storage")
    reflected = inspector.get_columns(name)
    expected = [
        (
            column.name,
            column_type(column.type, connection.dialect),
            column.nullable,
            None,
            column.autoincrement is True,
            getattr(column.type, "collation", None) or None,
        )
        for column in table.columns
    ]
    actual = [
        (
            column["name"],
            column_type(column["type"], connection.dialect),
            column["nullable"],
            column["default"],
            column.get("autoincrement", False),
            getattr(column["type"], "collation", None) or None,
        )
        for column in reflected
    ]
    if actual != expected:
        incompatible(name, "columns")
    if inspector.get_pk_constraint(name)["constrained_columns"] != list(
        table.primary_key.columns.keys()
    ):
        incompatible(name, "primary key")

    expected_fks = {
        (
            tuple(element.parent.name for element in fk.elements),
            fk.elements[0].column.table.name,
            tuple(element.column.name for element in fk.elements),
        )
        for fk in table.foreign_key_constraints
    }
    fks = inspector.get_foreign_keys(name)
    actual_fks = {
        (tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]))
        for fk in fks
    }
    if (
        actual_fks != expected_fks
        or len(fks) != len(expected_fks)
        or any(
            fk.get("referred_schema") not in {None, connection.engine.url.database}
            or any(
                action not in {"NO ACTION", "RESTRICT"} for action in fk.get("options", {}).values()
            )
            for fk in fks
        )
    ):
        incompatible(name, "foreign keys")

    required_indexes = {
        constraint.name: tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, sa.UniqueConstraint)
    }
    for index in inspector.get_indexes(name):
        index_name = index["name"]
        columns = tuple(index["column_names"])
        if index_name in required_indexes:
            expected_index = (required_indexes.pop(index_name), True)
        elif name == staging_index.table.name and index_name == staging_index.name:
            expected_index = (tuple(staging_index.columns.keys()), False)
        elif any(columns == fk[0] for fk in expected_fks) and index_name == columns[0]:
            # MySQL creates an index for a foreign key without a covering index.
            expected_index = (columns, False)
        else:
            incompatible(name, "indexes")
        if (columns, bool(index["unique"])) != expected_index or index.get("dialect_options"):
            incompatible(name, "indexes")
    if required_indexes or inspector.get_check_constraints(name):
        incompatible(name, "constraints")


def pending_steps(connection, metadata, staging_index):
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    views = set(inspector.get_view_names())
    missing = []
    for table in metadata.tables.values():
        if table.name in views or (table.name in tables and missing):
            incompatible(table.name, "migration order or object type")
        if table.name in tables:
            validate_table(connection, inspector, table, staging_index)
        else:
            missing.append(sa.schema.CreateTable(table))

        if table is staging_index.table and (
            table.name not in tables
            or not any(i["name"] == staging_index.name for i in inspector.get_indexes(table.name))
        ):
            missing.append(sa.schema.CreateIndex(staging_index))

    publications = metadata.tables["dataset_publications"]
    if publications.name in tables:
        rows = connection.execute(sa.select(publications.c.dataset)).scalars().all()
        if rows and rows != ["onrc-firme-pj"]:
            incompatible(publications.name, "publication seed")
    else:
        rows = []
    if not rows:
        missing.append(publications.insert().values(dataset="onrc-firme-pj"))
    return missing


def upgrade() -> None:
    metadata, staging_index = migration_schema()
    if op.get_context().as_sql:
        for table in metadata.tables.values():
            op.execute(sa.schema.CreateTable(table))
            if table is staging_index.table:
                op.execute(sa.schema.CreateIndex(staging_index))
        op.execute("INSERT INTO dataset_publications (dataset) VALUES ('onrc-firme-pj')")
        return

    connection = op.get_bind()
    for step in pending_steps(connection, metadata, staging_index):
        connection.execute(step)
    if pending_steps(connection, metadata, staging_index):
        raise RuntimeError("Cannot complete 0002_etl: migration steps are still missing")


def downgrade() -> None:
    # Downgrade is destructive and is intentionally unavailable for retained snapshots.
    raise RuntimeError("M2 downgrade requires an explicitly approved data-retention plan")
