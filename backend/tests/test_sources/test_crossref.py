"""
CrossRef API 测试（Mock HTTP 响应）
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.sources.crossref import CrossRefSource


MOCK_SEARCH_RESPONSE = {
    "status": "ok",
    "message": {
        "total-results": 2,
        "items": [
            {
                "DOI": "10.1000/test1",
                "title": ["Attention Is All You Need"],
                "author": [
                    {"given": "Ashish", "family": "Vaswani"},
                    {"given": "Noam", "family": "Shazeer"},
                ],
                "abstract": "The dominant sequence transduction models...",
                "published-print": {"date-parts": [[2017]]},
                "container-title": ["NeurIPS"],
                "is-referenced-by-count": 120000,
                "URL": "https://doi.org/10.1000/test1",
                "link": [
                    {
                        "content-type": "application/pdf",
                        "URL": "https://example.com/paper.pdf",
                    }
                ],
                "subject": ["Computer Science", "Machine Learning"],
            },
            {
                "DOI": "10.1000/test2",
                "title": ["BERT"],
                "author": [
                    {"given": "Jacob", "family": "Devlin"},
                ],
                "abstract": None,
                "published-online": {"date-parts": [[2019]]},
                "container-title": ["NAACL"],
                "is-referenced-by-count": 80000,
                "URL": "https://doi.org/10.1000/test2",
                "link": [],
            },
        ],
    },
}


def _make_mock_response(json_data, status_code=200):
    """创建 mock HTTP 响应（json/raise_for_status 为同步方法）"""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}
    return mock_response


def _make_mock_client(response):
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=response)
    mock_client.is_closed = False
    return mock_client


class TestCrossRefSource:
    """CrossRefSource 测试套件"""

    def test_name(self):
        source = CrossRefSource()
        assert source.name == "crossref"

    def test_base_api_url(self):
        source = CrossRefSource()
        assert "crossref.org" in source.base_api_url

    def test_headers_with_email(self):
        source = CrossRefSource(email="test@example.com")
        headers = source._get_headers()
        assert "test@example.com" in headers["User-Agent"]

    def test_headers_without_email(self):
        source = CrossRefSource()
        headers = source._get_headers()
        assert "ScholarNova" in headers["User-Agent"]

    async def test_search_success(self):
        mock_response = _make_mock_response(MOCK_SEARCH_RESPONSE)
        source = CrossRefSource(email="test@example.com")
        source._client = _make_mock_client(mock_response)

        papers = await source.search("attention mechanism", max_results=10)

        assert len(papers) == 2
        assert papers[0].title == "Attention Is All You Need"
        assert papers[0].source == "crossref"
        assert papers[0].doi == "10.1000/test1"
        assert papers[0].is_open_access is True
        assert papers[0].citation_count == 120000

    async def test_search_empty_result(self):
        mock_response = _make_mock_response(
            {"status": "ok", "message": {"items": []}}
        )
        source = CrossRefSource()
        source._client = _make_mock_client(mock_response)

        papers = await source.search("nonexistent")
        assert papers == []

    async def test_search_error_returns_empty(self):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Service unavailable"))
        mock_client.is_closed = False

        source = CrossRefSource()
        source._client = mock_client

        papers = await source.search("test")
        assert papers == []

    async def test_get_paper_success(self):
        mock_response = _make_mock_response(
            {"message": MOCK_SEARCH_RESPONSE["message"]["items"][0]}
        )
        source = CrossRefSource()
        source._client = _make_mock_client(mock_response)

        paper = await source.get_paper("10.1000/test1")
        assert paper is not None
        assert paper.title == "Attention Is All You Need"

    async def test_get_paper_not_found(self):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Not found"))
        mock_client.is_closed = False

        source = CrossRefSource()
        source._client = mock_client

        paper = await source.get_paper("nonexistent")
        assert paper is None

    async def test_get_pdf_url(self):
        mock_response = _make_mock_response(
            {"message": MOCK_SEARCH_RESPONSE["message"]["items"][0]}
        )
        source = CrossRefSource()
        source._client = _make_mock_client(mock_response)

        url = await source.get_pdf_url("10.1000/test1")
        assert url == "https://example.com/paper.pdf"

    async def test_get_pdf_url_none(self):
        mock_response = _make_mock_response(
            {"message": MOCK_SEARCH_RESPONSE["message"]["items"][1]}
        )
        source = CrossRefSource()
        source._client = _make_mock_client(mock_response)

        url = await source.get_pdf_url("10.1000/test2")
        assert url is None

    async def test_health_check_success(self):
        mock_response = _make_mock_response(
            {"message": {"total-results": 150000000}}
        )
        source = CrossRefSource()
        source._client = _make_mock_client(mock_response)

        result = await source.health_check()
        assert result["status"] == "ok"
        assert result["source"] == "crossref"

    async def test_health_check_error(self):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Service down"))
        mock_client.is_closed = False

        source = CrossRefSource()
        source._client = mock_client

        result = await source.health_check()
        assert result["status"] == "error"

    def test_parse_paper_author_format(self):
        source = CrossRefSource()
        data = {
            "DOI": "10.1000/test",
            "title": ["Test Paper"],
            "author": [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"},
            ],
            "is-referenced-by-count": 0,
        }
        paper = source._parse_paper(data)
        assert "John Doe" in paper.authors
        assert "Jane Smith" in paper.authors

    def test_parse_paper_no_pdf(self):
        source = CrossRefSource()
        data = {
            "DOI": "10.1000/test",
            "title": ["Test"],
            "author": [],
            "link": [],
            "is-referenced-by-count": 0,
        }
        paper = source._parse_paper(data)
        assert paper.pdf_url is None
        assert paper.is_open_access is False

    def test_parse_paper_year_from_online(self):
        source = CrossRefSource()
        data = {
            "DOI": "10.1000/test",
            "title": ["Test"],
            "author": [],
            "published-online": {"date-parts": [[2023]]},
            "is-referenced-by-count": 0,
        }
        paper = source._parse_paper(data)
        assert paper.year == 2023

    def test_parse_paper_no_year(self):
        source = CrossRefSource()
        data = {
            "DOI": "10.1000/test",
            "title": ["Test"],
            "author": [],
            "is-referenced-by-count": 0,
        }
        paper = source._parse_paper(data)
        assert paper.year is None

    def test_parse_paper_no_doi(self):
        source = CrossRefSource()
        data = {
            "title": ["Test"],
            "author": [],
            "is-referenced-by-count": 0,
        }
        paper = source._parse_paper(data)
        assert paper is None

    def test_clean_abstract_removes_jats_markup(self):
        source = CrossRefSource()
        result = source._clean_abstract(
            "<jats:title>Abstract</jats:title><jats:p>A &amp; B result.</jats:p>"
        )
        assert result == "Abstract A & B result."
