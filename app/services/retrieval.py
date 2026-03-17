from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Float, and_, cast, func, select
from sqlalchemy.orm import Session

from app.db.models import Entity, Memory, MemoryEntityLink
from app.services.entities import extract_query_terms


@dataclass(slots=True)
class SearchHit:
    memory: Memory
    score: float
    score_components: dict[str, float]


def search_memories(
    db: Session,
    query_embedding: list[float],
    top_k: int,
    memory_type: str | None = None,
    source: str | None = None,
    recency_weight: float = 0.15,
    score_threshold: float = 0.15,
    query_text: str = "",
) -> list[SearchHit]:
    distance = Memory.embedding.cosine_distance(query_embedding)
    similarity = 1.0 - distance

    age_seconds = func.extract("epoch", func.now() - Memory.created_at)
    recency_boost = 1.0 / (1.0 + (cast(age_seconds, Float) / 86400.0))

    filters = [Memory.embedding.is_not(None)]
    if memory_type:
        filters.append(Memory.memory_type == memory_type)
    if source:
        filters.append(Memory.source == source)

    query_terms = extract_query_terms(query_text)

    entity_boost = 0.0
    if query_terms:
        entity_match_exists = (
            select(func.count(MemoryEntityLink.id) > 0)
            .select_from(MemoryEntityLink)
            .join(Entity, Entity.id == MemoryEntityLink.entity_id)
            .where(
                MemoryEntityLink.memory_id == Memory.id,
                func.lower(Entity.name).in_(query_terms),
            )
            .correlate(Memory)
            .scalar_subquery()
        )
        entity_boost = cast(entity_match_exists, Float) * 0.2

    total_score = similarity + (recency_weight * recency_boost) + entity_boost

    stmt = (
        select(
            Memory,
            similarity.label("similarity"),
            recency_boost.label("recency_boost"),
            cast(entity_boost, Float).label("entity_boost"),
            total_score.label("total_score"),
        )
        .where(and_(*filters))
        .order_by(total_score.desc())
        .limit(top_k)
    )
    rows = db.execute(stmt).all()

    hits: list[SearchHit] = []
    for row in rows:
        score = float(row.total_score)
        if score < score_threshold:
            continue
        components = {
            "similarity": float(row.similarity),
            "recency_boost": float(row.recency_boost),
            "entity_boost": float(row.entity_boost),
        }
        hits.append(SearchHit(memory=row.Memory, score=score, score_components=components))
    return hits

