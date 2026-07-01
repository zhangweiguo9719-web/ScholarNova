"""
数据源集成测试

使用真实 API 调用，标记为 @pytest.mark.integration。
默认跳过（需要网络访问），手动运行:
    pytest -m integration tests/test_sources/test_integration.py -v
"""

import asyncio

import pytest

from app.services.sources.arxiv import ArxivSource
from app.services.sources.crossref import CrossRefSource
from app.services.sources.openalex import OpenAlexSource
from app.services.sources.semantic_scholar import SemanticScholarSource
from app.services.search.retriever import Retriever
from app.schemas.query import DataSource, SubQuery

# 标记所有测试为 integration
pytestmark = pytest.mark.integration


# ==========================================================================
# Semantic Scholar
# ==========================================================================


class TestSemanticScholarIntegration:
    """Semantic Scholar 集成测试"""

    @pytest.mark.asyncio
    async def test_search(self):
        async with SemanticScholarSource(timeout=15) as source:
            papers = await source.search("attention mechanism", max_results=5)
            assert len(papers) > 0
            paper = papers[0]
            assert paper.title
            assert paper.source == "semantic_scholar"
            assert paper.id  # UUID

    @pytest.mark.asyncio
    async def test_get_paper(self):
        async with SemanticScholarSource(timeout=15) as source:
            paper = await source.get_paper("204e3073870fae3d05bcbc2f6a8e263d9b72e776")
            assert paper is not None
            assert paper.title
            assert paper.source == "semantic_scholar"

    @pytest.mark.asyncio
    async def test_get_pdf_url(self):
        async with SemanticScholarSource(timeout=15) as source:
            url = await source.get_pdf_url("204e3073870fae3d05bcbc2f6a8e263d9b72e776")
            # 此论文有 OA PDF
            assert url is not None
            assert url.startswith("http")

    @pytest.mark.asyncio
    async def test_health_check(self):
        async with SemanticScholarSource(timeout=15) as source:
            result = await source.health_check()
            assert result["status"] == "ok"
            assert result["source"] == "semantic_scholar"

    @pytest.mark.asyncio
    async def test_paper_fields(self):
        """验证返回的论文包含所有必要字段"""
        async with SemanticScholarSource(timeout=15) as source:
            papers = await source.search("BERT NLP", max_results=3)
            assert len(papers) > 0
            paper = papers[0]
            assert hasattr(paper, "title")
            assert hasattr(paper, "authors")
            assert hasattr(paper, "abstract")
            assert hasattr(paper, "year")
            assert hasattr(paper, "venue")
            assert hasattr(paper, "doi")
            assert hasattr(paper, "citation_count")
            assert hasattr(paper, "pdf_url")
            assert hasattr(paper, "is_open_access")
            assert isinstance(paper.authors, list)


# ==========================================================================
# OpenAlex
# ==========================================================================


class TestOpenAlexIntegration:
    """OpenAlex 集成测试"""

    @pytest.mark.asyncio
    async def test_search(self):
        async with OpenAlexSource(timeout=15) as source:
            papers = await source.search("attention mechanism", max_results=5)
            assert len(papers) > 0
            paper = papers[0]
            assert paper.title
            assert paper.source == "openalex"

    @pytest.mark.asyncio
    async def test_search_with_email(self):
        async with OpenAlexSource(email="test@example.com", timeout=15) as source:
            papers = await source.search("deep learning", max_results=3)
            assert len(papers) > 0

    @pytest.mark.asyncio
    async def test_get_paper(self):
        async with OpenAlexSource(timeout=15) as source:
            paper = await source.get_paper("W2741809807")
            assert paper is not None
            assert paper.title
            assert paper.source == "openalex"

    @pytest.mark.asyncio
    async def test_get_pdf_url(self):
        async with OpenAlexSource(timeout=15) as source:
            url = await source.get_pdf_url("W2741809807")
            # 此论文可能有 OA PDF
            # 不强制断言有值，只检查不报错
            assert url is None or url.startswith("http")

    @pytest.mark.asyncio
    async def test_health_check(self):
        async with OpenAlexSource(timeout=15) as source:
            result = await source.health_check()
            assert result["status"] == "ok"
            assert result["source"] == "openalex"

    @pytest.mark.asyncio
    async def test_reconstruct_abstract(self):
        """验证摘要重建"""
        async with OpenAlexSource(timeout=15) as source:
            papers = await source.search("BERT language model", max_results=5)
            # 找到有摘要的论文
            has_abstract = any(p.abstract for p in papers)
            assert has_abstract, "应至少有一篇论文有摘要"


# ==========================================================================
# CrossRef
# ==========================================================================


class TestCrossRefIntegration:
    """CrossRef 集成测试"""

    @pytest.mark.asyncio
    async def test_search(self):
        async with CrossRefSource(timeout=15) as source:
            papers = await source.search("attention mechanism", max_results=5)
            assert len(papers) > 0
            paper = papers[0]
            assert paper.title
            assert paper.source == "crossref"

    @pytest.mark.asyncio
    async def test_search_with_email(self):
        async with CrossRefSource(email="test@example.com", timeout=15) as source:
            papers = await source.search("deep learning", max_results=3)
            assert len(papers) > 0

    @pytest.mark.asyncio
    async def test_get_paper_by_doi(self):
        async with CrossRefSource(timeout=15) as source:
            paper = await source.get_paper("10.1038/s41586-020-2649-2")
            assert paper is not None
            assert paper.title
            assert paper.doi == "10.1038/s41586-020-2649-2"
            assert paper.source == "crossref"

    @pytest.mark.asyncio
    async def test_get_pdf_url(self):
        async with CrossRefSource(timeout=15) as source:
            url = await source.get_pdf_url("10.1038/s41586-020-2649-2")
            # 不强制断言有值
            assert url is None or url.startswith("http")

    @pytest.mark.asyncio
    async def test_health_check(self):
        async with CrossRefSource(timeout=15) as source:
            result = await source.health_check()
            assert result["status"] == "ok"
            assert result["source"] == "crossref"

    @pytest.mark.asyncio
    async def test_paper_authors(self):
        """验证作者解析"""
        async with CrossRefSource(timeout=15) as source:
            papers = await source.search("BERT deep learning", max_results=5)
            has_authors = any(len(p.authors) > 0 for p in papers)
            assert has_authors, "应至少有一篇论文有作者"


# ==========================================================================
# arXiv
# ==========================================================================


class TestArxivIntegration:
    """arXiv 集成测试"""

    @pytest.mark.asyncio
    async def test_search(self):
        async with ArxivSource(timeout=15) as source:
            papers = await source.search("attention mechanism", max_results=5)
            assert len(papers) > 0
            paper = papers[0]
            assert paper.title
            assert paper.source == "arxiv"
            assert paper.is_open_access is True

    @pytest.mark.asyncio
    async def test_get_paper(self):
        async with ArxivSource(timeout=15) as source:
            paper = await source.get_paper("1706.03762")
            assert paper is not None
            assert "Attention" in paper.title
            assert paper.year == 2017
            assert paper.source == "arxiv"

    @pytest.mark.asyncio
    async def test_get_pdf_url(self):
        source = ArxivSource()
        url = await source.get_pdf_url("1706.03762")
        assert url == "http://arxiv.org/pdf/1706.03762"

    @pytest.mark.asyncio
    async def test_health_check(self):
        async with ArxivSource(timeout=15) as source:
            result = await source.health_check()
            assert result["status"] == "ok"
            assert result["source"] == "arxiv"

    @pytest.mark.asyncio
    async def test_paper_fields(self):
        """验证返回的论文包含所有必要字段"""
        async with ArxivSource(timeout=15) as source:
            papers = await source.search("BERT NLP", max_results=3)
            assert len(papers) > 0
            paper = papers[0]
            assert paper.venue == "arXiv"
            assert paper.citation_count == 0
            assert isinstance(paper.authors, list)

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """验证 arXiv 请求间隔遵守 3 秒限制"""
        import time
        async with ArxivSource(timeout=15) as source:
            start = time.monotonic()
            await source.search("test1", max_results=1)
            await source.search("test2", max_results=1)
            elapsed = time.monotonic() - start
            assert elapsed >= 2.5, f"两次请求间隔应 >= 3s，实际 {elapsed:.1f}s"


# ==========================================================================
# Retriever 集成测试
# ==========================================================================


class TestRetrieverIntegration:
    """检索器集成测试"""

    @pytest.mark.asyncio
    async def test_parallel_retrieval(self):
        """测试并行检索多个数据源"""
        sources = {
            DataSource.ARXIV: ArxivSource(timeout=15),
        }
        retriever = Retriever(sources=sources, timeout=30)

        sub_queries = [
            SubQuery(
                query="attention mechanism transformer",
                source=DataSource.ARXIV,
                rationale="arXiv 有最新的预印本",
            ),
        ]

        result = await retriever.retrieve(sub_queries, max_results=5)

        assert result.total_papers > 0
        assert result.successful_sources >= 1
        assert len(result.source_statuses) == 1
        status = result.source_statuses[0]
        assert status.success is True
        assert status.elapsed_ms > 0
        assert status.paper_count > 0

    @pytest.mark.asyncio
    async def test_source_status_on_success(self):
        """验证成功时的 SourceStatus"""
        sources = {
            DataSource.ARXIV: ArxivSource(timeout=15),
        }
        retriever = Retriever(sources=sources, timeout=30)

        sub_queries = [
            SubQuery(
                query="BERT",
                source=DataSource.ARXIV,
                rationale="test",
            ),
        ]

        result = await retriever.retrieve(sub_queries, max_results=3)

        assert len(result.source_statuses) == 1
        status = result.source_statuses[0]
        assert status.source == "arxiv"
        assert status.success is True
        assert status.error is None

    @pytest.mark.asyncio
    async def test_source_status_on_failure(self):
        """验证失败时的 SourceStatus（未知数据源）"""
        from app.services.sources.base import BaseSource
        from typing import List, Optional
        from app.schemas.paper import Paper

        class FailingSource(BaseSource):
            @property
            def name(self):
                return "failing"

            @property
            def base_api_url(self):
                return "http://localhost:1"

            async def search(self, query, max_results=50):
                raise ConnectionError("故意失败")

            async def get_paper(self, paper_id):
                return None

            async def get_pdf_url(self, paper_id):
                return None

            async def health_check(self):
                return {"status": "error"}

        sources = {
            DataSource.ARXIV: FailingSource(timeout=2),
        }
        retriever = Retriever(sources=sources, timeout=5)

        sub_queries = [
            SubQuery(
                query="test",
                source=DataSource.ARXIV,
                rationale="test failure",
            ),
        ]

        result = await retriever.retrieve(sub_queries, max_results=5)

        assert result.total_papers == 0
        assert result.failed_sources == 1
        assert result.successful_sources == 0
        assert result.source_statuses[0].success is False
        assert result.source_statuses[0].error is not None

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """测试对所有数据源执行健康检查"""
        sources = {
            DataSource.ARXIV: ArxivSource(timeout=15),
        }
        retriever = Retriever(sources=sources)

        results = await retriever.health_check_all()
        assert "arxiv" in results
        assert results["arxiv"]["status"] == "ok"
