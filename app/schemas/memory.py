from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MemoryType(str, Enum):
    preference = "preference"
    profile = "profile"
    project = "project"
    task = "task"
    note = "note"


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    memory_type: MemoryType = MemoryType.note
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=5000)
    memory_type: MemoryType | None = None
    source: str | None = None
    tags: list[str] | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    memory_type: MemoryType
    source: str | None
    tags: list[str]
    confidence: float
    embedding_model: str
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    memory_type: MemoryType | None = None
    source: str | None = None
    recency_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    score_threshold: float = Field(default=0.15, ge=0.0, le=2.0)


class SearchResult(MemoryRead):
    score: float
    score_components: dict[str, float] | None = None


class MemorySuggestRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    source: str | None = "suggestion"


class MemorySuggestion(BaseModel):
    content: str
    memory_type: MemoryType
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class MemoryRememberRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    memory_type: MemoryType = MemoryType.note
    source: str | None = "manual"
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class MemoryImportMode(str, Enum):
    skip_existing = "skip_existing"
    upsert = "upsert"


class MemoryImportRequest(BaseModel):
    ndjson: str = Field(min_length=1)
    mode: MemoryImportMode = MemoryImportMode.skip_existing


class MemoryImportResult(BaseModel):
    imported: int
    skipped: int
    updated: int
