from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


def test_v1_health() -> None:
    assert client.get("/v1/health").status_code == 200


def test_vault_health_reports_note_count(monkeypatch, tmp_path) -> None:
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    monkeypatch.setattr("app.api.routes.health.settings.vault_root", str(tmp_path))
    body = client.get("/health/vault").json()
    assert body["status"] == "ok"
    assert body["notes"] == 1


def test_vault_health_errors_when_root_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.api.routes.health.settings.vault_root", str(tmp_path / "nope"))
    response = client.get("/health/vault")
    assert response.status_code == 503
    assert response.json()["status"] == "error"
