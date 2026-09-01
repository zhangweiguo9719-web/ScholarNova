"""Dependency-free BM25 ranking for mixed Chinese and English research text."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from app.services.retrieval.contracts import RetrievalChunk

_EN_TOKEN = re.compile(r"[a-z0-9][a-z0-9+._-]{1,}")
_ZH_RUN = re.compile(r"[\u4e00-\u9fff]+")
_EN_STOP = {
    "about", "and", "are", "for", "from", "have", "how", "into", "paper",
    "papers", "research", "that", "the", "these", "this", "what", "which",
    "with",
}
_ZH_STOP = {
    "一个", "什么", "以及", "哪些", "如何", "怎么", "是否", "目前", "相关",
    "研究", "论文", "文献", "这个", "这些", "进行",
}


def tokenize(text: str) -> list[str]:
    """Tokenize English words and Chinese 2/3-grams without external models."""
    lowered = (text or "").casefold()
    tokens = [token for token in _EN_TOKEN.findall(lowered) if token not in _EN_STOP]
    for run in _ZH_RUN.findall(lowered):
        if len(run) <= 4 and run not in _ZH_STOP:
            tokens.append(run)
        for size in (2, 3):
            for index in range(len(run) - size + 1):
                token = run[index:index + size]
                if token not in _ZH_STOP:
                    tokens.append(token)
    return tokens


@dataclass(frozen=True, slots=True)
class RankedChunk:
    chunk: RetrievalChunk
    score: float


def rank_chunks(
    query: str,
    chunks: Sequence[RetrievalChunk],
    *,
    limit: int = 6,
    max_per_document: int = 2,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[RankedChunk]:
    """Rank candidates with BM25 and enforce document-level diversity."""
    if limit <= 0 or max_per_document <= 0 or not chunks:
        return []
    query_terms = tokenize(query)
    if not query_terms:
        return []

    tokenized = [tokenize(chunk.search_text) for chunk in chunks]
    average_length = sum(len(tokens) for tokens in tokenized) / len(tokenized)
    average_length = max(average_length, 1.0)
    document_frequency: Counter[str] = Counter()
    for tokens in tokenized:
        document_frequency.update(set(tokens))

    query_frequency = Counter(query_terms)
    total_documents = len(chunks)
    scored: list[RankedChunk] = []
    normalized_query = " ".join(query.casefold().split())
    for chunk, tokens in zip(chunks, tokenized):
        frequencies = Counter(tokens)
        document_length = max(len(tokens), 1)
        score = 0.0
        for term, query_count in query_frequency.items():
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            df = document_frequency[term]
            inverse_frequency = math.log(
                1 + (total_documents - df + 0.5) / (df + 0.5)
            )
            denominator = frequency + k1 * (
                1 - b + b * document_length / average_length
            )
            score += inverse_frequency * (
                frequency * (k1 + 1) / denominator
            ) * (1 + math.log(query_count))
        if normalized_query and normalized_query in chunk.search_text.casefold():
            score += 2.0
        if score > 0:
            scored.append(RankedChunk(chunk=chunk, score=round(score, 6)))

    scored.sort(
        key=lambda item: (
            item.score,
            item.chunk.source,
            item.chunk.document_id,
            -item.chunk.position,
        ),
        reverse=True,
    )
    selected: list[RankedChunk] = []
    per_document: Counter[str] = Counter()
    for item in scored:
        if per_document[item.chunk.document_id] >= max_per_document:
            continue
        selected.append(item)
        per_document[item.chunk.document_id] += 1
        if len(selected) >= limit:
            break
    return selected
