"""
MCP v1 tool definitions and local handlers.

This module keeps tool contracts stable and reusable by both:
- a future full MCP protocol server
- local/CLI bridge adapters
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.memory import MemoryRememberRequest, SearchRequest
from app.services.memory_service import remember_memory
from app.services.retrieval import search_memories
from app.services.embedding import embed_text


@dataclass(slots=True)
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]


def list_tools() -> list[MCPTool]:
    return [
        MCPTool(
            name="remember",
            description="Persist explicit long-term memory",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "memory_type": {"type": "string"},
                    "source": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
                "required": ["content"],
            },
        ),
        MCPTool(
            name="recall",
            description="Retrieve relevant memories by semantic search",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer"},
                    "memory_type": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
    ]


def handle_remember(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request = MemoryRememberRequest.model_validate(payload)
    memory = remember_memory(db, request)
    return {
        "id": str(memory.id),
        "content": memory.content,
        "memory_type": memory.memory_type,
        "source": memory.source,
        "tags": memory.tags,
        "confidence": memory.confidence,
    }


def handle_recall(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request = SearchRequest.model_validate(payload)
    query_embedding = embed_text(request.query)
    hits = search_memories(
        db=db,
        query_embedding=query_embedding.vector,
        top_k=request.top_k,
        memory_type=request.memory_type,
        source=request.source,
        recency_weight=request.recency_weight,
        score_threshold=request.score_threshold,
        query_text=request.query,
    )
    return {
        "results": [
            {
                "id": str(hit.memory.id),
                "content": hit.memory.content,
                "memory_type": hit.memory.memory_type,
                "score": hit.score,
            }
            for hit in hits
        ]
    }

