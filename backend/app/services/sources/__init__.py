"""
学术数据源适配器模块
"""

from app.services.sources.arxiv import ArxivSource
from app.services.sources.base import BaseSource, make_paper_uuid
from app.services.sources.crossref import CrossRefSource
from app.services.sources.openalex import OpenAlexSource
from app.services.sources.semantic_scholar import SemanticScholarSource

__all__ = [
    "BaseSource",
    "make_paper_uuid",
    "SemanticScholarSource",
    "OpenAlexSource",
    "CrossRefSource",
    "ArxivSource",
]
