from datetime import UTC, datetime, timedelta
from hashlib import sha256
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"
CURATORS = "/api/v1/admin/curators"
KEYS = "/api/v1/admin/api-keys"
REVIEW = "/api/v1/curator/versions"
EXTERNAL = "/api/v1/versions"
WEB = "/api/web/v1/versions"
BASE_URL = "https://testserver"
PEER = ("192.0.2.1", 1000)


def test_auth_routes_are_documented():
    with TestClient(create_app(MagicMock())) as client:
        spec = client.get("/openapi.json").json()
    assert spec["paths"][EXTERNAL]["get"]["security"] == [{"APIKeyHeader": []}]
    assert "security" not in spec["paths"][WEB]["get"]
    assert spec["components"]["securitySchemes"]["APIKeyHeader"] == {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
    }
    for path in (LOGIN, LOGOUT, ME, CURATORS, KEYS, REVIEW):
        assert path in spec["paths"]


@pytest.fixture(name="auth")
def auth(engine):
    from app.auth.accounts import bootstrap_admin

    admin_email = f"{uuid4()}@example.test"
    curator_email = f"{uuid4()}@example.test"
    password = f"fixture-{uuid4()}"
    bootstrap_admin(engine, admin_email, password)
    try:
        with TestClient(create_app(engine), base_url=BASE_URL, client=PEER) as admin:
            login = admin.post(LOGIN, json={"email": admin_email, "password": password})
            assert login.status_code == 200, login.text
            created = admin.post(CURATORS, json={"email": curator_email, "password": password})
            assert created.status_code == 201, created.text
            yield admin, login, created.json(), password
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM users WHERE email IN (:admin, :curator)"),
                {"admin": admin_email, "curator": curator_email},
            )


@pytest.mark.integration
def test_role_matrix_and_key_lifecycle(engine, auth):
    admin, _, curator, password = auth
    assert admin.get(ME).json()["role"] == "admin"
    assert admin.get(REVIEW).status_code == 403
    assert admin.delete(f"{CURATORS}/{admin.get(ME).json()['id']}").status_code == 404

    listed = admin.post(KEYS, json={"owner_id": curator["id"], "name": "fixture"})
    assert listed.status_code == 201
    assert listed.headers["cache-control"] == "no-store"
    data = listed.json()
    key, key_id = data["key"], data["id"]
    header = {"X-API-Key": key}
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT key_hash, key_prefix, daily_quota FROM api_keys WHERE id = :id"),
            {"id": key_id},
        ).one()
        assert row == (sha256(key.encode()).digest(), key[: len(row.key_prefix)], 5000)

    with TestClient(create_app(engine), base_url=BASE_URL, client=PEER) as other:
        for headers, external_status in (({}, 401), (header, 200), ({"X-API-Key": "invalid"}, 401)):
            assert other.get(WEB, headers=headers).status_code == 200
            assert other.get(EXTERNAL, headers=headers).status_code == external_status
            assert other.get(REVIEW, headers=headers).status_code == 401
            assert other.post(KEYS, headers=headers, json={}).status_code == 401
        assert (
            other.post(LOGIN, json={"email": curator["email"], "password": password}).status_code
            == 200
        )
        assert other.get(ME).json()["role"] == "curator"
        assert other.get(REVIEW).status_code == 200
        assert other.get(EXTERNAL).status_code == 401
        assert (
            other.post(CURATORS, json={"email": curator["email"], "role": "admin"}).status_code
            == 403
        )
        assert other.delete(f"{CURATORS}/{admin.get(ME).json()['id']}").status_code == 403
        assert (
            other.post(KEYS, json={"owner_id": curator["id"], "name": "fixture"}).status_code == 403
        )
        version = uuid4()
        assert other.post(f"{REVIEW}/{version}/publish").status_code == 409
        assert (
            other.post(f"{REVIEW}/{version}/approve", json={"report_hash": "0" * 64}).status_code
            == 409
        )
        assert admin.delete(f"{CURATORS}/{curator['id']}").status_code == 204
        assert other.get(ME).status_code == 401
        assert other.get(EXTERNAL, headers=header).status_code == 200

    etag = admin.get(EXTERNAL, headers=header).headers["etag"]
    assert admin.delete(f"{KEYS}/{key_id}").status_code == 204
    assert admin.get(EXTERNAL, headers={**header, "If-None-Match": etag}).status_code == 401


@pytest.mark.integration
def test_sessions_and_password_redaction(engine, auth, caplog, monkeypatch):
    from app.auth import sessions

    admin, login, curator, password = auth
    cookie = login.headers["set-cookie"]
    for flag in ("HttpOnly", "Secure", "SameSite=strict"):
        assert flag.lower() in cookie.lower()
    with engine.connect() as connection:
        encoded = connection.scalar(
            text("SELECT password_hash FROM users WHERE id = :id"), {"id": curator["id"]}
        )
        assert encoded.startswith("$argon2id$")
        assert password not in encoded
    malformed = admin.post(LOGIN, json={"email": [password], "password": {"secret": password}})
    assert malformed.status_code == 422
    assert password not in malformed.text
    assert password not in caplog.text
    assert admin.post(LOGOUT, headers={"Origin": "https://other.example"}).status_code == 403
    token = admin.cookies.get("companywatch_session")
    assert admin.post(LOGOUT).status_code == 204
    assert admin.get(ME, headers={"Cookie": f"companywatch_session={token}"}).status_code == 401
    assert (
        admin.post(LOGIN, json={"email": curator["email"], "password": password}).status_code == 200
    )
    token = admin.cookies.get("companywatch_session")
    assert (
        admin.get(ME, headers={"Cookie": f"companywatch_session={token}tampered"}).status_code
        == 401
    )
    now = datetime.now(UTC) + timedelta(hours=8, seconds=1)
    monkeypatch.setattr(sessions, "utc_now", lambda: now)
    assert admin.get(ME).status_code == 401


@pytest.mark.integration
def test_curator_review_and_stale_approval_preserve_pointer(engine, auth):
    from app.etl.models import publications, versions
    from app.etl.service import DATASET, digest_json

    _, _, curator, password = auth
    version = str(uuid4())
    report = {"full_file_validated": True, "accepted_records": 100_000, "minimum_records": 100_000}
    report_hash = digest_json(report)
    pointer = publications.select().where(publications.c.dataset == DATASET)
    with engine.begin() as connection:
        previous = connection.execute(pointer).one().current_version_id
        connection.execute(
            versions.insert().values(
                id=version,
                edition="2026-11-04",
                state="review",
                source_kind="real",
                resource_id=version,
                source_url="https://example.test",
                license="CC-BY",
                sha256="0" * 64,
                schema_hash="1" * 64,
                profile="fixture",
                manifest={},
                report=report,
                report_hash=report_hash,
                created_at=datetime.now(UTC),
            )
        )
    try:
        with TestClient(create_app(engine), base_url=BASE_URL, client=PEER) as client:
            assert (
                client.post(
                    LOGIN, json={"email": curator["email"], "password": password}
                ).status_code
                == 200
            )
            listed = client.get(REVIEW).json()["items"]
            assert any(row["id"] == version and row["report_hash"] == report_hash for row in listed)
            assert next(row for row in listed if row["id"] == version)["report"] == report
            assert client.post(f"{REVIEW}/{version}/publish").status_code == 409
            assert (
                client.post(
                    f"{REVIEW}/{version}/approve", json={"report_hash": "0" * 64}
                ).status_code
                == 409
            )
        with engine.connect() as connection:
            assert connection.execute(pointer).one().current_version_id == previous
            row = connection.execute(versions.select().where(versions.c.id == version)).one()
            assert row.state == "review" and row.approval is None
    finally:
        with engine.begin() as connection:
            connection.execute(versions.delete().where(versions.c.id == version))
