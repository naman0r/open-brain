import pytest
from starlette.testclient import TestClient

from app.mcp.http import HEALTH_PATH, InsecureConfiguration, build_app

TOKEN = "s3cret-token"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr("app.mcp.http.settings.vault_root", str(tmp_path))
    # Entering the context runs the app lifespan, which starts the transport's
    # session manager. Without it, authenticated requests fail inside the transport.
    with TestClient(build_app(token=TOKEN)) as client:
        yield client


class TestAuth:
    def test_mcp_endpoint_requires_a_token(self, client):
        response = client.post("/mcp", json={"jsonrpc": "2.0", "method": "ping", "id": 1})
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"].startswith("Bearer")

    @pytest.mark.parametrize(
        "header",
        ["Bearer wrong", "Bearer ", TOKEN, f"Basic {TOKEN}", f"bearer {TOKEN}"],
    )
    def test_bad_credentials_are_refused(self, client, header):
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "ping", "id": 1},
            headers={"Authorization": header},
        )
        assert response.status_code == 401

    def test_correct_token_passes_the_auth_layer(self, client):
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "ping", "id": 1},
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Accept": "application/json, text/event-stream",
            },
        )
        # Past auth. The transport may still reject an unestablished session,
        # but 401 would mean the middleware failed open.
        assert response.status_code != 401

    def test_health_is_exempt(self, client):
        response = client.get(HEALTH_PATH)
        assert response.status_code == 200
        assert response.text == "ok"


class TestRefusesInsecureStartup:
    @pytest.mark.parametrize("token", ["change-me", ""])
    def test_default_or_empty_token_refused(self, monkeypatch, tmp_path, token):
        monkeypatch.setattr("app.mcp.http.settings.vault_root", str(tmp_path))
        with pytest.raises(InsecureConfiguration):
            build_app(token=token)

    def test_missing_vault_root_refused_before_binding(self, monkeypatch, tmp_path):
        from app.vault import VaultError

        monkeypatch.setattr("app.mcp.http.settings.vault_root", str(tmp_path / "nope"))
        with pytest.raises(VaultError):
            build_app(token=TOKEN)
