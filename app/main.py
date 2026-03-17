from fastapi import FastAPI, HTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import http_exception_handler, runtime_exception_handler
from app.core.request_context import RequestContextMiddleware

app = FastAPI(title=settings.app_name)
app.add_middleware(RequestContextMiddleware)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RuntimeError, runtime_exception_handler)
app.include_router(api_router)
