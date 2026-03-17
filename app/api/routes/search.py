from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import require_api_token
from app.db.session import get_db
from app.schemas.memory import SearchRequest, SearchResult
from app.services.embedding import embed_text
from app.services.retrieval import search_memories

router = APIRouter(prefix="/search", tags=["search"], dependencies=[Depends(require_api_token)])


@router.post("", response_model=list[SearchResult])
def search(payload: SearchRequest, db: Session = Depends(get_db)) -> list[SearchResult]:
    query_embedding = embed_text(payload.query)
    top_k = min(payload.top_k, settings.retrieval_max_top_k)
    hits = search_memories(
        db=db,
        query_embedding=query_embedding.vector,
        top_k=top_k,
        memory_type=payload.memory_type,
        source=payload.source,
        recency_weight=payload.recency_weight,
        score_threshold=max(payload.score_threshold, settings.retrieval_score_threshold),
        query_text=payload.query,
    )
    return [
        SearchResult.model_validate(
            {
                "id": hit.memory.id,
                "content": hit.memory.content,
                "memory_type": hit.memory.memory_type,
                "source": hit.memory.source,
                "tags": hit.memory.tags,
                "confidence": hit.memory.confidence,
                "embedding_model": hit.memory.embedding_model,
                "created_at": hit.memory.created_at,
                "updated_at": hit.memory.updated_at,
                "score": hit.score,
                "score_components": hit.score_components,
            }
        )
        for hit in hits
    ]
