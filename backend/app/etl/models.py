from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)

metadata = MetaData()
BINARY_COLLATION = "utf8mb4_0900_bin"


def fields(nullable=True, key_primary=False):
    return [
        Column(
            "euid",
            String(255, collation=BINARY_COLLATION),
            nullable=nullable,
            primary_key=key_primary,
        ),
        Column("cui", String(64, collation=BINARY_COLLATION)),
        Column("registration", String(255, collation=BINARY_COLLATION)),
        Column("name", Text(collation=BINARY_COLLATION)),
        Column("legal_form", Text(collation=BINARY_COLLATION)),
        Column("county", Text(collation=BINARY_COLLATION)),
        Column("locality", Text(collation=BINARY_COLLATION)),
        Column("registration_date", String(64, collation=BINARY_COLLATION)),
    ]


versions = Table(
    "etl_versions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("edition", String(10), nullable=False),
    Column("resource_id", String(64), nullable=False),
    Column("source_url", Text, nullable=False),
    Column("license", String(32), nullable=False),
    Column("source_kind", String(16), nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("profile", String(64), nullable=False),
    Column("schema_hash", String(64), nullable=False),
    Column("state", String(16), nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("manifest", JSON, nullable=False),
    Column("report", JSON),
    Column("report_hash", String(64)),
    Column("prepared_hash", String(64)),
    Column("approval", String(64)),
    UniqueConstraint("source_kind", "resource_id", "sha256", "profile", name="uq_etl_input"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)
attempts = Table(
    "etl_attempts",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("version_id", ForeignKey("etl_versions.id"), nullable=False),
    Column("state", String(16), nullable=False),
    Column("failure_code", String(64)),
    Column("created_at", DateTime, nullable=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)
staging = Table(
    "etl_staging_rows",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("version_id", ForeignKey("etl_versions.id"), nullable=False),
    Column("source_line", BigInteger, nullable=False),
    Column("valid", Boolean, nullable=False),
    Column("excluded", Boolean, nullable=False),
    Column("key_digest", String(64)),
    Column("errors", JSON, nullable=False),
    *fields(),
    Index("ix_etl_staging_version_key", "version_id", "key_digest"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)
companies = Table(
    "company_version_rows",
    metadata,
    Column("version_id", ForeignKey("etl_versions.id"), primary_key=True),
    *fields(nullable=False, key_primary=True),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)
Index(
    "ix_company_version_name",
    companies.c.version_id,
    companies.c.name,
    mysql_length={"name": 191},
)
Index("ix_company_version_cui", companies.c.version_id, companies.c.cui)
Index(
    "ix_company_version_county_locality",
    companies.c.version_id,
    companies.c.county,
    companies.c.locality,
    mysql_length={"county": 191, "locality": 191},
)
# One physical row per version/key; duplicate groups exist only in staging.
publications = Table(
    "dataset_publications",
    metadata,
    Column("dataset", String(64), primary_key=True),
    Column("current_version_id", ForeignKey("etl_versions.id")),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)
