import math

from app.services.embedding import EMBEDDING_DIMENSION, embed_text


def test_embed_text_is_deterministic_and_normalized() -> None:
    vector_a = embed_text("open brain memory")
    vector_b = embed_text("open brain memory")

    assert len(vector_a) == EMBEDDING_DIMENSION
    assert vector_a == vector_b

    magnitude = math.sqrt(sum(v * v for v in vector_a))
    assert abs(magnitude - 1.0) < 1e-6

