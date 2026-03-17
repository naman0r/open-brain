import math

from app.services.embedding import EMBEDDING_DIMENSION, embed_text


def test_embed_text_is_deterministic_and_normalized() -> None:
    result_a = embed_text("open brain memory")
    result_b = embed_text("open brain memory")
    vector_a = result_a.vector
    vector_b = result_b.vector

    assert len(vector_a) == EMBEDDING_DIMENSION
    assert vector_a == vector_b
    assert result_a.model
    assert result_a.provider

    magnitude = math.sqrt(sum(v * v for v in vector_a))
    assert abs(magnitude - 1.0) < 1e-6
