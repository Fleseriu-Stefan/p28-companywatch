from sqlalchemy import Integer, Numeric, and_, func, or_, select

from app.api.onrc_models import EditionSource, QualityCounts
from app.etl.models import companies, publications, versions
from app.etl.service import DATASET

PUBLISHED = (versions.c.state == "published") & (versions.c.source_kind == "real")
NAME_COLLATION = "utf8mb4_0900_ai_ci"


def current_version_id(connection):
    return connection.scalar(
        select(versions.c.id)
        .join(publications, publications.c.current_version_id == versions.c.id)
        .where(publications.c.dataset == DATASET, PUBLISHED)
    )


def published_versions(connection):
    return (
        connection.execute(
            select(
                versions.c.id,
                versions.c.edition,
                versions.c.report,
                versions.c.resource_id,
                versions.c.source_url,
                versions.c.license,
            )
            .where(PUBLISHED)
            .order_by(versions.c.edition, versions.c.id)
        )
        .mappings()
        .all()
    )


def edition_source(version):
    return EditionSource(
        resource_id=version["resource_id"], url=version["source_url"], license=version["license"]
    )


def get_version(connection, version_id):
    return (
        connection.execute(select(versions).where(PUBLISHED, versions.c.id == version_id))
        .mappings()
        .one_or_none()
    )


def version_as_of(connection, edition):
    return (
        connection.execute(
            select(versions)
            .where(PUBLISHED, versions.c.edition <= edition)
            .order_by(versions.c.edition.desc(), versions.c.id.desc())
            .limit(1)
        )
        .mappings()
        .one_or_none()
    )


def next_edition(connection, edition):
    return connection.scalar(
        select(func.min(versions.c.edition)).where(PUBLISHED, versions.c.edition > edition)
    )


def lookup_company(connection, version_id, euid):
    return (
        connection.execute(
            select(companies).where(companies.c.version_id == version_id, companies.c.euid == euid)
        )
        .mappings()
        .one_or_none()
    )


def company_search(version_id, query, cursor):
    fields = companies.c
    name = fields.name.collate(NAME_COLLATION)
    # ETL retains DD/MM/YYYY with an optional time. Sort on the calendar date.
    date_key = func.date_format(
        func.str_to_date(func.substring_index(fields.registration_date, " ", 1), "%d/%m/%Y"),
        "%Y-%m-%d",
    )
    sort_key = name if query.sort == "name" else date_key
    statement = select(companies, sort_key.label("sort_value")).where(
        fields.version_id == version_id
    )
    if query.name is not None:
        match = name.startswith if query.name_match == "prefix" else name.contains
        statement = statement.where(match(query.name, autoescape=True))
    for column in (fields.cui, fields.legal_form, fields.county, fields.locality):
        value = getattr(query, column.name)
        if value is not None:
            statement = statement.where(column == value)
    if cursor:
        after_euid = fields.euid > cursor.euid
        if cursor.sort_value is None:
            statement = statement.where(sort_key.is_(None), after_euid)
        else:
            statement = statement.where(
                or_(
                    sort_key > cursor.sort_value,
                    and_(sort_key == cursor.sort_value, after_euid),
                    sort_key.is_(None),
                )
            )
    return statement.order_by(sort_key.is_(None), sort_key, fields.euid).limit(query.limit + 1)


def group_counts(connection, version_ids, *, by_county=False):
    dimensions = [companies.c.legal_form]
    if by_county:
        dimensions.append(companies.c.county)
    grouping = [versions.c.edition, companies.c.version_id, *dimensions]
    statement = (
        select(*grouping, func.count().label("count"))
        .join(versions, versions.c.id == companies.c.version_id)
        .where(companies.c.version_id.in_(version_ids))
        .group_by(*grouping)
        .order_by(*grouping)
    )
    return connection.execute(statement).mappings().all()


def quality_aggregates(connection, version_ids):
    def count(key):
        value = func.json_unquote(func.json_extract(versions.c.report, f"$.{key}"))
        return func.nullif(value, "null").cast(Integer)

    counts = [func.sum(count(key)).label(key) for key in QualityCounts.model_fields]
    by_edition = (
        connection.execute(
            select(versions.c.edition, versions.c.id.label("version_id"), *counts)
            .where(versions.c.id.in_(version_ids))
            .group_by(versions.c.edition, versions.c.id)
            .order_by(versions.c.edition, versions.c.id)
        )
        .mappings()
        .all()
    )
    rate = count("quarantined_records").cast(Numeric(30, 15)) / func.nullif(
        count("source_records"), 0
    )
    average = connection.scalar(select(func.avg(rate)).where(versions.c.id.in_(version_ids)))
    return by_edition, average
