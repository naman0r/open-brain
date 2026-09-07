from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.vault import Vault, VaultError

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/vault")
def vault_health():
    try:
        vault = Vault(settings.vault_root)
        notes = sum(1 for _ in vault.iter_notes())
    except VaultError as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(exc)},
        )
    return {"status": "ok", "root": str(vault.root), "notes": notes}
