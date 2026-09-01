"""Regression tests for optional BM25 + embedding retrieval."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.retrieval.bm25 import rank_chunks
from app.services.retrieval.contracts import RetrievalChunk
from app.services.retrieval.embeddings import EmbeddingBatch
from app.services.retrieval.hybrid import (
    rank_chunks_by_vector,
    rank_chunks_hybrid,
    reciprocal_rank_fusion,
)


def _chunk(chunk_id: str, title: str, content: str) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        document_id=f"document:{chunk_id}",
        source="knowledge",
        title=title,
        content=content,
    )


def test_golden_set_hybrid_top1_is_not_worse_than_bm25() -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "retrieval_golden.json"
    cases = json.loads(fixture.read_text(encoding="utf-8"))
    bm25_hits = 0
    hybrid_hits = 0
    for case in cases:
        chunks = [
            _chunk(item["id"], item["title"], item["content"])
            for item in case["candidates"]
        ]
        vectors = {
            item["id"]: item["vector"]
            for item in case["candidates"]
        }
        lexical = rank_chunks(case["query"], chunks, limit=3, max_per_document=1)
        semantic = rank_chunks_by_vector(
            case["query_vector"], chunks, vectors, limit=3
        )
        fused = reciprocal_rank_fusion(
            [lexical, semantic],
            weights=[1.15, 1.0],
            limit=1,
            max_per_document=1,
        )
        bm25_hits += bool(lexical and lexical[0].chunk.chunk_id == case["relevant"])
        hybrid_hits += bool(fused and fused[0].chunk.chunk_id == case["relevant"])

    assert bm25_hits == 3
    assert hybrid_hits == 4


class FakeEmbeddingGateway:
    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, texts) -> EmbeddingBatch:
        self.calls += 1
        vectors = [
            [1.0, 0.0] if "privacy" in text.casefold() else [0.0, 1.0]
            for text in texts
        ]
        return EmbeddingBatch(vectors=vectors, input_tokens=len(texts) * 3)


@pytest.mark.asyncio
async def test_hybrid_embeddings_are_cached_locally(
    db_session,
    monkeypatch,
) -> None:
    from app.services.retrieval import hybrid

    fake = FakeEmbeddingGateway()
    monkeypatch.setattr(
        hybrid,
        "get_embedding_config",
        lambda: {
            "enabled": True,
            "provider": "custom",
            "model": "test-embedding",
            "api_key": None,
            "base_url": "https://embedding.example/v1",
        },
    )
    monkeypatch.setattr(hybrid, "EmbeddingGateway", lambda config: fake)
    chunks = [
        _chunk("privacy", "Privacy", "Privacy preserving aggregation"),
        _chunk("traffic", "Traffic", "Road speed forecasting"),
    ]

    first = await rank_chunks_hybrid(db_session, "privacy safeguards", chunks)
    second = await rank_chunks_hybrid(db_session, "privacy safeguards", chunks)

    assert first.mode == "hybrid"
    assert first.cache_misses == 3
    assert first.embedding_tokens == 9
    assert second.mode == "hybrid"
    assert second.cache_hits == 3
    assert second.cache_misses == 0
    assert second.embedding_tokens == 0
    assert fake.calls == 1


@pytest.mark.asyncio
async def test_hybrid_failure_falls_back_to_bm25(
    db_session,
    monkeypatch,
) -> None:
    from app.services.retrieval import hybrid

    class BrokenGateway:
        def __init__(self, config) -> None:
            pass

        async def embed(self, texts):
            raise TimeoutError

    monkeypatch.setattr(
        hybrid,
        "get_embedding_config",
        lambda: {
            "enabled": True,
            "provider": "custom",
            "model": "broken",
            "base_url": "https://embedding.example/v1",
        },
    )
    monkeypatch.setattr(hybrid, "EmbeddingGateway", BrokenGateway)
    chunks = [_chunk("trace", "Traceable retrieval", "citation evidence retrieval")]

    result = await rank_chunks_hybrid(db_session, "citation retrieval", chunks)

    assert result.mode == "bm25"
    assert result.semantic_status == "unavailable"
    assert result.ranked[0].chunk.chunk_id == "trace"
    assert result.embedding_tokens == 0
