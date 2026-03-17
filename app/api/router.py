from fastapi import APIRouter

from app.api.routes import health, memories, search
from app.core.config import settings

api_router = APIRouter()
v1_router = APIRouter(prefix=f"/{settings.api_version}")
v1_router.include_router(health.router)
v1_router.include_router(memories.router)
v1_router.include_router(search.router)

api_router.include_router(v1_router)

# Legacy path for simple health probes.
api_router.include_router(health.router)
