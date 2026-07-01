"""
OpenAlex API 测试（Mock HTTP 响应）
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.sources.openalex import OpenAlexSource


MOCK_SEARCH_RESPONSE = {
    "meta": {"count": 2},
    "results": [
        {
            "id": "https://openalex.org/W2741809807",
            "title": "Attention Is All You Need",
            "authorships": [
                {"author": {"display_name": "Ashish Vaswani"}},
                {"author": {"display_name": "Noam Shazeer"}},
            ],
            "abstract_inverted_index": {
                "The": [0],
                "dominant": [1],
                "attention": [2],
            },
            "publication_year": 2017,
            "primary_location": {
                "source": {"display_name": "NeurIPS"}
            },
            "cited_by_count": 120000,
            "doi": "https://doi.org/10.48550/arXiv.1706.03762",
            "open_access": {
                "is_oa": True,
                "oa_url": "https://arxiv.org/pdf/1706.03762",
            },
            "concepts": [
                {"display_name": "Computer Science"},
                {"display_name": "Artificial Intelligence"},
            ],
        },
        {
            "id": "https://openalex.org/W2963451630",
            "title": "BERT",
            "authorships": [
                {"author": {"display_name": "Jacob Devlin"}},
            ],
            "abstract_inverted_index": None,
            "publication_year": 2019,
            "primary_location": None,
            "cited_by_count": 80000,
            "doi": None,
            "open_access": {"is_oa": False},
            "concepts": [],
        },
    ],
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


class TestOpenAlexSource:
    """OpenAlexSource 测试套件"""

    def test_name(self):
        source = OpenAlexSource()
        assert source.name == "openalex"

    def test_base_api_url(self):
        source = OpenAlexSource()
        assert "openalex.org" in source.base_api_url

    def test_email_in_params(self):
        source = OpenAlexSource(email="test@example.com")
        assert source.email == "test@example.com"
        params = source._get_polite_params()
        assert params["mailto"] == "test@example.com"

    def test_no_email_params(self):
        source = OpenAlexSource()
        params = source._get_polite_params()
        assert params == {}

    async def test_search_success(self):
        mock_response = _make_mock_response(MOCK_SEARCH_RESPONSE)
        source = OpenAlexSource(email="test@example.com")
        source._client = _make_mock_client(mock_response)

        papers = await source.search("attention mechanism", max_results=10)

        assert len(papers) == 2
        assert papers[0].title == "Attention Is All You Need"
        assert papers[0].source == "openalex"
        assert papers[0].is_open_access is True

    async def test_search_empty_result(self):
        mock_response = _make_mock_response({"meta": {"count": 0}, "results": []})
        source = OpenAlexSource()
        source._client = _make_mock_client(mock_response)

        papers = await source.search("nonexistent")
        assert papers == []

    async def test_search_error_returns_empty(self):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Timeout"))
        mock_client.is_closed = False

        source = OpenAlexSource()
        source._client = mock_client

        papers = await source.search("test")
        assert papers == []

    async def test_get_paper_success(self):
        mock_response = _make_mock_response(MOCK_SEARCH_RESPONSE["results"][0])
        source = OpenAlexSource()
        source._client = _make_mock_client(mock_response)

        paper = await source.get_paper("W2741809807")
        assert paper is not None
        assert paper.title == "Attention Is All You Need"

    async def test_get_paper_not_found(self):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Not found"))
        mock_client.is_closed = False

        source = OpenAlexSource()
        source._client = mock_client

        paper = await source.get_paper("nonexistent")
        assert paper is None

    async def test_get_pdf_url(self):
        mock_response = _make_mock_response(MOCK_SEARCH_RESPONSE["results"][0])
        source = OpenAlexSource()
        source._client = _make_mock_client(mock_response)

        url = await source.get_pdf_url("W2741809807")
        assert url == "https://arxiv.org/pdf/1706.03762"

    async def test_health_check_success(self):
        mock_response = _make_mock_response({"meta": {"count": 250000000}, "results": []})
        source = OpenAlexSource()
        source._client = _make_mock_client(mock_response)

        result = await source.health_check()
        assert result["status"] == "ok"
        assert result["source"] == "openalex"

    async def test_health_check_error(self):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Service down"))
        mock_client.is_closed = False

        source = OpenAlexSource()
        source._client = mock_client

        result = await source.health_check()
        assert result["status"] == "error"

    def test_reconstruct_abstract(self):
        source = OpenAlexSource()
        inverted_index = {"Hello": [0], "world": [1], "test": [2]}
        result = source._reconstruct_abstract(inverted_index)
        assert result == "Hello world test"

    def test_reconstruct_abstract_none(self):
        source = OpenAlexSource()
        result = source._reconstruct_abstract(None)
        assert result is None

    def test_reconstruct_abstract_empty(self):
        source = OpenAlexSource()
        result = source._reconstruct_abstract({})
        assert result is None

    def test_parse_paper_doi_stripping(self):
        source = OpenAlexSource()
        data = {
            "id": "https://openalex.org/W123",
            "title": "Test",
            "authorships": [],
            "doi": "https://doi.org/10.1000/test",
            "open_access": {"is_oa": False},
        }
        paper = source._parse_paper(data)
        assert paper.doi == "10.1000/test"

    def test_parse_paper_no_doi(self):
        source = OpenAlexSource()
        data = {
            "id": "https://openalex.org/W123",
            "title": "Test",
            "authorships": [],
            "doi": None,
            "open_access": {"is_oa": False},
        }
        paper = source._parse_paper(data)
        assert paper.doi is None

    def test_parse_paper_year_parsing(self):
        source = OpenAlexSource()
        data = {
            "id": "https://openalex.org/W123",
            "title": "Test",
            "authorships": [],
            "publication_year": "2020",
            "open_access": {"is_oa": False},
        }
        paper = source._parse_paper(data)
        assert paper.year == 2020

    def test_parse_paper_no_id(self):
        source = OpenAlexSource()
        data = {
            "id": "",
            "title": "Test",
            "authorships": [],
            "open_access": {"is_oa": False},
        }
        paper = source._parse_paper(data)
        assert paper is None
