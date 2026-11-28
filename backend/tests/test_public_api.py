from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, insert, select, update

from app.etl.models import companies, publications, versions
from app.etl.service import DATASET
from app.main import create_app

PREFIX = "/api/v1"
OCTOBER = "2026-10-19"
NOVEMBER = "2026-11-04"


@pytest.fixture
def published_data(engine):
    """Use fictional rows in the isolated MySQL project."""
    ids = [str(uuid4()) for _ in range(3)]
    pointer = publications.c.dataset == DATASET
    with engine.begin() as connection:
        previous = connection.scalar(select(publications.c.current_version_id).where(pointer))
        for version, edition, state, report in zip(
            ids,
            (OCTOBER, NOVEMBER, "2026-12-01"),
            ("published", "approved", "review"),
            (
                {"source_records": 8, "accepted_records": 5, "quarantined_records": 2,
                 "excluded_records": 1},
                {"source_records": 20, "accepted_records": 5, "quarantined_records": 0},
                {"source_records": 0, "accepted_records": 0, "quarantined_records": 0},
            ),
            strict=True,
        ):
            connection.execute(
                insert(versions).values(
                    id=version, edition=edition, state=state, report=report,
                    resource_id=version, source_url="https://example.com/onrc",
                    license="CC BY 4.0", source_kind="real", sha256="0" * 64,
                    profile="test", schema_hash="1" * 64, created_at=datetime.now(UTC),
                    manifest={},
                )
            )
        for version, rows in (
            (ids[0], (
                ("ROONRC.A", "BRAȘOV alpha", "31/01/2022", "BV"),
                ("ROONRC.B", "BRAȘOV alpha", "01/12/2021", "BV"),
                ("ROONRC.C", "BRAȘOV alpha", "01/12/2021 00:00:00", "BV"),
                ("ROONRC.D", "ALT BRAȘOV", None, "BV"),
                ("ROONRC.E", "OTHER", None, "CJ"),
            )),
            (ids[1], (
                ("ROONRC.A", "BRAȘOV beta", "31/01/2022", "BV"),
                ("ROONRC.B", "BRAȘOV alpha", "01/12/2021", "BV"),
                ("ROONRC.C", "BRAȘOV alpha", "01/12/2021 00:00:00", "BV"),
                ("ROONRC.E", "OTHER", None, "CJ"),
                ("ROONRC.F", "NEW", None, None),
            )),
        ):
            connection.execute(
                insert(companies),
                [
                    dict(version_id=version, euid=euid, name=name, county=county,
                         registration_date=date, legal_form="SRL", locality="CENTRU",
                         cui="42" if euid == "ROONRC.A" else None)
                    for euid, name, date, county in rows
                ],
            )
        connection.execute(update(publications).where(pointer).values(current_version_id=ids[0]))
    try:
        with TestClient(create_app(engine)) as client:
            yield client, ids
    finally:
        with engine.begin() as connection:
            connection.execute(update(publications).where(pointer).values(current_version_id=previous))
            connection.execute(delete(companies).where(companies.c.version_id.in_(ids)))
            connection.execute(delete(versions).where(versions.c.id.in_(ids)))


def publish(engine, version):
    with engine.begin() as connection:
        connection.execute(update(versions).where(versions.c.id == version).values(state="published"))
        connection.execute(
            update(publications).where(publications.c.dataset == DATASET)
            .values(current_version_id=version)
        )


def euids(response):
    assert response.status_code == 200, response.text
    return [item["euid"] for item in response.json()["items"]]


@pytest.mark.integration
def test_search_sort_and_cursor_survive_publication(published_data, engine):
    client, (old, new, _) = published_data
    path = PREFIX + "/companies"
    params = {"name": "brasov", "name_match": "prefix", "county": "BV",
              "locality": "CENTRU", "legal_form": "SRL", "limit": 1}
    first = client.get(path, params=params)
    assert euids(first) == ["ROONRC.A"]
    cursor = first.json()["next_cursor"]
    assert client.get(path, params={**params, "cursor": cursor, "county": "CJ"}).status_code == 422
    assert client.get(path, params={**params, "cursor": "invalid"}).status_code == 422
    assert client.get(path, params={"version": new}).status_code == 404
    assert client.get(path, params={"limit": 201}).status_code == 422
    assert euids(client.get(path, params={"cui": "42"})) == ["ROONRC.A"]
    assert euids(client.get(path, params={"name": "%"})) == []
    assert euids(client.get(path, params={"name": "brasov"})) == [
        "ROONRC.D", "ROONRC.A", "ROONRC.B", "ROONRC.C",
    ]
    date_params = {"version": old, "sort": "registration_date", "limit": 2}
    dates = client.get(path, params=date_params)
    assert euids(dates) == ["ROONRC.B", "ROONRC.C"]
    dates = client.get(path, params={**date_params, "cursor": dates.json()["next_cursor"]})
    assert euids(dates) == ["ROONRC.A", "ROONRC.D"]
    assert euids(client.get(path, params={**date_params, "cursor": dates.json()["next_cursor"]})) == [
        "ROONRC.E",
    ]

    publish(engine, new)
    all_seen = euids(first)
    while cursor:
        page = client.get(path, params={**params, "cursor": cursor})
        assert page.json()["version_id"] == old
        all_seen.extend(euids(page))
        cursor = page.json()["next_cursor"]
    assert all_seen == ["ROONRC.A", "ROONRC.B", "ROONRC.C"]
    assert client.get(path, params=params).json()["version_id"] == new


@pytest.mark.integration
def test_observed_history(published_data, engine):
    client, (old, new, _) = published_data
    publish(engine, new)
    path = PREFIX + "/companies/ROONRC.D"
    assert client.get(path, params={"as_of": "2026-10-18"}).json()["status"] == "unavailable"
    for when in (OCTOBER, "2026-11-03"):
        observed = client.get(path, params={"as_of": when}).json()
        assert observed["status"] == "present"
        assert observed["version_id"] == old
        assert observed["valid_from"] == OCTOBER
        assert observed["valid_to"] == NOVEMBER
        assert observed["source"]["url"] == "https://example.com/onrc"
    for params in ({}, {"as_of": NOVEMBER}, {"as_of": "2027-01-01"}):
        absent = client.get(path, params=params).json()
        assert absent["status"] == "absent"
        assert absent["version_id"] == new
        assert absent["valid_from"] == NOVEMBER
        assert absent["valid_to"] is None
        assert absent["company"] is None
    assert client.get(path, params={"as_of": "2026-02-31"}).status_code == 422
    assert client.get(path, params={"as_of": "1793750400"}).status_code == 422
    assert client.get(PREFIX + "/companies/roOnrc.a").json()["status"] == "absent"


@pytest.mark.integration
def test_diff_pages_and_aggregates(published_data, engine):
    client, (old, new, third) = published_data
    path = f"{PREFIX}/versions/{old}/diff/{new}"
    assert client.get(path).status_code == 404
    publish(engine, new)
    first = client.get(path, params={"limit": 2})
    assert euids(first) == ["ROONRC.A", "ROONRC.B"]
    modified = first.json()["items"][0]
    assert modified["change_type"] == "modified"
    assert modified["previous"]["name"] == "BRAȘOV alpha"
    assert modified["current"]["name"] == "BRAȘOV beta"
    assert modified["changed_fields"] == ["name"]
    second = client.get(path, params={"limit": 2, "cursor": first.json()["next_cursor"]})
    assert euids(second) == ["ROONRC.C", "ROONRC.D"]
    assert second.json()["items"][0]["change_type"] == "unchanged"
    assert second.json()["items"][1]["current"] is None
    third_page = client.get(path, params={"limit": 2, "cursor": second.json()["next_cursor"]})
    assert euids(third_page) == ["ROONRC.E", "ROONRC.F"]
    assert third_page.json()["items"][1]["previous"] is None
    assert third_page.json()["next_cursor"] is None
    filtered = client.get(path, params={"change_type": "removed"})
    assert euids(filtered) == ["ROONRC.D"]
    assert filtered.json()["items"][0]["change_type"] == "removed"
    assert client.get(path, params={"limit": 201}).status_code == 422

    url = PREFIX + "/aggregates"
    aggregate = client.get(url, params=[("version", old), ("version", old), ("version", new)]).json()
    assert [(group["edition"], group["count"]) for group in aggregate["by_legal_form"]] == [
        (OCTOBER, 5), (NOVEMBER, 5),
    ]
    assert any(group["county"] is None and group["count"] == 1
               for group in aggregate["by_county"])
    assert [(row["quarantined_records"], row["excluded_records"])
            for row in aggregate["quality_by_edition"]] == [(2, 1), (0, None)]
    assert aggregate["average_quarantine_rate"] == 0.125
    publish(engine, third)
    zero = client.get(url, params={"version": third}).json()
    assert zero["quality_by_edition"][0]["accepted_records"] == 0
    assert zero["average_quarantine_rate"] is None


@pytest.mark.integration
def test_etags_follow_current_and_keep_explicit_versions_stable(published_data, engine):
    client, (old, new, third) = published_data
    publish(engine, new)
    latest = ["/versions", "/companies?limit=1", "/companies/ROONRC.A", "/aggregates"]
    pinned = [f"/companies?version={old}", f"/versions/{old}/diff/{new}",
              f"/aggregates?version={old}", f"/companies/ROONRC.A?as_of={OCTOBER}"]
    tags = {}
    for path in latest + pinned:
        response = client.get(PREFIX + path)
        assert response.status_code == 200
        tag = tags[path] = response.headers["etag"]
        cached = client.get(PREFIX + path, headers={"If-None-Match": f'"other", {tag}'})
        assert cached.status_code == 304
        assert cached.headers["etag"] == tag
        assert cached.content == b""

    publish(engine, third)
    for path in latest + pinned:
        response = client.get(PREFIX + path, headers={"If-None-Match": tags[path]})
        if path in latest:
            assert response.status_code == 200
            assert response.headers["etag"] != tags[path]
        else:
            assert response.status_code == 304
            assert response.headers["etag"] == tags[path]


def test_openapi_documents_public_routes():
    with TestClient(create_app(MagicMock())) as client:
        paths = client.get("/openapi.json").json()["paths"]
    for path in ("/versions", "/companies", "/companies/{euid}",
                 "/versions/{a}/diff/{b}", "/aggregates"):
        operation = paths[PREFIX + path]["get"]
        assert "ETag" in operation["responses"]["200"]["headers"]
        assert "304" in operation["responses"]
        assert "If-None-Match" in {p["name"] for p in operation["parameters"]}
        assert "$ref" in operation["responses"]["200"]["content"]["application/json"]["schema"]
