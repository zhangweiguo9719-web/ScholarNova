"""Tests for the versioned knowledge feature pipeline."""

import pytest

from app.models.knowledge import KnowledgeBase
from app.services.features.knowledge import (
    KNOWLEDGE_FEATURE_VERSION,
    ensure_knowledge_features,
    rebuild_knowledge_features,
    split_knowledge_text,
)


def test_split_knowledge_text_is_bounded_and_overlapping() -> None:
    text = "第一部分。" + ("A" * 1150) + "。第二部分。" + ("B" * 1150)

    chunks = split_knowledge_text(text, target_chars=1200, overlap_chars=120)

    assert len(chunks) >= 2
    assert all(0 < len(chunk) <= 1200 for chunk in chunks)
    assert chunks[0][-80:] in chunks[1]


@pytest.mark.asyncio
async def test_knowledge_features_are_stable_and_rebuilt_when_content_changes(
    db_session,
) -> None:
    knowledge = KnowledgeBase(
        title="长文证据",
        category="RAG",
        content=("第一段用于检索。" * 120) + ("第二段用于验证。" * 120),
    )
    db_session.add(knowledge)
    await db_session.flush()

    first = await rebuild_knowledge_features(db_session, knowledge)
    first_ids = [chunk.id for chunk in first]
    ensured = await ensure_knowledge_features(db_session, [knowledge])

    assert [chunk.id for chunk in ensured] == first_ids
    assert all(chunk.feature_version == KNOWLEDGE_FEATURE_VERSION for chunk in ensured)

    knowledge.content += "新增的研究结论。"
    rebuilt = await ensure_knowledge_features(db_session, [knowledge])

    assert [chunk.id for chunk in rebuilt] != first_ids
    assert all(chunk.knowledge_id == knowledge.id for chunk in rebuilt)
