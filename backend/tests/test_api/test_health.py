"""
健康检查端点测试
"""

import pytest
from httpx import AsyncClient


class TestLLMConfigurationHealth:
    """Health checks must use task routes and never invoke a paid model."""

    @pytest.mark.parametrize("provider", ["zhipu", "qwen", "siliconflow", "openai", "anthropic"])
    async def test_saved_provider_route_is_available_without_network(self, monkeypatch, provider):
        from app import config
        from app.api.v1.health import _check_llm
        from app.services.llm.gateway import LLMGateway

        def no_model_call(*args, **kwargs):
            raise AssertionError("Health must not instantiate a model gateway")

        monkeypatch.setattr(LLMGateway, "__init__", no_model_call)
        monkeypatch.setattr(config.settings, "OPENAI_API_KEY", None)
        monkeypatch.setattr(config.settings, "ANTHROPIC_API_KEY", None)
        monkeypatch.setattr(config, "get_model_for_task", lambda task: {
            "provider": provider,
            "model": "test-model",
            "api_key": "test-only-key" if task == "analysis" else None,
            "base_url": "https://provider.example/v1",
        })
        assert await _check_llm() == "available"

    @pytest.mark.parametrize("api_key", [None, "", "  ", "ENV"])
    async def test_missing_cloud_key_is_unavailable(self, monkeypatch, api_key):
        from app import config
        from app.api.v1.health import _check_llm

        monkeypatch.setattr(config, "get_model_for_task", lambda task: {
            "provider": "zhipu", "model": "test-model", "api_key": api_key,
        })
        assert await _check_llm() == "unavailable"

    @pytest.mark.parametrize("provider", ["ollama", "custom"])
    @pytest.mark.parametrize("base_url, expected", [
        ("http://127.0.0.1:11434", "available"), ("", "unavailable"),
    ])
    async def test_keyless_local_route_needs_endpoint(self, monkeypatch, provider, base_url, expected):
        from app import config
        from app.api.v1.health import _check_llm

        monkeypatch.setattr(config, "get_model_for_task", lambda task: {
            "provider": provider, "model": "test-model", "api_key": None,
            "base_url": base_url,
        })
        assert await _check_llm() == expected

    async def test_anthropic_route_uses_its_dedicated_env_key(self, monkeypatch):
        from app import config
        from app.api.v1.health import _check_llm

        monkeypatch.setattr(config.settings, "ANTHROPIC_API_KEY", "test-only-key")
        monkeypatch.setattr(config, "get_model_for_task", lambda task: {
            "provider": "anthropic", "model": "test-model", "api_key": None,
        })
        assert await _check_llm() == "available"

    async def test_credential_alone_without_model_is_not_configured(self, monkeypatch):
        from app import config
        from app.api.v1.health import _check_llm

        monkeypatch.setattr(config, "get_model_for_task", lambda task: {
            "provider": "qwen", "model": "", "api_key": "test-only-key",
        })
        assert await _check_llm() == "unavailable"


class TestHealthCheck:
    """健康检查端点测试套件"""

    async def test_health_returns_200(self, client: AsyncClient):
        """健康检查应返回 200 状态码"""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

    async def test_health_response_structure(self, client: AsyncClient):
        """健康检查响应应包含所有必需字段"""
        response = await client.get("/api/v1/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "services" in data

    async def test_health_status_value(self, client: AsyncClient):
        """状态值应为 healthy / degraded / unhealthy 之一"""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert data["status"] in ("healthy", "degraded", "unhealthy")

    @pytest.mark.parametrize("endpoint", ["/api/v1/health", "/api/v1/health/live"])
    async def test_health_version(self, client: AsyncClient, monkeypatch, endpoint):
        """Both health endpoints must report the current application version."""
        from unittest.mock import AsyncMock

        from app import __version__
        from app.api.v1 import health

        monkeypatch.setattr(health, "_check_redis", AsyncMock(return_value="connected"))
        monkeypatch.setattr(health, "_check_llm", AsyncMock(return_value="available"))
        monkeypatch.setattr(health, "_data_source_cache", (
            health.time.monotonic(), {"semantic_scholar": "available"},
        ))
        response = await client.get(endpoint)
        data = response.json()
        assert response.status_code == 200
        assert data["version"] == __version__

    async def test_health_services_dict(self, client: AsyncClient):
        """services 字段应为字典类型"""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert isinstance(data["services"], dict)

    async def test_health_timestamp_format(self, client: AsyncClient):
        """timestamp 字段应为合法的 ISO 格式时间字符串"""
        response = await client.get("/api/v1/health")
        data = response.json()
        # 简单验证 timestamp 存在且非空
        assert data["timestamp"]
        assert isinstance(data["timestamp"], str)

    async def test_health_content_type(self, client: AsyncClient):
        """响应 Content-Type 应为 application/json"""
        response = await client.get("/api/v1/health")
        assert "application/json" in response.headers.get("content-type", "")
