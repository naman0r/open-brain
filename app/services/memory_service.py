from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Entity, Memory, MemoryEntityLink
from app.schemas.memory import (
    MemoryCreate,
    MemoryImportMode,
    MemoryImportRequest,
    MemoryImportResult,
    MemoryRememberRequest,
    MemorySuggestion,
    MemorySuggestRequest,
    MemoryUpdate,
)
from app.services.embedding import embed_text
from app.services.entities import extract_entities


def _memory_hash(content: str, memory_type: str, source: str | None) -> str:
    payload = f"{memory_type}:{source or ''}:{content}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _link_entities(db: Session, memory_id: UUID, entities: list[tuple[str, str]]) -> None:
    for name, entity_type in entities:
        entity_stmt = select(Entity).where(Entity.name == name, Entity.entity_type == entity_type)
        entity = db.execute(entity_stmt).scalar_one_or_none()
        if entity is None:
            entity = Entity(name=name, entity_type=entity_type)
            db.add(entity)
            db.flush()

        exists_stmt = select(MemoryEntityLink).where(
            MemoryEntityLink.memory_id == memory_id,
            MemoryEntityLink.entity_id == entity.id,
        )
        if db.execute(exists_stmt).scalar_one_or_none() is None:
            db.add(MemoryEntityLink(memory_id=memory_id, entity_id=entity.id))


def create_memory(db: Session, payload: MemoryCreate) -> Memory:
    embedding = embed_text(payload.content)
    memory = Memory(
        content=payload.content,
        memory_type=payload.memory_type,
        source=payload.source,
        tags=payload.tags,
        confidence=payload.confidence,
        content_hash=_memory_hash(payload.content, payload.memory_type, payload.source),
        embedding=embedding.vector,
        embedding_model=embedding.model,
    )
    db.add(memory)
    db.flush()
    _link_entities(db, memory.id, extract_entities(payload.content))
    db.commit()
    db.refresh(memory)
    return memory


def remember_memory(db: Session, payload: MemoryRememberRequest) -> Memory:
    create_payload = MemoryCreate(
        content=payload.content,
        memory_type=payload.memory_type,
        source=payload.source,
        tags=payload.tags,
        confidence=payload.confidence,
    )
    existing_stmt = select(Memory).where(
        Memory.content_hash == _memory_hash(
            create_payload.content,
            create_payload.memory_type,
            create_payload.source,
        )
    )
    existing = db.execute(existing_stmt).scalar_one_or_none()
    if existing:
        return existing
    return create_memory(db, create_payload)


def list_memories(db: Session, limit: int = 50) -> list[Memory]:
    stmt = select(Memory).order_by(Memory.created_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_memory(db: Session, memory_id: UUID) -> Memory | None:
    return db.get(Memory, memory_id)


def update_memory(db: Session, memory: Memory, payload: MemoryUpdate) -> Memory:
    if payload.content is not None:
        memory.content = payload.content
        embedding = embed_text(payload.content)
        memory.embedding = embedding.vector
        memory.embedding_model = embedding.model
        memory.content_hash = _memory_hash(payload.content, memory.memory_type, memory.source)
        db.execute(delete(MemoryEntityLink).where(MemoryEntityLink.memory_id == memory.id))
        _link_entities(db, memory.id, extract_entities(payload.content))
    if payload.memory_type is not None:
        memory.memory_type = payload.memory_type
        memory.content_hash = _memory_hash(memory.content, payload.memory_type, memory.source)
    if payload.source is not None:
        memory.source = payload.source
        memory.content_hash = _memory_hash(memory.content, memory.memory_type, payload.source)
    if payload.tags is not None:
        memory.tags = payload.tags
    if payload.confidence is not None:
        memory.confidence = payload.confidence
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def delete_memory(db: Session, memory: Memory) -> None:
    db.delete(memory)
    db.commit()


def suggest_memories(payload: MemorySuggestRequest) -> list[MemorySuggestion]:
    text = payload.text.strip()
    lowered = text.lower()
    memory_type = "note"
    confidence = 0.6
    tags: list[str] = []

    if any(k in lowered for k in ("i prefer", "i like", "my preference", "prefer to")):
        memory_type = "preference"
        confidence = 0.9
        tags.append("preference")
    elif any(k in lowered for k in ("my name is", "i am ", "i'm ")):
        memory_type = "profile"
        confidence = 0.9
        tags.append("profile")
    elif any(k in lowered for k in ("project", "building", "working on", "roadmap")):
        memory_type = "project"
        confidence = 0.8
        tags.append("project")
    elif any(k in lowered for k in ("todo", "task", "need to", "must")):
        memory_type = "task"
        confidence = 0.8
        tags.append("task")

    suggestion = MemorySuggestion(
        content=text,
        memory_type=memory_type,
        source=payload.source,
        confidence=confidence,
        tags=tags,
        reason="Heuristic extraction from provided text",
    )
    return [suggestion]


def export_memories_ndjson(db: Session) -> str:
    memories = list_memories(db, limit=10_000)
    rows: list[str] = []
    for memory in memories:
        payload = {
            "id": str(memory.id),
            "content": memory.content,
            "memory_type": memory.memory_type,
            "source": memory.source,
            "tags": memory.tags,
            "confidence": memory.confidence,
            "embedding_model": memory.embedding_model,
            "created_at": memory.created_at.isoformat() if isinstance(memory.created_at, datetime) else None,
            "updated_at": memory.updated_at.isoformat() if isinstance(memory.updated_at, datetime) else None,
        }
        rows.append(json.dumps(payload))
    return "\n".join(rows)


def import_memories_ndjson(db: Session, payload: MemoryImportRequest) -> MemoryImportResult:
    imported = 0
    skipped = 0
    updated = 0

    lines = [line.strip() for line in payload.ndjson.splitlines() if line.strip()]
    for line in lines:
        data = json.loads(line)
        create_payload = MemoryCreate(
            content=data["content"],
            memory_type=data.get("memory_type", "note"),
            source=data.get("source"),
            tags=data.get("tags", []),
            confidence=float(data.get("confidence", 0.8)),
        )
        remember_payload = MemoryRememberRequest(**create_payload.model_dump())
        existing_stmt = select(Memory).where(
            Memory.content_hash == _memory_hash(
                remember_payload.content,
                remember_payload.memory_type,
                remember_payload.source,
            )
        )
        existing = db.execute(existing_stmt).scalar_one_or_none()
        if existing and payload.mode == MemoryImportMode.skip_existing:
            skipped += 1
            continue
        if existing and payload.mode == MemoryImportMode.upsert:
            update_payload = MemoryUpdate(
                content=remember_payload.content,
                memory_type=remember_payload.memory_type,
                source=remember_payload.source,
                tags=remember_payload.tags,
                confidence=remember_payload.confidence,
            )
            update_memory(db, existing, update_payload)
            updated += 1
            continue
        remember_memory(db, remember_payload)
        imported += 1

    return MemoryImportResult(imported=imported, skipped=skipped, updated=updated)

