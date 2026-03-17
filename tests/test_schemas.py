import pytest
from pydantic import ValidationError

from app.schemas.memory import SearchRequest


def test_search_request_default_recency_weight() -> None:
    req = SearchRequest(query="my query")
    assert req.recency_weight == 0.15
    assert req.score_threshold == 0.15


def test_search_request_recency_weight_bounds() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(query="my query", recency_weight=1.5)
