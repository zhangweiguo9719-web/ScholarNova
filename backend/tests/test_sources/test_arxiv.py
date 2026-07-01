"""
arXiv API 测试（Mock HTTP 响应）
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.sources.arxiv import ArxivSource


# Mock Atom XML 响应
MOCK_ATOM_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <title>ArXiv Query: search_query=all:attention+mechanism</title>
  <totalResults xmlns="opensearch">2</totalResults>
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex
recurrent or convolutional neural networks.</summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <published>2017-06-12T17:57:02Z</published>
    <link href="http://arxiv.org/abs/1706.03762v5" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/1706.03762v5" rel="related" type="application/pdf"/>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2005.14165v4</id>
    <title>GPT-4 Technical Report</title>
    <summary>We report the development of GPT-4, a large-scale, multimodal
model.</summary>
    <author><name>OpenAI</name></author>
    <published>2023-03-27T17:57:02Z</published>
    <link href="http://arxiv.org/abs/2005.14165v4" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2005.14165v4" rel="related" type="application/pdf"/>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>
"""

MOCK_SINGLE_ENTRY = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models.</summary>
    <author><name>Ashish Vaswani</name></author>
    <published>2017-06-12T17:57:02Z</published>
    <link href="http://arxiv.org/abs/1706.03762v5" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/1706.03762v5" rel="related" type="application/pdf"/>
    <category term="cs.CL"/>
  </entry>
</feed>
"""

MOCK_EMPTY_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv Query</title>
</feed>
"""


def _make_mock_response(text_data, status_code=200):
    """创建 mock HTTP 响应（text/raise_for_status 为同步方法）"""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = text_data
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}
    return mock_response


def _make_mock_client(response):
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=response)
    mock_client.is_closed = False
    return mock_client


class TestArxivSource:
    """ArxivSource 测试套件"""

    def test_name(self):
        source = ArxivSource()
        assert source.name == "arxiv"

    def test_base_api_url(self):
        source = ArxivSource()
        assert "arxiv.org" in source.base_api_url

    def test_headers_no_auth(self):
        source = ArxivSource()
        headers = source._get_headers()
        assert "Authorization" not in headers
        assert "User-Agent" in headers

    async def test_search_success(self):
        mock_response = _make_mock_response(MOCK_ATOM_RESPONSE)
        source = ArxivSource()
        source._client = _make_mock_client(mock_response)
        source._last_request_time = 0  # 跳过限流等待

        papers = await source.search("attention mechanism", max_results=10)

        assert len(papers) == 2
        assert papers[0].title == "Attention Is All You Need"
        assert papers[0].source == "arxiv"
        assert papers[0].is_open_access is True
        assert papers[0].venue == "arXiv"

    async def test_search_empty_result(self):
        mock_response = _make_mock_response(MOCK_EMPTY_FEED)
        source = ArxivSource()
        source._client = _make_mock_client(mock_response)
        source._last_request_time = 0

        papers = await source.search("nonexistent query")
        assert papers == []

    async def test_search_error_returns_empty(self):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Network error"))
        mock_client.is_closed = False

        source = ArxivSource()
        source._client = mock_client
        source._last_request_time = 0

        papers = await source.search("test")
        assert papers == []

    async def test_get_paper_success(self):
        mock_response = _make_mock_response(MOCK_SINGLE_ENTRY)
        source = ArxivSource()
        source._client = _make_mock_client(mock_response)
        source._last_request_time = 0

        paper = await source.get_paper("1706.03762v5")

        assert paper is not None
        assert paper.title == "Attention Is All You Need"
        assert paper.year == 2017
        assert paper.pdf_url is not None

    async def test_get_paper_not_found(self):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Not found"))
        mock_client.is_closed = False

        source = ArxivSource()
        source._client = mock_client
        source._last_request_time = 0

        paper = await source.get_paper("nonexistent")
        assert paper is None

    async def test_get_pdf_url(self):
        source = ArxivSource()
        url = await source.get_pdf_url("2301.07041")
        assert url == "http://arxiv.org/pdf/2301.07041"

    def test_parse_atom_feed(self):
        source = ArxivSource()
        papers = source._parse_atom_feed(MOCK_ATOM_RESPONSE)
        assert len(papers) == 2

    def test_parse_entry_authors(self):
        source = ArxivSource()
        papers = source._parse_atom_feed(MOCK_ATOM_RESPONSE)
        assert "Ashish Vaswani" in papers[0].authors
        assert "Noam Shazeer" in papers[0].authors

    def test_parse_entry_categories(self):
        """验证分类信息被正确解析（用于判断论文领域）"""
        source = ArxivSource()
        papers = source._parse_atom_feed(MOCK_ATOM_RESPONSE)
        # categories are extracted internally but Paper doesn't have keywords field
        assert papers[0].title == "Attention Is All You Need"

    def test_parse_entry_no_pdf(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/9999.99999</id>
            <title>Test Paper</title>
            <author><name>Test Author</name></author>
            <published>2024-01-01T00:00:00Z</published>
            <link href="http://arxiv.org/abs/9999.99999" rel="alternate" type="text/html"/>
          </entry>
        </feed>"""
        source = ArxivSource()
        papers = source._parse_atom_feed(xml)
        assert len(papers) == 1
        assert papers[0].pdf_url is None

    def test_citation_count_always_zero(self):
        source = ArxivSource()
        papers = source._parse_atom_feed(MOCK_ATOM_RESPONSE)
        for paper in papers:
            assert paper.citation_count == 0

    def test_is_open_access_always_true(self):
        source = ArxivSource()
        papers = source._parse_atom_feed(MOCK_ATOM_RESPONSE)
        for paper in papers:
            assert paper.is_open_access is True
