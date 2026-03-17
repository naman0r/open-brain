from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "message": exc.detail,
                "request_id": _request_id(request),
            }
        },
    )


async def runtime_exception_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "runtime_error",
                "message": str(exc),
                "request_id": _request_id(request),
            }
        },
    )

