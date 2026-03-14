from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    memory_type: str = "note"
    source: str | None = None


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=5000)
    memory_type: str | None = None
    source: str | None = None


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    memory_type: str
    source: str | None
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    memory_type: str | None = None
    source: str | None = None
    recency_weight: float = Field(default=0.15, ge=0.0, le=1.0)


class SearchResult(MemoryRead):
    score: float
