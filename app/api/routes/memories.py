from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.security import require_api_token
from app.db.models import Memory
from app.db.session import get_db
from app.schemas.memory import (
    MemoryCreate,
    MemoryImportRequest,
    MemoryImportResult,
    MemoryRead,
    MemoryRememberRequest,
    MemorySuggestRequest,
    MemorySuggestion,
    MemoryUpdate,
)
from app.services.memory_service import (
    create_memory,
    delete_memory,
    export_memories_ndjson,
    get_memory,
    import_memories_ndjson,
    list_memories,
    remember_memory,
    suggest_memories,
    update_memory,
)

router = APIRouter(prefix="/memories", tags=["memories"], dependencies=[Depends(require_api_token)])


@router.post("", response_model=MemoryRead)
def create_memory_route(payload: MemoryCreate, db: Session = Depends(get_db)) -> Memory:
    return create_memory(db=db, payload=payload)


@router.post("/remember", response_model=MemoryRead)
def remember_memory_route(payload: MemoryRememberRequest, db: Session = Depends(get_db)) -> Memory:
    return remember_memory(db=db, payload=payload)


@router.post("/suggest", response_model=list[MemorySuggestion])
def suggest_memory_route(payload: MemorySuggestRequest) -> list[MemorySuggestion]:
    return suggest_memories(payload)


@router.post("/export", response_class=PlainTextResponse)
def export_memories_route(db: Session = Depends(get_db)) -> str:
    return export_memories_ndjson(db)


@router.post("/import", response_model=MemoryImportResult)
def import_memories_route(payload: MemoryImportRequest, db: Session = Depends(get_db)) -> MemoryImportResult:
    return import_memories_ndjson(db=db, payload=payload)


@router.get("", response_model=list[MemoryRead])
def list_memories_route(db: Session = Depends(get_db)) -> list[Memory]:
    return list_memories(db=db, limit=50)


@router.get("/{memory_id}", response_model=MemoryRead)
def get_memory_route(memory_id: UUID, db: Session = Depends(get_db)) -> Memory:
    memory = get_memory(db, memory_id)
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return memory


@router.patch("/{memory_id}", response_model=MemoryRead)
def update_memory_route(memory_id: UUID, payload: MemoryUpdate, db: Session = Depends(get_db)) -> Memory:
    memory = get_memory(db, memory_id)
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return update_memory(db=db, memory=memory, payload=payload)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory_route(memory_id: UUID, db: Session = Depends(get_db)) -> Response:
    memory = get_memory(db, memory_id)
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    delete_memory(db=db, memory=memory)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

