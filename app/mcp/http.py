"""HTTP transport for the context-vault MCP server.

Kept separate from `server.py` because the tool definitions are transport-agnostic
and the concerns here (auth, host allowlisting, bind address) apply only when the
server is reachable over a network.
"""

from __future__ import annotations

from secrets import compare_digest

from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.types import Receive, Scope, Send

from app.core.config import settings
from app.mcp.server import mcp
from app.vault import Vault

HEALTH_PATH = "/healthz"
DEFAULT_TOKEN = "change-me"


class InsecureConfiguration(RuntimeError):
    pass


class BearerAuth:
    """Raw ASGI middleware so streamed responses are never buffered.

    Starlette's BaseHTTPMiddleware wraps the response body, which breaks the SSE
    stream the streamable-http transport relies on.
    """

    def __init__(self, app: Starlette, token: str, exempt: tuple[str, ...] = ()) -> None:
        self.app = app
        self.expected = f"Bearer {token}".encode()
        self.exempt = exempt

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in self.exempt:
            await self.app(scope, receive, send)
            return

        provided = b""
        for key, value in scope.get("headers", []):
            if key == b"authorization":
                provided = value
                break

        if not compare_digest(provided, self.expected):
            response = JSONResponse(
                {"error": {"type": "unauthorized", "message": "Invalid or missing bearer token"}},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="context-vault"'},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


@mcp.custom_route(HEALTH_PATH, methods=["GET"])
async def healthz(_: Request) -> PlainTextResponse:
    """Unauthenticated liveness probe, so a tunnel or monitor can check the server."""
    return PlainTextResponse("ok")


def build_app(
    host: str = "127.0.0.1",
    allowed_hosts: list[str] | None = None,
    allowed_origins: list[str] | None = None,
    token: str | None = None,
) -> Starlette:
    token = token if token is not None else settings.open_brain_api_token
    if not token or token == DEFAULT_TOKEN:
        raise InsecureConfiguration(
            "OPEN_BRAIN_API_TOKEN is unset or still the default. Set a real token "
            "before serving over HTTP; the tools include write access."
        )

    # Fail before binding rather than 500ing on the first tool call.
    Vault(settings.vault_root)

    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts or [host, f"{host}:*"],
        allowed_origins=allowed_origins or [],
    )
    app = mcp.streamable_http_app(transport_security=security, host=host)
    app.add_middleware(BearerAuth, token=token, exempt=(HEALTH_PATH,))
    return app
