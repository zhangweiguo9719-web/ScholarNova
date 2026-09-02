"""
模型配置端点测试
"""

import json
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient


def test_task_profiles_inherit_default_credentials_after_restart(monkeypatch):
    """任务留空时应在重启后继承同提供商的主配置。"""
    from app.config import MODEL_PROFILES, load_saved_model_config, runtime_path, settings

    config = {
        "provider": "mimo",
        "model_name": "mimo-v2.5-pro",
        "api_key": "test-main-key",
        "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
        "temperature": 0.7,
        "max_tokens": 4096,
        "tasks": {
            "analysis": {
                "provider": "mimo",
                "model_name": "mimo-v2.5-pro",
                "api_key": None,
                "base_url": None,
            },
            "diagram": {
                "provider": "sensenova",
                "model_name": "sensenova-u1-fast",
                "api_key": None,
                "base_url": "https://token.sensenova.cn/v1",
            },
        },
    }
    runtime_path("model_config.json").write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setitem(MODEL_PROFILES, "analysis", {})
    monkeypatch.setitem(
        MODEL_PROFILES,
        "diagram",
        {
            "provider": "sensenova",
            "model": "sensenova-u1-fast",
            "api_key": "ENV",
            "base_url": "https://token.sensenova.cn/v1",
        },
    )
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_BASE", "https://api.openai.com/v1")
    monkeypatch.setattr(settings, "OPENAI_DEFAULT_MODEL", "gpt-4o")

    load_saved_model_config()

    assert MODEL_PROFILES["analysis"] == {
        "provider": "mimo",
        "model": "mimo-v2.5-pro",
        "api_key": "test-main-key",
        "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
    }
    assert MODEL_PROFILES["diagram"]["provider"] == "sensenova"
    assert MODEL_PROFILES["diagram"]["api_key"] is None
    assert settings.OPENAI_API_KEY == "test-main-key"


def test_cross_provider_task_never_inherits_primary_credentials(monkeypatch):
    """千问等独立任务不能误用主供应商的 Key 或地址。"""
    from app.config import MODEL_PROFILES, get_model_for_task, settings

    monkeypatch.setattr(settings, "DEFAULT_LLM_PROVIDER", "mimo")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "mimo-secret")
    monkeypatch.setattr(
        settings,
        "OPENAI_API_BASE",
        "https://token-plan-cn.xiaomimimo.com/v1",
    )
    monkeypatch.setitem(
        MODEL_PROFILES,
        "translation",
        {
            "provider": "qwen",
            "model": "qwen-plus",
            "api_key": None,
            "base_url": None,
        },
    )

    profile = get_model_for_task("translation")

    assert profile["provider"] == "qwen"
    assert profile["api_key"] is None
    assert profile["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"


class TestSaveModelConfig:
    """POST /api/v1/model/config 测试套件"""

    async def test_save_config_openai(self, client: AsyncClient):
        """保存 OpenAI 配置应返回成功"""
        response = await client.post(
            "/api/v1/model/config",
            json={
                "provider": "openai",
                "model_name": "gpt-4o",
                "api_key": "sk-test-key",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_config_hides_saved_credentials(self, client: AsyncClient):
        """浏览器只能知道 Key 已配置，不能读取 Key 本身。"""
        from app.config import runtime_path

        runtime_path("model_config.json").write_text(
            json.dumps(
                {
                    "provider": "zhipu",
                    "model_name": "glm-5.2",
                    "api_key": "local-secret",
                    "base_url": "https://open.bigmodel.cn/api/paas/v4",
                    "tasks": {
                        "diagram": {
                            "provider": "sensenova",
                            "model_name": "sensenova-u1-fast",
                            "api_key": "diagram-secret",
                        }
                    },
                    "fallback": {
                        "enabled": True,
                        "provider": "qwen",
                        "model_name": "qwen-plus",
                        "api_key": "fallback-secret",
                        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    },
                    "embedding": {
                        "enabled": True,
                        "provider": "openai",
                        "model_name": "text-embedding-3-small",
                        "api_key": "embedding-secret",
                        "base_url": "https://api.openai.com/v1",
                    },
                }
            ),
            encoding="utf-8",
        )

        response = await client.get("/api/v1/model/config")
        data = response.json()

        assert response.status_code == 200
        assert data["provider"] == "zhipu"
        assert data["api_key"] is None
        assert data["api_key_configured"] is True
        assert data["tasks"]["diagram"]["api_key"] is None
        assert data["tasks"]["diagram"]["api_key_configured"] is True
        assert data["fallback"]["enabled"] is True
        assert data["fallback"]["provider"] == "qwen"
        assert data["fallback"]["api_key"] is None
        assert data["fallback"]["api_key_configured"] is True
        assert data["embedding"]["enabled"] is True
        assert data["embedding"]["api_key"] is None
        assert data["embedding"]["api_key_configured"] is True

    async def test_save_config_preserves_hidden_credentials(self, client: AsyncClient):
        """页面留空保存时应保留同一提供商已有的本机 Key。"""
        from app.config import runtime_path

        config_path = runtime_path("model_config.json")
        config_path.write_text(
            json.dumps(
                {
                    "provider": "zhipu",
                    "model_name": "glm-5.2",
                    "api_key": "local-secret",
                    "base_url": "https://open.bigmodel.cn/api/paas/v4",
                    "tasks": {
                        "diagram": {
                            "provider": "sensenova",
                            "model_name": "sensenova-u1-fast",
                            "api_key": "diagram-secret",
                            "base_url": "https://token.sensenova.cn/v1",
                        }
                    },
                    "fallback": {
                        "enabled": True,
                        "provider": "qwen",
                        "model_name": "qwen-plus",
                        "api_key": "fallback-secret",
                        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    },
                    "embedding": {
                        "enabled": True,
                        "provider": "openai",
                        "model_name": "text-embedding-3-small",
                        "api_key": "embedding-secret",
                        "base_url": "https://api.openai.com/v1",
                    },
                }
            ),
            encoding="utf-8",
        )

        response = await client.post(
            "/api/v1/model/config",
            json={
                "provider": "zhipu",
                "model_name": "glm-5.2",
                "api_key": "",
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "tasks": {
                    "diagram": {
                        "provider": "sensenova",
                        "model_name": "sensenova-u1-fast",
                        "api_key": "",
                        "base_url": "https://token.sensenova.cn/v1",
                    }
                },
                "fallback": {
                    "enabled": True,
                    "provider": "qwen",
                    "model_name": "qwen-plus",
                    "api_key": "",
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                },
                "embedding": {
                    "enabled": True,
                    "provider": "openai",
                    "model_name": "text-embedding-3-small",
                    "api_key": "",
                    "base_url": "https://api.openai.com/v1",
                },
            },
        )
        saved = json.loads(config_path.read_text(encoding="utf-8"))

        assert response.status_code == 200
        assert saved["api_key"] == "local-secret"
        assert saved["tasks"]["diagram"]["api_key"] == "diagram-secret"
        assert saved["fallback"]["api_key"] == "fallback-secret"
        assert saved["embedding"]["api_key"] == "embedding-secret"

    async def test_save_config_anthropic(self, client: AsyncClient):
        """保存 Anthropic 配置应返回成功"""
        response = await client.post(
            "/api/v1/model/config",
            json={
                "provider": "anthropic",
                "model_name": "claude-3-5-sonnet-20241022",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_save_config_ollama(self, client: AsyncClient):
        """保存 Ollama 配置应返回成功"""
        response = await client.post(
            "/api/v1/model/config",
            json={
                "provider": "ollama",
                "model_name": "qwen2.5:14b",
                "base_url": "http://localhost:11434",
            },
        )
        assert response.status_code == 200

    async def test_save_config_siliconflow(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/model/config",
            json={
                "provider": "siliconflow",
                "model_name": "Qwen/Qwen3-8B",
                "api_key": "test-only-key",
                "base_url": "https://api.siliconflow.cn/v1",
            },
        )

        assert response.status_code == 200

    async def test_save_config_invalid_provider(self, client: AsyncClient):
        """无效的 provider 应返回 422"""
        response = await client.post(
            "/api/v1/model/config",
            json={
                "provider": "invalid_provider",
                "model_name": "test",
            },
        )
        assert response.status_code == 422

    async def test_save_config_missing_provider(self, client: AsyncClient):
        """缺少 provider 应返回 422"""
        response = await client.post(
            "/api/v1/model/config",
            json={"model_name": "test"},
        )
        assert response.status_code == 422

    async def test_save_config_missing_model_name(self, client: AsyncClient):
        """缺少 model_name 应返回 422"""
        response = await client.post(
            "/api/v1/model/config",
            json={"provider": "openai"},
        )
        assert response.status_code == 422

    async def test_save_config_temperature_boundary_low(self, client: AsyncClient):
        """temperature < 0 应返回 422"""
        response = await client.post(
            "/api/v1/model/config",
            json={
                "provider": "openai",
                "model_name": "gpt-4o",
                "temperature": -0.1,
            },
        )
        assert response.status_code == 422

    async def test_save_config_temperature_boundary_high(self, client: AsyncClient):
        """temperature > 2 应返回 422"""
        response = await client.post(
            "/api/v1/model/config",
            json={
                "provider": "openai",
                "model_name": "gpt-4o",
                "temperature": 2.1,
            },
        )
        assert response.status_code == 422

    async def test_save_config_max_tokens_zero(self, client: AsyncClient):
        """max_tokens < 1 应返回 422"""
        response = await client.post(
            "/api/v1/model/config",
            json={
                "provider": "openai",
                "model_name": "gpt-4o",
                "max_tokens": 0,
            },
        )
        assert response.status_code == 422


class TestModelConnection:
    """POST /api/v1/model/test 测试套件"""

    async def test_capabilities_endpoint_never_calls_provider(
        self,
        client: AsyncClient,
    ):
        response = await client.get(
            "/api/v1/model/capabilities",
            params={
                "provider": "qwen",
                "model_name": "qwen-plus",
                "task": "vision",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "unsupported"

    async def test_real_capability_probe_uses_matching_saved_task_key(
        self,
        client: AsyncClient,
        monkeypatch,
    ):
        """A real task probe may reuse only the matching task credential."""
        from app.config import runtime_path

        runtime_path("model_config.json").write_text(
            json.dumps(
                {
                    "provider": "zhipu",
                    "model_name": "glm-5.2",
                    "api_key": "primary-secret",
                    "tasks": {
                        "translation": {
                            "provider": "qwen",
                            "model_name": "qwen-plus",
                            "api_key": "task-secret",
                            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        async def fake_probe(profile, task):
            assert profile["provider"] == "qwen"
            assert profile["api_key"] == "task-secret"
            assert task == "translation"
            return {
                "success": True,
                "status": "passed",
                "provider": "qwen",
                "model_name": "qwen-plus",
                "task": "translation",
                "capability": "text",
                "tested_at": "2026-09-02T00:00:00+00:00",
                "latency_ms": 12,
                "prompt_tokens": 7,
                "completion_tokens": 3,
                "total_tokens": 10,
                "detail_zh": "通过",
                "detail_en": "Passed",
                "error": None,
            }

        monkeypatch.setattr(
            "app.services.inference.capability_probe.run_capability_probe",
            fake_probe,
        )
        monkeypatch.setattr(
            "app.services.inference.capability_probe.save_probe_report",
            lambda _report: None,
        )
        response = await client.post(
            "/api/v1/model/capabilities/probe",
            json={
                "provider": "qwen",
                "model_name": "qwen-plus",
                "task": "translation",
            },
        )

        assert response.status_code == 200
        assert response.json()["total_tokens"] == 10

    async def test_real_capability_probe_never_reuses_cross_provider_key(
        self,
        client: AsyncClient,
        monkeypatch,
    ):
        from app.config import runtime_path, settings

        runtime_path("model_config.json").write_text(
            json.dumps(
                {
                    "provider": "zhipu",
                    "model_name": "glm-5.2",
                    "api_key": "zhipu-secret",
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(settings, "DEFAULT_LLM_PROVIDER", "zhipu")
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "zhipu-env-secret")

        async def fake_probe(profile, task):
            assert profile["provider"] == "qwen"
            assert profile["api_key"] is None
            return {
                "success": False,
                "status": "failed",
                "provider": "qwen",
                "model_name": "qwen-plus",
                "task": task,
                "capability": "text",
                "tested_at": "2026-09-02T00:00:00+00:00",
                "latency_ms": 1,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "detail_zh": "失败",
                "detail_en": "Failed",
                "error": "missing key",
            }

        monkeypatch.setattr(
            "app.services.inference.capability_probe.run_capability_probe",
            fake_probe,
        )
        monkeypatch.setattr(
            "app.services.inference.capability_probe.save_probe_report",
            lambda _report: None,
        )
        response = await client.post(
            "/api/v1/model/capabilities/probe",
            json={
                "provider": "qwen",
                "model_name": "qwen-plus",
                "task": "assistant",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is False

    async def test_embedding_connection_reports_dimensions(
        self,
        client: AsyncClient,
        monkeypatch,
    ):
        from app.services.retrieval.embeddings import EmbeddingBatch

        embed = AsyncMock(return_value=EmbeddingBatch(vectors=[[0.1, 0.2, 0.3]], input_tokens=5))
        monkeypatch.setattr(
            "app.services.retrieval.embeddings.EmbeddingGateway.embed",
            embed,
        )
        response = await client.post(
            "/api/v1/model/test-embedding",
            json={
                "enabled": True,
                "provider": "openai",
                "model_name": "text-embedding-3-small",
                "api_key": "test-key",
                "base_url": "https://api.openai.com/v1",
            },
        )

        data = response.json()
        assert response.status_code == 200
        assert data["success"] is True
        assert data["model_info"]["dimensions"] == 3
        assert data["model_info"]["input_tokens"] == 5

    async def test_cross_provider_probe_does_not_reuse_primary_key(
        self,
        client: AsyncClient,
        monkeypatch,
    ):
        from app.config import settings

        monkeypatch.setattr(settings, "DEFAULT_LLM_PROVIDER", "zhipu")
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "zhipu-secret")

        async def inspect_profile(gateway):
            assert gateway.provider == "qwen"
            assert gateway._api_key is None
            return {"success": False, "error": "missing qwen key"}

        monkeypatch.setattr(
            "app.services.llm.gateway.LLMGateway.test_connection",
            inspect_profile,
        )
        response = await client.post(
            "/api/v1/model/test",
            json={
                "provider": "qwen",
                "model_name": "qwen-plus",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is False

    async def test_embedding_connection_accepts_debug_localhost(
        self,
        client: AsyncClient,
        monkeypatch,
    ):
        from app.config import settings
        from app.services.retrieval.embeddings import EmbeddingBatch

        monkeypatch.setattr(settings, "DEBUG", True)
        monkeypatch.setattr(
            "app.services.retrieval.embeddings.EmbeddingGateway.embed",
            AsyncMock(return_value=EmbeddingBatch(vectors=[[0.1, 0.2]])),
        )
        response = await client.post(
            "/api/v1/model/test-embedding",
            json={
                "enabled": True,
                "provider": "ollama",
                "model_name": "nomic-embed-text",
                "base_url": "http://127.0.0.1:11434",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_test_connection_returns_response(self, client: AsyncClient):
        """测试连接端点应返回标准结构"""
        response = await client.post(
            "/api/v1/model/test",
            json={
                "provider": "openai",
                "model_name": "gpt-4o",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "latency_ms" in data
        assert "model_info" in data
        assert "error" in data

    async def test_test_connection_not_implemented(self, client: AsyncClient):
        """当前实现应返回 success=False"""
        response = await client.post(
            "/api/v1/model/test",
            json={
                "provider": "openai",
                "model_name": "gpt-4o",
            },
        )
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None

    async def test_test_connection_missing_provider(self, client: AsyncClient):
        """缺少 provider 应返回 422"""
        response = await client.post(
            "/api/v1/model/test",
            json={"model_name": "gpt-4o"},
        )
        assert response.status_code == 422

    async def test_test_connection_timeout_has_actionable_error(self, client: AsyncClient):
        """探针超时不应再返回空错误。"""
        with patch(
            "app.services.llm.gateway.LLMGateway.test_connection",
            new=AsyncMock(side_effect=TimeoutError),
        ):
            response = await client.post(
                "/api/v1/model/test",
                json={"provider": "zhipu", "model_name": "glm-5.2"},
            )

        assert response.status_code == 200
        assert response.json()["success"] is False
        assert "15 秒" in response.json()["error"]
