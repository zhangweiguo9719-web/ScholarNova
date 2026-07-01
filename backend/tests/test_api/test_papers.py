"""
论文端点测试
"""

import uuid

import pytest
from httpx import AsyncClient


class TestGetPaper:
    """GET /api/v1/papers/{paper_id} 测试套件"""

    async def test_get_paper_not_found(self, client: AsyncClient):
        """获取不存在的论文应返回 404"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/papers/{fake_id}")
        assert response.status_code == 404

    async def test_get_paper_invalid_uuid(self, client: AsyncClient):
        """无效的 UUID 应返回 422"""
        response = await client.get("/api/v1/papers/not-a-uuid")
        assert response.status_code == 422

    async def test_get_paper_error_detail(self, client: AsyncClient):
        """404 响应应包含 detail 字段"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/papers/{fake_id}")
        data = response.json()
        assert "detail" in data


class TestGetEvidence:
    """GET /api/v1/papers/{run_id}/{paper_id}/evidence 测试套件"""

    async def test_get_evidence_returns_response(self, client: AsyncClient):
        """获取证据应返回 EvidenceResponse 结构"""
        run_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/papers/{run_id}/{paper_id}/evidence")
        assert response.status_code == 200
        data = response.json()
        assert "paper_id" in data
        assert "run_id" in data
        assert "evidence_spans" in data

    async def test_get_evidence_empty_list(self, client: AsyncClient):
        """不存在的论文证据应返回空列表"""
        run_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/papers/{run_id}/{paper_id}/evidence")
        data = response.json()
        assert data["evidence_spans"] == []

    async def test_get_evidence_invalid_run_id(self, client: AsyncClient):
        """无效的 run_id 应返回 422"""
        paper_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/papers/not-a-uuid/{paper_id}/evidence")
        assert response.status_code == 422

    async def test_get_evidence_invalid_paper_id(self, client: AsyncClient):
        """无效的 paper_id 应返回 422"""
        run_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/papers/{run_id}/not-a-uuid/evidence")
        assert response.status_code == 422


class TestAnalyzePaper:
    """POST /api/v1/papers/{paper_id}/analyze 测试套件"""

    async def test_analyze_nonexistent_paper(self, client: AsyncClient):
        """分析不存在的论文应返回 404"""
        fake_id = str(uuid.uuid4())
        response = await client.post(
            f"/api/v1/papers/{fake_id}/analyze",
            json={"query": "summarize this paper", "analysis_type": "full"},
        )
        assert response.status_code == 404

    async def test_analyze_missing_query(self, client: AsyncClient):
        """缺少 query 字段应返回 422"""
        fake_id = str(uuid.uuid4())
        response = await client.post(
            f"/api/v1/papers/{fake_id}/analyze",
            json={"analysis_type": "full"},
        )
        assert response.status_code == 422

    async def test_analyze_invalid_analysis_type(self, client: AsyncClient):
        """无效的 analysis_type 应返回 422"""
        fake_id = str(uuid.uuid4())
        response = await client.post(
            f"/api/v1/papers/{fake_id}/analyze",
            json={"query": "test", "analysis_type": "invalid_type"},
        )
        assert response.status_code == 422


class TestComparePapers:
    """POST /api/v1/papers/compare 测试套件"""

    async def test_compare_papers_empty_list(self, client: AsyncClient):
        """空论文列表应返回 422"""
        response = await client.post(
            "/api/v1/papers/compare",
            json={"paper_ids": [], "query": "compare methods"},
        )
        assert response.status_code == 422

    async def test_compare_papers_single_paper(self, client: AsyncClient):
        """只有1篇论文应返回 422（最少需要2篇）"""
        response = await client.post(
            "/api/v1/papers/compare",
            json={
                "paper_ids": [str(uuid.uuid4())],
                "query": "compare methods",
            },
        )
        assert response.status_code == 422

    async def test_compare_papers_valid_request(self, client: AsyncClient):
        """有效的对比请求应返回 200"""
        response = await client.post(
            "/api/v1/papers/compare",
            json={
                "paper_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
                "query": "compare methods",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "papers" in data
        assert "comparison" in data

    async def test_compare_papers_missing_query(self, client: AsyncClient):
        """缺少 query 应返回 422"""
        response = await client.post(
            "/api/v1/papers/compare",
            json={
                "paper_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            },
        )
        assert response.status_code == 422
