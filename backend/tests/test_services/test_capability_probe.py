"""Tests for explicit, task-level model capability probes."""

import json

import pytest

from app.services.inference.capability_probe import (
    latest_probe_report,
    run_capability_probe,
    save_probe_report,
)


class _FakeGateway:
    def __init__(self, response: str = "SCHOLARNOVA_OK"):
        self.response = response
        self.messages = None
        self.usage = {
            "prompt_tokens": 7,
            "completion_tokens": 3,
            "total_tokens": 10,
        }

    async def chat(self, *, messages, **_kwargs):
        self.messages = messages
        return self.response

    async def generate_image(self, **_kwargs):
        return {"status": "ok", "url": "https://example.com/probe.png"}


class _FakeFactory:
    gateway = _FakeGateway()

    @classmethod
    def from_profile(cls, _profile):
        return cls.gateway


@pytest.mark.asyncio
async def test_structured_probe_requires_valid_expected_json():
    _FakeFactory.gateway = _FakeGateway('{"scholarnova_probe": true}')

    report = await run_capability_probe(
        {"provider": "qwen", "model": "qwen-plus"},
        "query_planning",
        gateway_factory=_FakeFactory,
    )

    assert report["status"] == "passed"
    assert report["capability"] == "structured_output"
    assert report["total_tokens"] == 10


@pytest.mark.asyncio
async def test_vision_probe_actually_sends_an_image_part():
    _FakeFactory.gateway = _FakeGateway("red")

    report = await run_capability_probe(
        {"provider": "openai", "model": "gpt-4o"},
        "vision",
        gateway_factory=_FakeFactory,
    )

    content = _FakeFactory.gateway.messages[0]["content"]
    assert report["status"] == "passed"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_probe_history_is_local_redacted_and_queryable(tmp_path, monkeypatch):
    module = "app.services.inference.capability_probe"
    monkeypatch.setattr(f"{module}.runtime_path", lambda _name: tmp_path / "probes.json")
    report = {
        "provider": "zhipu",
        "model_name": "glm-5.2",
        "task": "analysis",
        "tested_at": "2026-09-02T00:00:00+00:00",
        "status": "passed",
        "api_key": "must-not-be-saved",
    }

    save_probe_report(report)
    loaded = json.loads((tmp_path / "probes.json").read_text(encoding="utf-8"))

    assert "must-not-be-saved" not in json.dumps(loaded)
    assert latest_probe_report("zhipu", "glm-5.2", "analysis")["status"] == "passed"
