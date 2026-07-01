"""
模拟数据源响应

为每个学术数据源提供标准的 Mock 响应数据。
"""


SEMANTIC_SCHOLAR_SEARCH_RESPONSE = {
    "total": 2,
    "data": [
        {
            "paperId": "204e3073870fae3d05bcbc2f6a8e263d9b72e776",
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
    ],
}

OPENALEX_SEARCH_RESPONSE = {
    "meta": {"count": 1, "per_page": 25, "page": 1},
    "results": [
        {
            "id": "https://openalex.org/W2741809807",
            "title": "Attention Is All You Need",
            "authorships": [
                {"author": {"display_name": "Ashish Vaswani"}},
            ],
            "abstract_inverted_index": {
                "The": [0],
                "dominant": [1],
                "sequence": [2],
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
        },
    ],
}

CROSSREF_SEARCH_RESPONSE = {
    "status": "ok",
    "message": {
        "total-results": 1,
        "items": [
            {
                "DOI": "10.48550/arXiv.1706.03762",
                "title": ["Attention Is All You Need"],
                "author": [
                    {"given": "Ashish", "family": "Vaswani"},
                ],
                "abstract": "The dominant sequence transduction models...",
                "published-print": {"date-parts": [[2017]]},
                "container-title": ["NeurIPS"],
                "is-referenced-by-count": 120000,
                "URL": "https://doi.org/10.48550/arXiv.1706.03762",
                "link": [
                    {
                        "content-type": "application/pdf",
                        "URL": "https://arxiv.org/pdf/1706.03762",
                    }
                ],
            },
        ],
    },
}

# 空响应
EMPTY_SEMANTIC_SCHOLAR = {"total": 0, "data": []}
EMPTY_OPENALEX = {"meta": {"count": 0}, "results": []}
EMPTY_CROSSREF = {"status": "ok", "message": {"total-results": 0, "items": []}}

# 错误响应
RATE_LIMIT_RESPONSE = {"message": "Too Many Requests"}
SERVER_ERROR_RESPONSE = {"message": "Internal Server Error"}
