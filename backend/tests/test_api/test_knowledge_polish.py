from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.v1 import knowledge as knowledge_api
from app.schemas.knowledge import KnowledgeCreate
from app.services.inference import AllModelsUnavailableError


class _CreateDB:
    def add(self, item):
        self.item = item

    async def flush(self):
        self.item.id = "polish-regression"
        self.item.created_at = self.item.updated_at = datetime(2026, 1, 1)

    async def commit(self):
        pass

    async def refresh(self, _item):
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["completed", "invalid_json", "invalid_fields", "unavailable", "skipped"])
async def test_polish_reports_actual_status_and_usage(monkeypatch, outcome):
    reported = {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40}
    contents = {
        "completed": '{"polished_content": "精炼后的笔记", "research_points": ["新研究点"], "tags": ["新标签"]}',
        "invalid_json": "not JSON",
        "invalid_fields": '{"polished_content": "精炼后的笔记", "research_points": "不是列表"}',
    }
    routed = (
        AsyncMock(side_effect=AllModelsUnavailableError([], reported))
        if outcome == "unavailable" else AsyncMock(return_value=SimpleNamespace(
            content=contents.get(outcome, ""), profile={"provider": "test", "model": "polish"},
            fallback_used=True, usage=reported,
        ))
    )
    monkeypatch.setattr(knowledge_api, "chat_with_fallback", routed)
    monkeypatch.setattr(knowledge_api, "rebuild_knowledge_features", AsyncMock())
    request = KnowledgeCreate(
        title="测试笔记", category="测试", content="原始笔记",
        research_points=["原始研究点"], tags=["原始标签"], auto_polish=outcome != "skipped",
    )

    result = await knowledge_api.create_knowledge(request, _CreateDB())

    if outcome == "skipped":
        assert result.polish_status == "skipped"
        assert result.model_completed is None
        assert result.total_tokens == 0
        routed.assert_not_awaited()
    else:
        routed.assert_awaited_once()
        assert result.prompt_tokens == 30
        assert result.completion_tokens == 10
        assert result.total_tokens == 40
        assert result.model_completed is (outcome != "unavailable")
        assert result.polish_status == (
            "model_unavailable" if outcome == "unavailable" else
            "completed" if outcome == "completed" else "invalid_response"
        )
        if outcome != "unavailable":
            assert result.provider == "test"
            assert result.model == "polish"
            assert result.fallback_used is True
    if outcome == "completed":
        assert result.content == "精炼后的笔记"
        assert result.research_points == ["新研究点"]
        assert result.tags == ["新标签"]
    else:
        assert result.content == "原始笔记"
        assert result.research_points == ["原始研究点"]
        assert result.tags == ["原始标签"]
