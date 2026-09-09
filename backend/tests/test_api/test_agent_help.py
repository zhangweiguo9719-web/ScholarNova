"""Offline regressions for contextual, bounded product-help answers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.agent import AgentMessage, _is_product_help, _product_help_answer
from app.services.inference.model_router import (
    AllModelsUnavailableError,
    ModelAttempt,
    RoutedChatResult,
)


HELP_PROFILE = {
    "provider": "siliconflow",
    "model": "Qwen/offline-help-model",
    "api_key": "offline-help-secret-must-not-appear-in-prompts",
    "base_url": "http://127.0.0.1:9/v1",
}
HELP_USAGE = {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100, "requests": 1}
FOLLOWUPS = ["那下一步呢", "那怎么用呢", "然后呢", "具体一点", "what next"]


def history_of(*questions):
    return [
        message
        for question in questions
        for message in (
            AgentMessage(role="user", content=question),
            AgentMessage(role="assistant", content="这是上一轮回答。"),
        )
    ]


@pytest.mark.parametrize("question", FOLLOWUPS)
@pytest.mark.parametrize(
    "history,expected",
    [
        ([], False),
        ([AgentMessage(role="assistant", content="我可以介绍 ScholarNova 的用法。")], False),
        (history_of("我该如何使用你"), True),
        (history_of("我该如何使用你", "那下一步呢"), True),
        (history_of("什么是RAG"), False),
        (history_of("我该如何使用你", "什么是RAG"), False),
        (history_of("我该如何使用你", "什么是RAG", "然后呢"), False),
        (history_of("什么是RAG", "我该如何使用你"), True),
    ],
    ids=["empty", "assistant-only", "help", "help-chain", "research",
         "research-interruption", "interrupted-chain", "back-to-help"],
)
def test_help_followups_require_traceable_uninterrupted_user_context(question, history, expected):
    assert _is_product_help(question, history) is expected


@pytest.mark.parametrize(
    "question",
    ["分析这篇论文的方法", "论文中智能体能做什么", "什么是RAG",
     "Who are you studying in this paper?", "这篇论文下一步实验该怎么做"],
)
def test_explicit_research_overrides_a_product_help_chain(question):
    assert _is_product_help(question, history_of("我该如何使用你", "那下一步呢")) is False


@pytest.mark.parametrize("question", ["你好", "您好"])
def test_standalone_chinese_greetings_still_enter_product_help(question):
    assert _is_product_help(question) is True


@pytest.fixture
def isolated_help(monkeypatch):
    monkeypatch.setattr("app.api.v1.agent.check_rate_limit", lambda *args, **kwargs: None)
    profile_lookup = MagicMock(return_value=dict(HELP_PROFILE))
    monkeypatch.setattr("app.api.v1.agent.get_model_for_task", profile_lookup)
    blocked = []
    for name in ("_knowledge_candidates", "_paper_candidates", "rank_chunks_hybrid"):
        mock = AsyncMock(side_effect=AssertionError(f"Help must not perform {name}"))
        monkeypatch.setattr(f"app.api.v1.agent.{name}", mock)
        blocked.append(mock)
    for name in ("ZoteroLocalClient", "LLMGateway"):
        mock = MagicMock(side_effect=AssertionError(f"Real service forbidden: {name}"))
        monkeypatch.setattr(f"app.api.v1.agent.{name}", mock)
        blocked.append(mock)
    chat = AsyncMock(side_effect=AssertionError("Configure an offline model result explicitly"))
    monkeypatch.setattr("app.api.v1.agent.chat_with_fallback", chat)
    yield chat, profile_lookup
    for mock in blocked:
        mock.assert_not_called()


def model_attempt(status="completed", error_type=None):
    return ModelAttempt(
        role="primary", provider=HELP_PROFILE["provider"], model=HELP_PROFILE["model"],
        status=status, error_type=error_type, **HELP_USAGE,
    )


def model_result(content):
    return RoutedChatResult(
        content=content, profile=dict(HELP_PROFILE), usage=dict(HELP_USAGE),
        attempts=(model_attempt(),), fallback_used=False,
    )


def assert_product_help_metadata(data):
    assert data["response_type"] == "product_help"
    assert data["grounded"] is False
    assert data["citations"] == []
    assert data["verification_status"] == "not_applicable"
    assert data["retrieval_tokens"] == 0
    assert data["model_fallback_used"] is False
    assert not ({"knowledge_search", "paper_fulltext_search", "zotero_search", "semantic_retrieval"}
                & {step["tool"] for step in data["tool_steps"]})


@pytest.mark.asyncio
@pytest.mark.parametrize("use_knowledge,use_zotero", [(True, False), (False, True)])
async def test_model_help_is_bounded_uses_recent_history_and_reports_actual_usage(
    client, isolated_help, use_knowledge, use_zotero,
):
    chat, profile_lookup = isolated_help
    chat.side_effect = None
    chat.return_value = model_result("先选择材料来源，再提出具体问题；设置中可以核对 Zotero 连接状态。")
    history = [
        {"role": "user", "content": "OLD_USER_MUST_NOT_APPEAR"},
        {"role": "assistant", "content": "OLD_ASSISTANT_MUST_NOT_APPEAR"},
        *[
            {"role": "user" if index % 2 == 0 else "assistant",
             "content": f"RECENT_{index}_" + "字" * 1100 + f"TRUNCATED_TAIL_{index}"}
            for index in range(4)
        ],
    ]
    question = "我该如何使用你"
    response = await client.post("/api/v1/agent/chat", json={
        "question": question, "history": history,
        "use_knowledge": use_knowledge, "use_zotero": use_zotero,
    })
    assert response.status_code == 200
    data = response.json()
    assert_product_help_metadata(data)
    assert data["answer"] == chat.return_value.content
    assert data["inference_mode"] == "model"
    assert data["model_route"] == "primary"
    assert data["fallback_used"] is False
    assert data["fallback_reason"] is None
    assert data["provider"] == HELP_PROFILE["provider"]
    assert data["model"] == HELP_PROFILE["model"]
    assert data["model_attempts"] == [model_attempt().to_dict()]
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        assert data[key] == HELP_USAGE[key]
    profile_lookup.assert_called_once_with("assistant")
    chat.assert_awaited_once()
    kwargs = chat.await_args.kwargs
    assert kwargs["task"] == "assistant"
    assert kwargs["allow_fallback"] is False
    assert kwargs["timeout_seconds"] == 12
    assert kwargs["max_tokens"] == 800
    assert kwargs["temperature"] == 0.2
    messages = kwargs["messages"]
    assert messages[1:-1] == [
        {"role": message["role"], "content": message["content"][:1000]}
        for message in history[-4:]
    ]
    prompt = "\n".join(message["content"] for message in messages)
    assert question in messages[-1]["content"]
    assert _product_help_answer(question) in prompt
    assert "OLD_USER_MUST_NOT_APPEAR" not in prompt
    assert "OLD_ASSISTANT_MUST_NOT_APPEAR" not in prompt
    assert "TRUNCATED_TAIL_" not in prompt
    assert HELP_PROFILE["api_key"] not in prompt
    assert f"use_knowledge={str(use_knowledge).lower()}" in prompt
    assert f"use_zotero={str(use_zotero).lower()}" in prompt
    assert "未执行连接检测" in messages[0]["content"]
    assert HELP_PROFILE["api_key"] not in str(data)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timeout", "blank", "fake-citation"])
async def test_help_failure_returns_builtin_guide_without_losing_attempt_usage(
    client, isolated_help, failure,
):
    chat, _ = isolated_help
    if failure == "timeout":
        attempt = model_attempt(status="unavailable", error_type="TimeoutError")
        chat.side_effect = AllModelsUnavailableError([attempt], dict(HELP_USAGE))
        expected_reason = "model_unavailable"
    else:
        attempt = model_attempt()
        chat.side_effect = None
        chat.return_value = model_result(" \n\t " if failure == "blank" else "这款软件已经验证了论文结论。[S1]")
        expected_reason = "invalid_help_response"
    question = "我该如何使用你"
    response = await client.post("/api/v1/agent/chat", json={
        "question": question, "use_knowledge": True, "use_zotero": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert_product_help_metadata(data)
    assert data["answer"] == _product_help_answer(question)
    assert data["inference_mode"] == "deterministic_fallback"
    assert data["model_route"] == "deterministic"
    assert data["fallback_used"] is True
    assert data["fallback_reason"] == expected_reason
    assert data["model_attempts"] == [attempt.to_dict()]
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        assert data[key] == HELP_USAGE[key]
    chat.assert_awaited_once()
    assert chat.await_args.kwargs["allow_fallback"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("question", FOLLOWUPS)
async def test_contextual_help_without_key_uses_builtin_guide_without_any_model(
    client, isolated_help, question,
):
    chat, profile_lookup = isolated_help
    profile_lookup.return_value = {**HELP_PROFILE, "api_key": ""}
    response = await client.post("/api/v1/agent/chat", json={
        "question": question,
        "history": [message.model_dump() for message in history_of("我该如何使用你", "那下一步呢")],
        "use_knowledge": True, "use_zotero": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert_product_help_metadata(data)
    assert data["inference_mode"] == "deterministic_fallback"
    assert data["model_route"] == "deterministic"
    assert data["fallback_used"] is True
    assert data["fallback_reason"] == "model_unavailable"
    assert data["model_attempts"] == []
    assert all(data[key] == 0 for key in (
        "prompt_tokens", "completion_tokens", "retrieval_tokens", "total_tokens"
    ))
    assert "ScholarNova" in data["answer"]
    chat.assert_not_called()


@pytest.mark.asyncio
async def test_help_without_key_neither_reads_nor_writes_user_database(
    client, db_session, isolated_help, monkeypatch,
):
    chat, profile_lookup = isolated_help
    profile_lookup.return_value = {**HELP_PROFILE, "api_key": ""}
    database_calls = []
    for name in ("execute", "scalar", "scalars", "get", "delete", "flush", "commit"):
        mock = AsyncMock(side_effect=AssertionError(f"Help must not access user data: {name}"))
        monkeypatch.setattr(db_session, name, mock)
        database_calls.append(mock)
    for name in ("add", "add_all"):
        mock = MagicMock(side_effect=AssertionError(f"Help must not modify user data: {name}"))
        monkeypatch.setattr(db_session, name, mock)
        database_calls.append(mock)

    response = await client.post("/api/v1/agent/chat", json={
        "question": "我该如何使用你",
        "history": [{"role": "user", "content": "分析这篇论文的方法"}],
        "use_knowledge": True, "use_zotero": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert_product_help_metadata(data)
    assert data["inference_mode"] == "deterministic_fallback"
    assert data["fallback_reason"] == "model_unavailable"
    assert data["total_tokens"] == 0
    chat.assert_not_called()
    for mock in database_calls:
        mock.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_boundary", ["profile-lookup", "gateway-construction"])
async def test_help_configuration_errors_return_safe_guide_instead_of_500(
    client, isolated_help, monkeypatch, failure_boundary,
):
    from app.services.inference.model_router import chat_with_fallback

    chat, profile_lookup = isolated_help
    failure = ValueError(f"Invalid offline configuration: {HELP_PROFILE['api_key']}")
    factory = None
    if failure_boundary == "profile-lookup":
        profile_lookup.side_effect = failure
    else:
        # Exercise the real router's initialization boundary, but never create
        # a provider client or send a request, even if error handling regresses.
        factory = MagicMock()
        factory.from_profile.side_effect = failure
        monkeypatch.setattr("app.api.v1.agent.LLMGateway", factory)
        monkeypatch.setattr("app.api.v1.agent.chat_with_fallback", chat_with_fallback)
        monkeypatch.setattr(
            "app.services.inference.model_router.get_fallback_model_config",
            lambda: {"enabled": False},
        )

    question = "我该如何使用你"
    response = await client.post("/api/v1/agent/chat", json={
        "question": question, "use_knowledge": True, "use_zotero": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert_product_help_metadata(data)
    assert data["answer"] == _product_help_answer(question)
    assert data["inference_mode"] == "deterministic_fallback"
    assert data["model_route"] == "deterministic"
    assert data["fallback_used"] is True
    assert data["fallback_reason"] == "model_unavailable"
    assert all(data[key] == 0 for key in (
        "prompt_tokens", "completion_tokens", "retrieval_tokens", "total_tokens"
    ))
    assert all(attempt["status"] == "unavailable" for attempt in data["model_attempts"])
    assert HELP_PROFILE["api_key"] not in str(data)
    profile_lookup.assert_called_once_with("assistant")
    chat.assert_not_called()
    if factory is not None:
        factory.from_profile.assert_called_once()
        factory.assert_not_called()
