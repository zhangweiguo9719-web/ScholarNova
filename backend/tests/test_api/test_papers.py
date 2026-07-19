"""
论文端点测试
"""

import uuid

import pytest
from httpx import AsyncClient

from app.models.paper import PaperEntity


class TestGetPaper:
    """GET /api/v1/papers/{paper_id} 测试套件"""

    async def test_get_paper_not_found(self, client: AsyncClient):
        """获取不存在的论文应返回 404"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/papers/{fake_id}")
        assert response.status_code == 404

    async def test_get_paper_invalid_uuid(self, client: AsyncClient):
        """Paper IDs may come from external sources; unknown strings return 404."""
        response = await client.get("/api/v1/papers/not-a-uuid")
        assert response.status_code == 404

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
        response = await client.get(f"/api/v1/evidence/{run_id}/{paper_id}")
        assert response.status_code == 200
        data = response.json()
        assert "paper_id" in data
        assert "run_id" in data
        assert "evidence_spans" in data

    async def test_get_evidence_empty_list(self, client: AsyncClient):
        """不存在的论文证据应返回空列表"""
        run_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/evidence/{run_id}/{paper_id}")
        data = response.json()
        assert data["evidence_spans"] == []

    async def test_get_evidence_external_run_id(self, client: AsyncClient):
        """External run identifiers are accepted and return an empty result."""
        paper_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/evidence/external-run/{paper_id}")
        assert response.status_code == 200
        assert response.json()["run_id"] == "external-run"

    async def test_get_evidence_external_paper_id(self, client: AsyncClient):
        """External paper identifiers are accepted and returned verbatim."""
        run_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/evidence/{run_id}/CorpusId:123")
        assert response.status_code == 200
        assert response.json()["paper_id"] == "CorpusId:123"


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


class TestFulltextUpload:
    """Imported PDFs are available to the full-text analysis pipeline."""

    async def test_upload_and_status(self, client: AsyncClient, db_session):
        import pymupdf

        paper = PaperEntity(
            id=str(uuid.uuid4()),
            title="Upload API paper",
            abstract="Test abstract",
            authors=[{"name": "Researcher"}],
            source="test",
        )
        db_session.add(paper)
        await db_session.flush()

        document = pymupdf.open()
        document.new_page().insert_text((72, 72), "A valid test paper")
        pdf_bytes = document.tobytes()
        document.close()

        response = await client.post(
            f"/api/v1/papers/{paper.id}/fulltext",
            files={"file": ("paper.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        assert response.json()["available"] is True
        assert response.json()["page_count"] == 1

        status = await client.get(f"/api/v1/papers/{paper.id}/fulltext/status")
        assert status.status_code == 200
        assert status.json()["available"] is True

class TestListPapers:
    """GET /api/v1/papers endpoint contract."""

    async def test_list_papers_returns_list(self, client: AsyncClient):
        response = await client.get("/api/v1/papers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_papers_accepts_pagination(self, client: AsyncClient):
        response = await client.get("/api/v1/papers?page=2&page_size=5")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
