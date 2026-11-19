from contextlib import contextmanager

from sqlalchemy import case, func, literal, or_, select, union_all

from app.etl.errors import ETLError
from app.etl.models import companies, versions
from app.etl.source import RETAINED

FIELDS = tuple(RETAINED.values())


def require_published(connection, old_id, new_id, *, allow_synthetic):
    requested = {old_id, new_id}
    states = connection.execute(
        select(versions.c.id, versions.c.state, versions.c.source_kind).where(
            versions.c.id.in_(requested)
        )
    ).all()
    if len(states) != len(requested) or any(row.state != "published" for row in states):
        raise ETLError("published_versions_required")
    if not allow_synthetic and any(row.source_kind != "real" for row in states):
        raise ETLError("synthetic_not_allowed")


def comparison(old_id, new_id):
    old = select(companies).where(companies.c.version_id == old_id).subquery("old_rows")
    new = select(companies).where(companies.c.version_id == new_id).subquery("new_rows")
    match = old.c.euid == new.c.euid
    changed = {
        field: ~old.c[field].is_not_distinct_from(new.c[field])
        for field in FIELDS
        if field != "euid"
    }
    return old, new, match, changed


def compare(engine, old_id, new_id, *, allow_synthetic=False):
    """Every count is computed in MySQL; no application-side row matching."""
    with engine.connect() as connection:
        require_published(connection, old_id, new_id, allow_synthetic=allow_synthetic)
        old, new, match, changed = comparison(old_id, new_id)
        added = connection.scalar(
            select(func.count()).select_from(new.outerjoin(old, match)).where(old.c.euid.is_(None))
        )
        removed = connection.scalar(
            select(func.count()).select_from(old.outerjoin(new, match)).where(new.c.euid.is_(None))
        )
        joined = old.join(new, match)
        modified = connection.scalar(
            select(func.count()).select_from(joined).where(or_(*changed.values()))
        )
        common = connection.scalar(select(func.count()).select_from(joined))
        by_field = {
            field: connection.scalar(select(func.count()).select_from(joined).where(condition))
            for field, condition in changed.items()
        }
    return {
        "old_version": old_id,
        "new_version": new_id,
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": common - modified,
        "by_field": by_field,
    }


def detail_statement(old_id, new_id):
    old, new, match, changed = comparison(old_id, new_id)
    sides = [
        rows.c[field].label(f"{side}_{field}")
        for side, rows in (("previous", old), ("current", new))
        for field in FIELDS
    ]
    old_side = select(
        old.c.euid.label("euid"),
        case(
            (new.c.euid.is_(None), "removed"),
            (or_(*changed.values()), "modified"),
            else_="unchanged",
        ).label("change_type"),
        *sides,
        *(
            (new.c.euid.is_not(None) & flag).label(f"changed_{field}")
            for field, flag in changed.items()
        ),
    ).select_from(old.outerjoin(new, match))
    added = (
        select(new.c.euid, literal("added"), *sides, *(literal(False) for _ in changed))
        .select_from(new.outerjoin(old, match))
        .where(old.c.euid.is_(None))
    )
    return union_all(old_side, added)


def detail_row(row):
    return {
        "euid": row["euid"],
        "change_type": row["change_type"],
        "previous": (
            {field: row[f"previous_{field}"] for field in FIELDS}
            if row["previous_euid"] is not None
            else None
        ),
        "current": (
            {field: row[f"current_{field}"] for field in FIELDS}
            if row["current_euid"] is not None
            else None
        ),
        "changed_fields": tuple(
            field for field in FIELDS if field != "euid" and row[f"changed_{field}"]
        ),
    }


@contextmanager
def compare_details(engine, old_id, new_id, *, allow_synthetic=False):
    """Stream SQL-classified rows while the caller owns the context."""
    with engine.connect() as connection:
        require_published(connection, old_id, new_id, allow_synthetic=allow_synthetic)
        statement = detail_statement(old_id, new_id)
        with connection.execute(statement, execution_options={"yield_per": 256}) as result:
            yield (detail_row(row) for row in result.mappings())
