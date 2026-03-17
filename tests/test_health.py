from fastapi.testclient import TestClient

from app.api.routes import health as health_route
from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


def test_v1_health() -> None:
    client = TestClient(app)
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_db_health_not_configured(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(health_route, "_session_error", None)
    monkeypatch.setattr(health_route, "engine", None)

    response = client.get("/health/db")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "detail": "Database is not configured"}


def test_db_health_session_error(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(health_route, "_session_error", RuntimeError("broken-url"))

    response = client.get("/health/db")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "detail": "broken-url"}


def test_db_health_ok(monkeypatch) -> None:
    client = TestClient(app)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def execute(self, _):
            return None

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    monkeypatch.setattr(health_route, "_session_error", None)
    monkeypatch.setattr(health_route, "engine", FakeEngine())

    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
