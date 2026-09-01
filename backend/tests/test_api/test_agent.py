"""Tests for the grounded research-assistant prototype."""

from unittest.mock import AsyncMock

import pytest

from app.models.knowledge import KnowledgeBase
from app.models.paper import PaperChunk, PaperEntity


class FakeGateway:
    def __init__(self, *args, **kwargs) -> None:
        self.last_usage = {
            "prompt_tokens": 120,
            "completion_tokens": 40,
            "total_tokens": 160,
            "requests": 1,
        }

    async def chat(self, messages, **kwargs) -> str:
        assert "[S1]" in messages[-1]["content"]
        return "现有材料指出需要进行可追溯检索。[S1]"


class FakeEmbeddingGateway:
    def __init__(self, config) -> None:
        pass

    async def embed(self, texts):
        from app.services.retrieval.embeddings import EmbeddingBatch

        return EmbeddingBatch(
            vectors=[[1.0, 0.0] for _ in texts],
            input_tokens=len(texts) * 2,
        )


@pytest.mark.asyncio
async def test_agent_answers_from_knowledge_with_citations(
    client,
    db_session,
    monkeypatch,
) -> None:
    db_session.add(
        KnowledgeBase(
            title="可追溯学术检索",
            category="科研智能体",
            content="研究系统应保留检索证据并约束回答来源。",
            source_paper_title="Evidence-grounded Research Assistants",
            source_paper_doi="10.1000/agent.1",
            research_points=["来源追踪"],
            tags=["agent"],
        )
    )
    await db_session.flush()
    monkeypatch.setattr("app.api.v1.agent.LLMGateway", FakeGateway)
    monkeypatch.setattr(
        "app.api.v1.agent.ZoteroLocalClient.search_items",
        AsyncMock(return_value=[]),
    )

    response = await client.post(
        "/api/v1/agent/chat",
        json={"question": "如何实现可追溯学术检索？"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["grounded"] is True
    assert data["response_type"] == "research"
    assert data["citations"][0]["source"] == "knowledge"
    assert data["citations"][0]["doi"] == "10.1000/agent.1"
    assert data["total_tokens"] == 160
    assert data["retrieval_tokens"] == 0
    assert data["retrieval_mode"] == "bm25"
    assert {step["tool"] for step in data["tool_steps"]} == {
        "semantic_retrieval",
        "knowledge_search",
        "paper_fulltext_search",
        "zotero_search",
    }


@pytest.mark.asyncio
async def test_agent_reports_hybrid_retrieval_tokens(
    client,
    db_session,
    monkeypatch,
) -> None:
    from app.services.retrieval import hybrid

    db_session.add(
        KnowledgeBase(
            title="Privacy-aware Agent",
            category="AI",
            content="Privacy safeguards constrain the research agent.",
        )
    )
    await db_session.flush()
    monkeypatch.setattr("app.api.v1.agent.LLMGateway", FakeGateway)
    monkeypatch.setattr(
        hybrid,
        "get_embedding_config",
        lambda: {
            "enabled": True,
            "provider": "custom",
            "model": "test-embedding",
            "base_url": "https://embedding.example/v1",
        },
    )
    monkeypatch.setattr(hybrid, "EmbeddingGateway", FakeEmbeddingGateway)

    response = await client.post(
        "/api/v1/agent/chat",
        json={
            "question": "What privacy safeguards constrain the agent?",
            "use_zotero": False,
        },
    )

    data = response.json()
    assert response.status_code == 200
    assert data["retrieval_mode"] == "hybrid"
    assert data["retrieval_tokens"] > 0
    assert data["total_tokens"] == 160 + data["retrieval_tokens"]
    semantic_step = next(
        step for step in data["tool_steps"]
        if step["tool"] == "semantic_retrieval"
    )
    assert semantic_step["status"] == "completed"


@pytest.mark.asyncio
async def test_agent_answers_from_indexed_pdf_chunk(
    client,
    db_session,
    monkeypatch,
) -> None:
    paper = PaperEntity(
        id="paper-feature-1",
        title="Evidence-aware Retrieval Agents",
        abstract="A retrieval agent study.",
        doi="10.1000/pdf.1",
        source="test",
    )
    db_session.add(paper)
    await db_session.flush()
    db_session.add(
        PaperChunk(
            id="a" * 64,
            paper_id=paper.id,
            position=0,
            kind="section",
            heading="Methods",
            page=3,
            content="The retrieval agent uses BM25 and citation verification.",
            content_hash="b" * 64,
            feature_version="pdf-parser-chunker-v2",
            char_count=58,
        )
    )
    await db_session.flush()
    monkeypatch.setattr("app.api.v1.agent.LLMGateway", FakeGateway)

    response = await client.post(
        "/api/v1/agent/chat",
        json={
            "question": "How does the retrieval agent use citation verification?",
            "use_zotero": False,
        },
    )

    data = response.json()
    assert response.status_code == 200
    assert data["grounded"] is True
    assert data["citations"][0]["source"] == "paper"
    assert data["citations"][0]["doi"] == "10.1000/pdf.1"
    assert data["citations"][0]["section"] == "Methods"
    assert data["citations"][0]["page"] == 3
    semantic_step = next(
        step for step in data["tool_steps"]
        if step["tool"] == "semantic_retrieval"
    )
    assert semantic_step["status"] == "skipped"
    paper_step = next(
        step for step in data["tool_steps"]
        if step["tool"] == "paper_fulltext_search"
    )
    assert paper_step["count"] == 1


@pytest.mark.asyncio
async def test_agent_answers_product_help_without_search_or_model(
    client,
    monkeypatch,
) -> None:
    zotero_search = AsyncMock(return_value=[])
    monkeypatch.setattr(
        "app.api.v1.agent.ZoteroLocalClient.search_items",
        zotero_search,
    )

    response = await client.post(
        "/api/v1/agent/chat",
        json={"question": "目前这个智能体怎么使用呢？"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["response_type"] == "product_help"
    assert data["grounded"] is False
    assert data["citations"] == []
    assert data["total_tokens"] == 0
    assert data["tool_steps"][0]["tool"] == "product_help"
    assert "目前这个智能体的使用方式" in data["answer"]
    zotero_search.assert_not_awaited()


@pytest.mark.asyncio
async def test_agent_does_not_use_unrelated_recent_knowledge(
    client,
    db_session,
    monkeypatch,
) -> None:
    db_session.add(
        KnowledgeBase(
            title="交通流预测",
            category="交通工程",
            content="研究交通事故严重程度与道路流量。",
        )
    )
    await db_session.flush()
    monkeypatch.setattr(
        "app.api.v1.agent.ZoteroLocalClient.search_items",
        AsyncMock(return_value=[]),
    )

    response = await client.post(
        "/api/v1/agent/chat",
        json={"question": "量子纠错码有哪些实验进展？"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["grounded"] is False
    assert data["citations"] == []
    assert "没有找到" in data["answer"]


@pytest.mark.asyncio
async def test_agent_returns_guidance_without_materials(
    client,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.api.v1.agent.ZoteroLocalClient.search_items",
        AsyncMock(return_value=[]),
    )

    response = await client.post(
        "/api/v1/agent/chat",
        json={"question": "请总结我的研究资料"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["grounded"] is False
    assert data["total_tokens"] == 0
    assert "没有找到" in data["answer"]


@pytest.mark.asyncio
async def test_agent_continues_when_zotero_is_unavailable(
    client,
    db_session,
    monkeypatch,
) -> None:
    db_session.add(
        KnowledgeBase(
            title="本地知识",
            category="测试",
            content="本地知识库仍然可以用于问答。",
        )
    )
    await db_session.flush()
    monkeypatch.setattr("app.api.v1.agent.LLMGateway", FakeGateway)
    monkeypatch.setattr(
        "app.api.v1.agent.ZoteroLocalClient.search_items",
        AsyncMock(side_effect=RuntimeError("offline")),
    )

    response = await client.post(
        "/api/v1/agent/chat",
        json={"question": "本地知识如何使用？"},
    )

    data = response.json()
    assert response.status_code == 200
    zotero_step = next(step for step in data["tool_steps"] if step["tool"] == "zotero_search")
    assert zotero_step["status"] == "unavailable"


@pytest.mark.asyncio
async def test_agent_retries_zotero_with_a_keyword(
    client,
    monkeypatch,
) -> None:
    search = AsyncMock(
        side_effect=[
            [],
            [{
                "key": "ZOTERO1",
                "data": {
                    "title": "Explainability in Agent Systems",
                    "abstractNote": "A review of explainable agent systems.",
                    "url": "https://example.org/agent-paper",
                },
            }],
        ]
    )
    monkeypatch.setattr("app.api.v1.agent.LLMGateway", FakeGateway)
    monkeypatch.setattr("app.api.v1.agent.ZoteroLocalClient.search_items", search)

    response = await client.post(
        "/api/v1/agent/chat",
        json={
            "question": "What research themes appear in my Zotero papers about agent systems?",
            "use_knowledge": False,
        },
    )

    data = response.json()
    assert response.status_code == 200
    assert search.await_count == 2
    assert data["citations"][0]["source"] == "zotero"
    assert data["citations"][0]["item_id"] == "ZOTERO1"
