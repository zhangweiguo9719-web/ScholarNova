"""Tests for the provider-neutral sparse retrieval layer."""

from app.services.retrieval.bm25 import rank_chunks, tokenize
from app.services.retrieval.contracts import RetrievalChunk


def _chunk(chunk_id: str, document_id: str, text: str, *, source: str = "knowledge") -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        source=source,
        title=text.split("。", 1)[0],
        content=text,
    )


def test_tokenize_supports_chinese_and_english_terms() -> None:
    tokens = tokenize("Hybrid RAG 检索结合向量召回与关键词排序")

    assert "hybrid" in tokens
    assert "rag" in tokens
    assert "检索" in tokens
    assert "向量" in tokens


def test_rank_chunks_prefers_relevant_chinese_evidence() -> None:
    candidates = [
        _chunk("1", "knowledge:traffic", "交通流预测与高速公路事故风险。"),
        _chunk("2", "knowledge:rag", "混合 RAG 使用关键词检索与向量召回提高证据覆盖。"),
    ]

    ranked = rank_chunks("如何通过混合 RAG 改进向量检索？", candidates)

    assert ranked[0].chunk.chunk_id == "2"
    assert ranked[0].score > 0


def test_rank_chunks_enforces_document_diversity() -> None:
    candidates = [
        _chunk("a1", "knowledge:a", "RAG retrieval evidence first section"),
        _chunk("a2", "knowledge:a", "RAG retrieval evidence second section"),
        _chunk("a3", "knowledge:a", "RAG retrieval evidence third section"),
        _chunk("b1", "zotero:b", "RAG retrieval from Zotero", source="zotero"),
    ]

    ranked = rank_chunks("RAG retrieval evidence", candidates, limit=4, max_per_document=2)

    assert len([item for item in ranked if item.chunk.document_id == "knowledge:a"]) == 2
    assert any(item.chunk.document_id == "zotero:b" for item in ranked)


def test_rank_chunks_returns_empty_for_unrelated_materials() -> None:
    ranked = rank_chunks(
        "量子纠错实验",
        [_chunk("1", "knowledge:traffic", "交通流预测与道路拥堵。")],
    )

    assert ranked == []
