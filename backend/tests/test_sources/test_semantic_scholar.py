"""
Semantic Scholar API 测试（Mock HTTP 响应）
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.schemas.paper import Paper
from app.services.sources import semantic_scholar as semantic_scholar_module
from app.services.sources.semantic_scholar import SemanticScholarSource


# Mock API 响应数据
MOCK_SEARCH_RESPONSE = {
    "total": 2,
    "data": [
        {
            "paperId": "abc123",
            "corpusId": 123456,
            "title": "Attention Is All You Need",
            "abstract": "The dominant sequence transduction models...",
            "authors": [
                {"name": "Ashish Vaswani"},
                {"name": "Noam Shazeer"},
            ],
            "year": 2017,
            "venue": "NeurIPS",
            "citationCount": 120000,
            "externalIds": {"DOI": "10.48550/arXiv.1706.03762"},
            "openAccessPdf": {"url": "https://arxiv.org/pdf/1706.03762"},
            "fieldsOfStudy": ["Computer Science"],
        },
        {
            "paperId": "def456",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "abstract": "We introduce a new language representation model...",
            "authors": [{"name": "Jacob Devlin"}],
            "year": 2019,
            "venue": "NAACL",
            "citationCount": 80000,
            "externalIds": {"DOI": "10.18653/v1/N19-1423"},
            "openAccessPdf": None,
            "fieldsOfStudy": ["Computer Science"],
        },
    ],
}

MOCK_PAPER_RESPONSE = {
    "paperId": "abc123",
    "corpusId": 123456,
    "title": "Attention Is All You Need",
    "abstract": "The dominant sequence transduction models...",
    "authors": [{"name": "Ashish Vaswani"}],
    "year": 2017,
    "venue": "NeurIPS",
    "citationCount": 120000,
    "externalIds": {"DOI": "10.48550/arXiv.1706.03762"},
    "openAccessPdf": {"url": "https://arxiv.org/pdf/1706.03762"},
    "fieldsOfStudy": ["Computer Science"],
}


@pytest.fixture(autouse=True)
def isolate_semantic_scholar_cache(monkeypatch, tmp_path):
    semantic_scholar_module._S2_CACHE.clear()
    semantic_scholar_module._S2_CACHE_LOCKS.clear()
    monkeypatch.setattr(
        semantic_scholar_module,
        "_S2_CACHE_DIR",
        tmp_path / "semantic-scholar-cache",
    )


def _make_mock_response(json_data, status_code=200):
    """创建 mock HTTP 响应（json/raise_for_status 为同步方法）"""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}
    return mock_response


def _make_mock_client(response):
    """创建 mock httpx 客户端"""
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=response)
    mock_client.is_closed = False
    return mock_client


class TestSemanticScholarSource:
    """SemanticScholarSource 测试套件"""

    def test_name(self):
        source = SemanticScholarSource()
        assert source.name == "semantic_scholar"

    def test_base_api_url(self):
        source = SemanticScholarSource()
        assert "semanticscholar.org" in source.base_api_url

    def test_headers_with_api_key(self):
        source = SemanticScholarSource(api_key="test-key")
        headers = source._get_headers()
        assert "x-api-key" in headers
        assert headers["x-api-key"] == "test-key"

    def test_headers_without_api_key(self):
        source = SemanticScholarSource()
        headers = source._get_headers()
        assert "x-api-key" not in headers

    async def test_search_success(self):
        mock_response = _make_mock_response(MOCK_SEARCH_RESPONSE)
        source = SemanticScholarSource()
        source._client = _make_mock_client(mock_response)

        papers = await source.search("attention mechanism", max_results=10)

        assert len(papers) == 2
        assert papers[0].title == "Attention Is All You Need"
        assert papers[0].source == "semantic_scholar"
        assert papers[0].doi == "10.48550/arXiv.1706.03762"
        assert papers[0].corpus_id == "123456"
        assert papers[0].is_open_access is True

    async def test_search_empty_result(self):
        mock_response = _make_mock_response({"total": 0, "data": []})
        source = SemanticScholarSource()
        source._client = _make_mock_client(mock_response)

        papers = await source.search("nonexistent query")
        assert papers == []

    async def test_search_cache_avoids_duplicate_request(self):
        mock_response = _make_mock_response(MOCK_SEARCH_RESPONSE)
        source = SemanticScholarSource()
        source._client = _make_mock_client(mock_response)

        first = await source.search("unique cache contract query", max_results=7)
        semantic_scholar_module._S2_CACHE.clear()
        second = await source.search("unique cache contract query", max_results=7)

        assert len(first) == len(second) == 2
        assert source._client.request.await_count == 1

    async def test_search_error_returns_empty(self):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Network error"))
        mock_client.is_closed = False

        source = SemanticScholarSource()
        source._client = mock_client

        papers = await source.search("test")
        assert papers == []

    async def test_get_paper_success(self):
        mock_response = _make_mock_response(MOCK_PAPER_RESPONSE)
        source = SemanticScholarSource()
        source._client = _make_mock_client(mock_response)

        paper = await source.get_paper("abc123")

        assert paper is not None
        assert paper.title == "Attention Is All You Need"
        assert paper.year == 2017

    async def test_get_paper_not_found(self):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Not found"))
        mock_client.is_closed = False

        source = SemanticScholarSource()
        source._client = mock_client

        paper = await source.get_paper("nonexistent")
        assert paper is None

    async def test_search_match_success(self):
        mock_response = _make_mock_response(MOCK_PAPER_RESPONSE)
        source = SemanticScholarSource()
        source._client = _make_mock_client(mock_response)

        paper = await source.search_match("Attention Is All You Need")

        assert paper is not None
        assert paper.corpus_id == "123456"
        request = source._client.request.await_args
        assert request.args[:2] == ("GET", "/paper/search/match")

    async def test_batch_enrichment_backfills_corpus_id(self):
        mock_response = _make_mock_response([MOCK_PAPER_RESPONSE])
        source = SemanticScholarSource()
        source._client = _make_mock_client(mock_response)
        candidate = Paper(
            id="11111111-1111-1111-1111-111111111111",
            title="Attention Is All You Need",
            authors=["Ashish Vaswani"],
            doi="10.48550/arXiv.1706.03762",
            source="crossref",
            citation_count=10,
        )

        enriched = await source.enrich_with_corpus_ids([candidate])

        assert enriched[0].corpus_id == "123456"
        assert enriched[0].citation_count == 120000
        assert source._client.request.await_count == 1
        request = source._client.request.await_args
        assert request.args[:2] == ("POST", "/paper/batch")

    async def test_get_citations_parses_citing_papers(self):
        mock_response = _make_mock_response(
            {"data": [{"citingPaper": MOCK_PAPER_RESPONSE}]}
        )
        source = SemanticScholarSource()
        source._client = _make_mock_client(mock_response)

        papers = await source.get_citations("abc123")

        assert len(papers) == 1
        assert papers[0].corpus_id == "123456"
        request = source._client.request.await_args
        assert request.args[:2] == ("GET", "/paper/abc123/citations")

    async def test_find_author_id_prefers_exact_name(self):
        mock_response = _make_mock_response(
            {
                "data": [
                    {"authorId": "wrong", "name": "David Hare", "paperCount": 100},
                    {"authorId": "right", "name": "David Harel", "paperCount": 50},
                ]
            }
        )
        source = SemanticScholarSource()
        source._client = _make_mock_client(mock_response)

        author_id = await source.find_author_id("David Harel")

        assert author_id == "right"

    async def test_get_author_papers_parses_and_caches(self):
        mock_response = _make_mock_response({"data": [MOCK_PAPER_RESPONSE]})
        source = SemanticScholarSource()
        source._client = _make_mock_client(mock_response)

        papers = await source.get_author_papers("right")
        semantic_scholar_module._S2_CACHE.clear()
        cached = await source.get_author_papers("right")

        assert len(papers) == len(cached) == 1
        assert source._client.request.await_count == 1

    async def test_get_pdf_url(self):
        mock_response = _make_mock_response(MOCK_PAPER_RESPONSE)
        source = SemanticScholarSource()
        source._client = _make_mock_client(mock_response)

        url = await source.get_pdf_url("abc123")
        assert url == "https://arxiv.org/pdf/1706.03762"

    async def test_health_check_success(self):
        mock_response = _make_mock_response({"total": 100, "data": []})
        source = SemanticScholarSource()
        source._client = _make_mock_client(mock_response)

        result = await source.health_check()
        assert result["status"] == "ok"
        assert result["source"] == "semantic_scholar"

    async def test_health_check_error(self):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Service down"))
        mock_client.is_closed = False

        source = SemanticScholarSource()
        source._client = mock_client

        result = await source.health_check()
        assert result["status"] == "error"

    def test_parse_paper_with_missing_fields(self):
        source = SemanticScholarSource()
        data = {
            "paperId": "test123",
            "title": "Test Paper",
        }
        paper = source._parse_paper(data)
        assert paper is not None
        assert paper.title == "Test Paper"
        assert paper.authors == []
        assert paper.abstract is None

    def test_parse_paper_with_no_open_access(self):
        source = SemanticScholarSource()
        data = {
            "paperId": "test123",
            "title": "Test Paper",
            "authors": [],
            "openAccessPdf": None,
        }
        paper = source._parse_paper(data)
        assert paper.is_open_access is False
        assert paper.pdf_url is None

    def test_parse_paper_no_paper_id(self):
        source = SemanticScholarSource()
        data = {"title": "Test"}
        paper = source._parse_paper(data)
        assert paper is None
