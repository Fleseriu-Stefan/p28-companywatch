import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.api import onrc_queries as queries
from app.api.onrc_models import (
    AggregatesResponse,
    ChangeType,
    Company,
    CompanyPage,
    CountyCount,
    DiffPage,
    DiffRow,
    EditionQuality,
    LegalFormCount,
    ObservedCompany,
    PublishedVersion,
    QualityCounts,
    VersionsResponse,
)
from app.etl.errors import ETLError
from app.etl.service import Pipeline, digest_json

ETAG_HEADER = {"ETag": {"schema": {"type": "string"}, "description": "Response validator."}}
router = APIRouter(
    tags=["Published ONRC data"],
    responses={
        200: {"headers": ETAG_HEADER},
        304: {"description": "Representation unchanged.", "headers": ETAG_HEADER},
        404: {"description": "Published version is unavailable."},
        503: {"description": "Published data is temporarily unavailable."},
    },
)
ENTITY_TAG = re.compile(r'(?:W/)?"[\x21\x23-\x7e\x80-\xff]*"')
IfNoneMatch = Annotated[
    str | None, Header(alias="If-None-Match", description="Cached ETag for conditional GET.")
]
PageLimit = Annotated[int, Query(ge=1, le=200)]
CursorParam = Annotated[str | None, Query(max_length=16384, description="Opaque next_cursor.")]


class SearchParams(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    name_match: Literal["prefix", "contains"] = "contains"
    cui: str | None = Field(None, min_length=1, max_length=64)
    legal_form: str | None = Field(None, min_length=1, max_length=255)
    county: str | None = Field(None, min_length=1, max_length=255)
    locality: str | None = Field(None, min_length=1, max_length=255)
    sort: Literal["name", "registration_date"] = "name"
    version: UUID | None = None
    limit: int = Field(50, ge=1, le=200)
    cursor: str | None = Field(None, max_length=16384, description="Opaque next_cursor.")


class PageCursor(BaseModel):
    scope: str
    version_id: UUID
    euid: str = Field(min_length=1, max_length=255)
    sort_value: str | None = None

    def encode(self):
        return urlsafe_b64encode(self.model_dump_json().encode()).decode().rstrip("=")


def decode_cursor(token, scope):
    if token is None:
        return None
    try:
        raw = urlsafe_b64decode(token + "=" * (-len(token) % 4))
        cursor = PageCursor.model_validate_json(raw)
        if cursor.scope == scope and cursor.encode() == token:
            return cursor
    except ValueError:
        pass
    raise HTTPException(422, "Invalid cursor for this query.")


def read_connection(request: Request):
    try:
        # Read the pointer, publication metadata and rows from one MySQL snapshot.
        with request.app.state.engine.connect() as connection:
            yield connection.execution_options(isolation_level="REPEATABLE READ")
    except SQLAlchemyError:
        raise HTTPException(503, "Published data is temporarily unavailable.") from None


Database = Annotated[Connection, Depends(read_connection)]


def conditional(request, response, if_none_match, body, current=None):
    tag = f'W/"{digest_json([current, body.model_dump(mode="json")])}"'
    cache = "private, no-cache" if getattr(request.state, "external_api", False) else "no-cache"
    headers = {"ETag": tag, "Cache-Control": cache}
    supplied = if_none_match or ""
    if supplied.strip() == "*" or any(
        value.removeprefix("W/") == tag.removeprefix("W/") for value in ENTITY_TAG.findall(supplied)
    ):
        return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return body


@router.get("/versions", response_model=VersionsResponse)
def list_versions(
    request: Request, database: Database, response: Response, if_none_match: IfNoneMatch = None
):
    """List the available ONRC editions and identify the current one."""
    current = queries.current_version_id(database)
    items = [
        PublishedVersion(
            version_id=version["id"],
            edition=version["edition"],
            source=queries.edition_source(version),
            counts=QualityCounts.model_validate(version["report"] or {}),
            current=version["id"] == current,
        )
        for version in queries.published_versions(database)
    ]
    return conditional(request, response, if_none_match, VersionsResponse(items=items), current)


@router.get("/companies", response_model=CompanyPage)
def list_companies(
    request: Request,
    database: Database,
    response: Response,
    query: Annotated[SearchParams, Query()],
    if_none_match: IfNoneMatch = None,
):
    """Search a published snapshot. Repeat the same query settings with next_cursor."""
    scope = digest_json(["companies", query.model_dump(mode="json", exclude={"cursor"})])
    cursor = decode_cursor(query.cursor, scope)
    explicit = str(query.version) if query.version else None
    if cursor and explicit and str(cursor.version_id) != explicit:
        raise HTTPException(422, "Invalid cursor for this version.")
    current = queries.current_version_id(database) if explicit is None and cursor is None else None
    version = str(cursor.version_id) if cursor else explicit or current
    if not version or queries.get_version(database, version) is None:
        raise HTTPException(404, "Published version is unavailable.")
    rows = database.execute(queries.company_search(version, query, cursor)).mappings().all()
    page = rows[: query.limit]
    next_cursor = None
    if len(rows) > query.limit:
        last = page[-1]
        next_cursor = PageCursor(
            scope=scope, version_id=version, euid=last["euid"], sort_value=last["sort_value"]
        ).encode()
    body = CompanyPage(
        version_id=version,
        items=[Company.model_validate(item) for item in page],
        next_cursor=next_cursor,
    )
    return conditional(request, response, if_none_match, body, current)


@router.get("/companies/{euid:path}", response_model=ObservedCompany)
def company_history(
    request: Request,
    database: Database,
    response: Response,
    euid: Annotated[str, Path(min_length=1, max_length=255)],
    as_of: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    if_none_match: IfNoneMatch = None,
):
    """Read an observed state at an edition date or in the current published snapshot."""
    current = None
    if as_of is None:
        current = queries.current_version_id(database)
        version = queries.get_version(database, current) if current else None
    else:
        try:
            requested = date.fromisoformat(as_of)
        except ValueError:
            raise HTTPException(422, "as_of must be a calendar date in YYYY-MM-DD form.") from None
        version = queries.version_as_of(database, requested.isoformat())

    if version is None:
        body = ObservedCompany(status="unavailable")
    else:
        row = queries.lookup_company(database, version["id"], euid)
        body = ObservedCompany(
            status="present" if row else "absent",
            version_id=version["id"],
            source=queries.edition_source(version),
            valid_from=version["edition"],
            valid_to=queries.next_edition(database, version["edition"]),
            company=Company.model_validate(row) if row else None,
        )
    return conditional(request, response, if_none_match, body, current)


@router.get("/versions/{a}/diff/{b}", response_model=DiffPage)
def version_diff(
    request: Request,
    response: Response,
    a: UUID,
    b: UUID,
    change_type: ChangeType | None = None,
    cursor: CursorParam = None,
    limit: PageLimit = 50,
    if_none_match: IfNoneMatch = None,
):
    """Compare the first published version with the second in EUID order."""
    scope = digest_json(["diff", str(a), str(b), change_type, limit])
    position = decode_cursor(cursor, scope)
    if position and position.version_id != b:
        raise HTTPException(422, "Invalid cursor for this version.")
    try:
        pipeline = Pipeline(request.app.state.engine)
        with pipeline.diff_details(
            str(a),
            str(b),
            after=position.euid if position else None,
            change_type=change_type,
            limit=limit + 1,
        ) as changes:
            rows = list(changes)
    except ETLError as error:
        if str(error) not in {"published_versions_required", "synthetic_not_allowed"}:
            raise
        raise HTTPException(404, "Published version is unavailable.") from None
    except SQLAlchemyError:
        raise HTTPException(503, "Published data is temporarily unavailable.") from None
    page = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        next_cursor = PageCursor(scope=scope, version_id=b, euid=page[-1]["euid"]).encode()
    body = DiffPage(
        previous_version_id=str(a),
        current_version_id=str(b),
        items=[DiffRow.model_validate(row) for row in page],
        next_cursor=next_cursor,
    )
    return conditional(request, response, if_none_match, body)


@router.get("/aggregates", response_model=AggregatesResponse)
def aggregates(
    request: Request,
    database: Database,
    response: Response,
    version: Annotated[
        list[UUID] | None, Query(description="Repeat to select exact versions.")
    ] = None,
    if_none_match: IfNoneMatch = None,
):
    """Count companies and combine public quality measures across selected editions."""
    published = queries.published_versions(database)
    requested = {str(item) for item in version or []}
    if requested - {row["id"] for row in published}:
        raise HTTPException(404, "Published version is unavailable.")
    selected = {}
    for row in published:
        if requested and row["id"] not in requested:
            continue
        if requested and row["edition"] in selected:
            raise HTTPException(422, "Select at most one version per edition.")
        # Incoming versions are sorted by edition and ID. The last ID wins ties.
        selected[row["edition"]] = row["id"]
    version_ids = list(selected.values())
    quality, average = queries.quality_aggregates(database, version_ids)
    body = AggregatesResponse(
        by_legal_form=[
            LegalFormCount.model_validate(row)
            for row in queries.group_counts(database, version_ids)
        ],
        by_county=[
            CountyCount.model_validate(row)
            for row in queries.group_counts(database, version_ids, by_county=True)
        ],
        quality_by_edition=[EditionQuality.model_validate(row) for row in quality],
        average_quarantine_rate=average,
    )
    current = None if requested else queries.current_version_id(database)
    return conditional(request, response, if_none_match, body, current)
