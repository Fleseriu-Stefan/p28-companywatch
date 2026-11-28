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
)

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
