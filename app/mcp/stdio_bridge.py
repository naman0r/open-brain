from __future__ import annotations

import json
import sys
from typing import Any

from app.db.session import SessionLocal, _session_error
from app.mcp.server import handle_recall, handle_remember, list_tools


def _read_payload(line: str) -> dict[str, Any]:
    payload = json.loads(line)
    if not isinstance(payload, dict):
        raise ValueError("Input must be a JSON object")
    return payload


def main() -> None:
    if _session_error is not None:
        raise _session_error
    if SessionLocal is None:
        raise RuntimeError("Database is not configured.")

    print(json.dumps({"status": "ready", "tools": [tool.name for tool in list_tools()]}), flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = _read_payload(line)
            action = request.get("action")
            payload = request.get("payload", {})

            with SessionLocal() as db:
                if action == "remember":
                    response = handle_remember(db, payload)
                elif action == "recall":
                    response = handle_recall(db, payload)
                elif action == "tools":
                    response = {"tools": [tool.__dict__ for tool in list_tools()]}
                else:
                    raise ValueError(f"Unsupported action: {action}")
            print(json.dumps({"ok": True, "data": response}), flush=True)
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": {"type": type(exc).__name__, "message": str(exc)},
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()

