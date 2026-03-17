from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_auth_error_is_structured() -> None:
    client = TestClient(app)
    response = client.get("/v1/memories")
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert body["error"]["type"] == "http_error"
    assert "request_id" in body["error"]


def test_suggest_endpoint_with_token() -> None:
    client = TestClient(app)
    token = settings.open_brain_api_token
    response = client.post(
        "/v1/memories/suggest",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": "I prefer practical answers"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["memory_type"] == "preference"
