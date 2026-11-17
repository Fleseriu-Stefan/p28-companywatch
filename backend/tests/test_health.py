from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import create_app


def test_liveness_does_not_connect_to_database():
    engine = MagicMock()
    engine.connect.side_effect = AssertionError("Liveness must not connect")
    with TestClient(create_app(engine)) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    engine.connect.assert_not_called()


@pytest.mark.parametrize(
    ("ready", "code", "body"),
    [(True, 200, {"status": "ready"}), (False, 503, {"status": "not_ready"})],
)
def test_readiness_contract(ready, code, body):
    with patch("app.api.health.is_database_ready", return_value=ready):
        with TestClient(create_app(MagicMock())) as client:
            response = client.get("/health/ready")
    assert response.status_code == code
    assert response.json() == body


def test_database_error_is_not_exposed():
    with patch("app.api.health.is_database_ready", side_effect=SQLAlchemyError("internal detail")):
        with TestClient(create_app(MagicMock())) as client:
            response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert "internal detail" not in response.text


def test_openapi_documents_health_responses_and_docs_are_available():
    with TestClient(create_app(MagicMock())) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json()["paths"]
        assert "200" in paths["/health/live"]["get"]["responses"]
        assert {"200", "503"} <= paths["/health/ready"]["get"]["responses"].keys()
        assert client.get("/docs").status_code == 200
