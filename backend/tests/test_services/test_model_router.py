"""Tests for explicit primary/fallback model routing."""

from __future__ import annotations

import asyncio

import pytest

from app.services.inference.model_router import (
    AllModelsUnavailableError,
    RoutedLLMGateway,
    chat_with_fallback,
)


class RoutedGateway:
    profiles: list[dict] = []
    fail_providers: set[str] = set()

    def __init__(self, profile: dict) -> None:
        self.profile = profile
        self._usage = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "requests": 1,
        }
        self.profiles.append(profile)

    @classmethod
    def from_profile(cls, profile: dict):
        return cls(profile)

    @property
    def usage(self) -> dict[str, int]:
        return dict(self._usage)

    async def chat(self, messages, **kwargs) -> str:
        del messages, kwargs
        if self.profile["provider"] in self.fail_providers:
            raise RuntimeError("offline")
        return f"answer from {self.profile['provider']}"


@pytest.mark.asyncio
async def test_primary_success_does_not_call_fallback(monkeypatch) -> None:
    RoutedGateway.profiles = []
    RoutedGateway.fail_providers = set()
    monkeypatch.setattr(
        "app.services.inference.model_router.get_model_for_task",
        lambda task: {
            "provider": "zhipu", "model": "glm-5.2", "api_key": "primary",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
        },
    )
    monkeypatch.setattr(
        "app.services.inference.model_router.get_fallback_model_config",
        lambda: {
            "enabled": True, "provider": "qwen", "model": "qwen-plus",
            "api_key": "fallback", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        },
    )

    result = await chat_with_fallback(
        task="assistant",
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.2,
        max_tokens=100,
        gateway_factory=RoutedGateway,
    )

    assert result.content == "answer from zhipu"
    assert result.fallback_used is False
    assert [profile["provider"] for profile in RoutedGateway.profiles] == ["zhipu"]
    assert result.usage["total_tokens"] == 15


@pytest.mark.asyncio
async def test_primary_failure_routes_to_qwen_and_sums_usage(monkeypatch) -> None:
    RoutedGateway.profiles = []
    RoutedGateway.fail_providers = {"zhipu"}
    monkeypatch.setattr(
        "app.services.inference.model_router.get_model_for_task",
        lambda task: {
            "provider": "zhipu", "model": "glm-5.2", "api_key": "primary",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
        },
    )
    monkeypatch.setattr(
        "app.services.inference.model_router.get_fallback_model_config",
        lambda: {
            "enabled": True, "provider": "qwen", "model": "qwen-plus",
            "api_key": "fallback", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        },
    )

    result = await chat_with_fallback(
        task="assistant",
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.2,
        max_tokens=100,
        gateway_factory=RoutedGateway,
    )

    assert result.content == "answer from qwen"
    assert result.fallback_used is True
    assert [attempt.status for attempt in result.attempts] == ["unavailable", "completed"]
    assert result.usage["total_tokens"] == 30


@pytest.mark.asyncio
async def test_all_routes_failure_exposes_attempts_without_raw_errors(monkeypatch) -> None:
    RoutedGateway.profiles = []
    RoutedGateway.fail_providers = {"zhipu", "qwen"}
    monkeypatch.setattr(
        "app.services.inference.model_router.get_model_for_task",
        lambda task: {
            "provider": "zhipu", "model": "glm-5.2", "api_key": "primary",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
        },
    )
    monkeypatch.setattr(
        "app.services.inference.model_router.get_fallback_model_config",
        lambda: {
            "enabled": True, "provider": "qwen", "model": "qwen-plus",
            "api_key": "fallback", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        },
    )

    with pytest.raises(AllModelsUnavailableError) as caught:
        await chat_with_fallback(
            task="assistant",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.2,
            max_tokens=100,
            gateway_factory=RoutedGateway,
        )

    assert [attempt.provider for attempt in caught.value.attempts] == ["zhipu", "qwen"]
    assert all(attempt.error_type == "RuntimeError" for attempt in caught.value.attempts)
    assert caught.value.usage["total_tokens"] == 30


@pytest.mark.asyncio
async def test_fallback_is_not_used_for_vision_task(monkeypatch) -> None:
    RoutedGateway.profiles = []
    RoutedGateway.fail_providers = {"mimo"}
    monkeypatch.setattr(
        "app.services.inference.model_router.get_model_for_task",
        lambda task: {"provider": "mimo", "model": "mimo-v2.5", "api_key": "primary", "base_url": "https://example.com/v1"},
    )
    monkeypatch.setattr(
        "app.services.inference.model_router.get_fallback_model_config",
        lambda: {"enabled": True, "provider": "qwen", "model": "qwen-plus"},
    )

    with pytest.raises(AllModelsUnavailableError) as caught:
        await chat_with_fallback(
            task="vision",
            messages=[{"role": "user", "content": "image"}],
            temperature=0.2,
            max_tokens=100,
            gateway_factory=RoutedGateway,
        )

    assert len(caught.value.attempts) == 1


@pytest.mark.asyncio
async def test_gateway_adapter_preserves_chat_contract_and_usage(monkeypatch) -> None:
    RoutedGateway.profiles = []
    RoutedGateway.fail_providers = set()
    monkeypatch.setattr(
        "app.services.inference.model_router.get_model_for_task",
        lambda task: {
            "provider": "qwen", "model": "qwen-plus", "api_key": "key",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        },
    )
    monkeypatch.setattr(
        "app.services.inference.model_router.get_fallback_model_config",
        lambda: {"enabled": False},
    )
    gateway = RoutedLLMGateway("query_planning", gateway_factory=RoutedGateway)

    content = await gateway.chat([{"role": "user", "content": "plan"}])

    assert content == "answer from qwen"
    assert gateway.last_usage["total_tokens"] == 15
    assert gateway.usage["requests"] == 1


@pytest.mark.asyncio
async def test_query_planning_timeout_leaves_time_for_fallback(monkeypatch) -> None:
    class TimeoutGateway(RoutedGateway):
        async def chat(self, messages, **kwargs) -> str:
            del messages, kwargs
            if self.profile["provider"] == "zhipu":
                await asyncio.sleep(1)
            return f"answer from {self.profile['provider']}"

    TimeoutGateway.profiles = []
    monkeypatch.setattr(
        "app.services.inference.model_router.get_model_for_task",
        lambda task: {
            "provider": "zhipu", "model": "glm-5.2", "api_key": "primary",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
        },
    )
    monkeypatch.setattr(
        "app.services.inference.model_router.get_fallback_model_config",
        lambda: {
            "enabled": True, "provider": "qwen", "model": "qwen-plus",
            "api_key": "fallback", "base_url": "https://example.com/v1",
        },
    )
    monkeypatch.setattr(
        "app.services.inference.model_router._route_timeout",
        lambda task: 0.01,
    )

    result = await chat_with_fallback(
        task="query_planning",
        messages=[{"role": "user", "content": "plan"}],
        temperature=0.2,
        max_tokens=100,
        gateway_factory=TimeoutGateway,
    )

    assert result.content == "answer from qwen"
    assert result.fallback_used is True
    assert [attempt.status for attempt in result.attempts] == [
        "unavailable",
        "completed",
    ]
