from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from tests.test_auth import BASE_URL, EXTERNAL, KEYS, WEB
from tests.test_auth import auth as auth_fixture  # noqa: F401


@pytest.mark.integration
def test_key_windows_and_concurrent_admission(engine, auth, monkeypatch):
    from app.auth import limits

    admin, _, curator, _ = auth
    issued = admin.post(KEYS, json={"owner_id": curator["id"], "name": "limit"}).json()
    header = {"X-API-Key": issued["key"]}
    now = datetime(2026, 11, 28, 23, 59, 50, tzinfo=UTC)
    monkeypatch.setattr(limits, "utc_now", lambda: now)
    first = admin.get(EXTERNAL, headers=header)
    assert first.status_code == 200
    etag = first.headers["etag"]
    conditional = {**header, "If-None-Match": etag}
    assert admin.get(EXTERNAL, headers=conditional).status_code == 304
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE api_usage SET count = 59 WHERE key_id = :key AND `window` = 'minute'"),
            {"key": issued["id"]},
        )
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: admin.get(EXTERNAL, headers=header), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 429]
    assert (
        next(response for response in responses if response.status_code == 429).headers[
            "retry-after"
        ]
        == "10"
    )
    now = datetime(2026, 11, 29, 0, 0, 1, tzinfo=UTC)
    assert admin.get(EXTERNAL, headers=header).status_code == 200
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE api_usage SET count = 5000 WHERE key_id = :key AND `window` = 'day'"),
            {"key": issued["id"]},
        )
    response = admin.get(EXTERNAL, headers=conditional)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "86399"


@pytest.mark.integration
def test_web_limit_uses_peer_and_rolls_over(engine, monkeypatch):
    from app.auth import limits

    now = datetime(2026, 11, 28, 12, 0, 50, tzinfo=UTC)
    monkeypatch.setattr(limits, "utc_now", lambda: now)
    app = create_app(engine)
    with (
        TestClient(app, base_url=BASE_URL, client=("192.0.2.1", 1000)) as first,
        TestClient(app, base_url=BASE_URL, client=("192.0.2.2", 1000)) as second,
    ):
        for _ in range(120):
            assert first.get(WEB).status_code == 200
        hit = first.get(WEB, headers={"X-Forwarded-For": "192.0.2.3"})
        assert hit.status_code == 429
        assert hit.headers["retry-after"] == "10"
        assert second.get(WEB).status_code == 200
        now = datetime(2026, 11, 28, 12, 1, tzinfo=UTC)
        assert first.get(WEB).status_code == 200
