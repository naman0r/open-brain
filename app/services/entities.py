from __future__ import annotations

import re
from collections import Counter


_ENTITY_TOKEN_PATTERN = re.compile(r"\b[A-Z][a-zA-Z0-9\-_]{2,}\b")


def extract_entities(text: str) -> list[tuple[str, str]]:
    """
    Lightweight entity extraction for MVP:
    - capitalized tokens (>=3 chars) treated as topics by default
    - common project keywords mapped to project type
    """
    candidates = _ENTITY_TOKEN_PATTERN.findall(text or "")
    counts = Counter(candidates)
    entities: list[tuple[str, str]] = []
    for name, _ in counts.most_common(12):
        entity_type = "project" if name.lower() in {"openbrain", "open-brain", "openbrain"} else "topic"
        entities.append((name, entity_type))
    return entities


def extract_query_terms(query: str) -> list[str]:
    return list({term.lower() for term, _ in extract_entities(query)})

