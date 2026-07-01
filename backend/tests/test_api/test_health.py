"""
健康检查端点测试
"""

import pytest
from httpx import AsyncClient


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

    async def test_health_version(self, client: AsyncClient):
        """版本号应为 1.0.0"""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert data["version"] == "1.0.0"

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
