from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import _session_error, engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def db_health():
    if _session_error is not None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(_session_error)},
        )

    if engine is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "Database is not configured"},
        )

    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "detail": "Database connection failed",
                "error_type": type(exc).__name__,
            },
        )

    return {"status": "ok"}
