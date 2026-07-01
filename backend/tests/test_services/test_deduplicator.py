"""
去重器测试
"""

import uuid

import pytest

from app.schemas.paper import Paper
from app.services.search.deduplicator import Deduplicator


def _make_paper(title: str, doi: str | None = None, source: str = "test") -> Paper:
    """辅助函数：快速创建 Paper 对象"""
    return Paper(
        id=uuid.uuid4(),
        title=title,
        authors=["Author A"],
        abstract="Abstract text",
        year=2024,
        venue="Test Venue",
        citation_count=10,
        doi=doi,
        url="https://example.com",
        pdf_url=None,
        source=source,
    )


class TestDeduplicator:
    """Deduplicator 测试套件"""

    def test_empty_list(self):
        """空列表应返回空列表"""
        dedup = Deduplicator()
        result = dedup.deduplicate([])
        assert result == []

    def test_no_duplicates(self):
        """无重复论文应全部保留"""
        dedup = Deduplicator()
        papers = [
            _make_paper("Paper A", doi="10.1000/a"),
            _make_paper("Paper B", doi="10.1000/b"),
            _make_paper("Paper C", doi="10.1000/c"),
        ]
        result = dedup.deduplicate(papers)
        assert len(result) == 3

    def test_dedup_by_doi(self):
        """相同 DOI 的论文应去重"""
        dedup = Deduplicator()
        papers = [
            _make_paper("Paper A", doi="10.1000/same"),
            _make_paper("Paper A Updated", doi="10.1000/same"),
        ]
        result = dedup.deduplicate(papers)
        assert len(result) == 1
        assert result[0].title == "Paper A"

    def test_dedup_by_title(self):
        """相同标题（标准化后）的论文应去重"""
        dedup = Deduplicator()
        papers = [
            _make_paper("Attention Is All You Need", doi="10.1000/a"),
            _make_paper("Attention is all you need", doi="10.1000/b"),
        ]
        result = dedup.deduplicate(papers)
        assert len(result) == 1

    def test_dedup_title_case_insensitive(self):
        """标题去重应不区分大小写"""
        dedup = Deduplicator()
        papers = [
            _make_paper("Deep Learning"),
            _make_paper("deep learning"),
            _make_paper("DEEP LEARNING"),
        ]
        result = dedup.deduplicate(papers)
        assert len(result) == 1

    def test_dedup_title_whitespace_normalization(self):
        """标题去重应标准化多余空格"""
        dedup = Deduplicator()
        papers = [
            _make_paper("Deep   Learning  for  NLP"),
            _make_paper("Deep Learning for NLP"),
        ]
        result = dedup.deduplicate(papers)
        assert len(result) == 1

    def test_dedup_title_punctuation_removal(self):
        """标题去重应移除标点符号"""
        dedup = Deduplicator()
        papers = [
            _make_paper("Deep Learning: A Survey"),
            _make_paper("Deep Learning A Survey"),
        ]
        result = dedup.deduplicate(papers)
        assert len(result) == 1

    def test_different_papers_kept(self):
        """不同论文应保留"""
        dedup = Deduplicator()
        papers = [
            _make_paper("Paper A", doi="10.1000/a"),
            _make_paper("Paper B", doi="10.1000/b"),
            _make_paper("Completely Different Title", doi="10.1000/c"),
        ]
        result = dedup.deduplicate(papers)
        assert len(result) == 3

    def test_dedup_preserves_first_occurrence(self):
        """去重应保留第一次出现的论文"""
        dedup = Deduplicator()
        paper1 = _make_paper("Same Title", doi="10.1000/a", source="source_a")
        paper2 = _make_paper("Same Title", doi="10.1000/b", source="source_b")
        papers = [paper1, paper2]
        result = dedup.deduplicate(papers)
        assert len(result) == 1
        assert result[0].source == "source_a"

    def test_dedup_mixed_doi_and_title(self):
        """DOI 去重优先于标题去重"""
        dedup = Deduplicator()
        papers = [
            _make_paper("Paper A", doi="10.1000/same"),
            _make_paper("Paper B", doi="10.1000/same"),
            _make_paper("Paper A", doi="10.1000/different"),
        ]
        result = dedup.deduplicate(papers)
        # 第1和第2篇 DOI 相同，去重第2篇；第3篇标题相同但 DOI 不同，标题去重
        assert len(result) == 1

    def test_dedup_no_doi_papers(self):
        """没有 DOI 的论文应通过标题去重"""
        dedup = Deduplicator()
        papers = [
            _make_paper("Same Title", doi=None),
            _make_paper("Same Title", doi=None),
            _make_paper("Different Title", doi=None),
        ]
        result = dedup.deduplicate(papers)
        assert len(result) == 2

    def test_similarity_threshold(self):
        """应使用配置的相似度阈值"""
        dedup = Deduplicator(similarity_threshold=0.9)
        assert dedup.similarity_threshold == 0.9

    def test_normalize_title(self):
        """标题标准化应正确处理"""
        dedup = Deduplicator()
        assert dedup._normalize_title("  Hello,  World!  ") == "hello world"

    def test_calculate_similarity_identical(self):
        """相同文本的相似度应为 1.0"""
        dedup = Deduplicator()
        sim = dedup._calculate_similarity("hello world", "hello world")
        assert sim == 1.0

    def test_calculate_similarity_different(self):
        """完全不同文本的相似度应接近 0"""
        dedup = Deduplicator()
        sim = dedup._calculate_similarity("apple banana", "car dog")
        assert sim == 0.0

    def test_calculate_similarity_partial(self):
        """部分重叠文本应有中间相似度"""
        dedup = Deduplicator()
        sim = dedup._calculate_similarity("hello world foo", "hello world bar")
        assert 0 < sim < 1

    def test_calculate_similarity_empty(self):
        """空文本的相似度应为 0"""
        dedup = Deduplicator()
        sim = dedup._calculate_similarity("", "")
        assert sim == 0.0
