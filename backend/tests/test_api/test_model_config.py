"""
模型配置端点测试
"""

import pytest
from httpx import AsyncClient


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
