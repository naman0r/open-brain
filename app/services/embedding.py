from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import httpx

from app.core.config import settings

EMBEDDING_DIMENSION = 1536


@dataclass(slots=True)
class EmbeddingResult:
    vector: list[float]
    model: str
    provider: str


class EmbeddingProvider:
    provider_name = "base"

    def embed(self, text: str) -> EmbeddingResult:  # pragma: no cover - interface
        raise NotImplementedError


def _byte_to_unit(value: int) -> float:
    return (value / 127.5) - 1.0


def _normalize(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / magnitude for v in vector]


class LocalDeterministicEmbeddingProvider(EmbeddingProvider):
    provider_name = "local"
    model_name = "local-deterministic-v1"

    def embed(self, text: str) -> EmbeddingResult:
        if not text:
            return EmbeddingResult(
                vector=[0.0] * EMBEDDING_DIMENSION,
                model=self.model_name,
                provider=self.provider_name,
            )

        bytes_out = bytearray()
        seed = text.encode("utf-8")
        while len(bytes_out) < EMBEDDING_DIMENSION:
            seed = hashlib.sha256(seed).digest()
            bytes_out.extend(seed)

        vector = [_byte_to_unit(b) for b in bytes_out[:EMBEDDING_DIMENSION]]
        return EmbeddingResult(
            vector=_normalize(vector),
            model=self.model_name,
            provider=self.provider_name,
        )


class OpenAIEmbeddingProvider(EmbeddingProvider):
    provider_name = "openai"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def embed(self, text: str) -> EmbeddingResult:
        payload = {"input": text, "model": self.model}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = httpx.post(
            "https://api.openai.com/v1/embeddings",
            json=payload,
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        vector = data["data"][0]["embedding"]
        return EmbeddingResult(
            vector=vector,
            model=self.model,
            provider=self.provider_name,
        )


def get_embedding_provider() -> EmbeddingProvider:
    configured = settings.embedding_provider.strip().lower()
    if configured in {"openai", "auto"} and settings.openai_api_key:
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embed_model,
        )
    return LocalDeterministicEmbeddingProvider()


def embed_text(text: str) -> EmbeddingResult:
    """
    Public embedding entrypoint used across API, MCP, and services.
    Falls back to local deterministic embeddings when configured provider
    is unavailable or errors.
    """
    provider = get_embedding_provider()
    try:
        return provider.embed(text)
    except Exception:
        fallback = LocalDeterministicEmbeddingProvider()
        return fallback.embed(text)

