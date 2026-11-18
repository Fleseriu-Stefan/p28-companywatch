from sqlalchemy import func, or_, select

from app.etl.errors import ETLError
from app.etl.models import companies, versions
from app.etl.source import RETAINED


def compare(engine, old_id, new_id, *, allow_synthetic=False):
    """Every count is computed in MySQL; no application-side row matching."""
    with engine.connect() as connection:
        states = connection.execute(
            select(versions.c.id, versions.c.state, versions.c.source_kind).where(
                versions.c.id.in_({old_id, new_id})
            )
        ).all()
        if len(states) != len({old_id, new_id}) or any(row.state != "published" for row in states):
            raise ETLError("published_versions_required")
        if not allow_synthetic and any(row.source_kind != "real" for row in states):
            raise ETLError("synthetic_not_allowed")
        old = select(companies).where(companies.c.version_id == old_id).subquery("old_rows")
        new = select(companies).where(companies.c.version_id == new_id).subquery("new_rows")
        match = old.c.euid == new.c.euid
        added = connection.scalar(
            select(func.count()).select_from(new.outerjoin(old, match)).where(old.c.euid.is_(None))
        )
        removed = connection.scalar(
            select(func.count()).select_from(old.outerjoin(new, match)).where(new.c.euid.is_(None))
        )
        changed = {
            field: ~old.c[field].is_not_distinct_from(new.c[field])
            for field in RETAINED.values()
            if field != "euid"
        }
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
