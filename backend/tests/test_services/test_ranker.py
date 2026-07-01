"""
排序器测试
"""

import uuid

import pytest

from app.schemas.paper import Paper
from app.services.search.ranker import Ranker


def _make_paper(
    title: str,
    abstract: str = "",
    citation_count: int = 0,
    year: int | None = 2024,
    is_open_access: bool = False,
) -> Paper:
    """辅助函数：快速创建 Paper 对象"""
    return Paper(
        id=str(uuid.uuid4()),
        title=title,
        authors=["Author A"],
        abstract=abstract,
        year=year,
        venue="Test Venue",
        citation_count=citation_count,
        doi=None,
        url="https://example.com",
        pdf_url=None,
        source="test",
        is_open_access=is_open_access,
    )


class TestRanker:
    """Ranker 测试套件"""

    async def test_rank_returns_sorted_list(self):
        """排序后应返回按相关性降序排列的列表"""
        ranker = Ranker()
        papers = [
            _make_paper("Unrelated Paper", abstract="Nothing to do with query"),
            _make_paper("Attention Mechanism", abstract="This paper discusses attention mechanism in detail"),
            _make_paper("Attention Is All You Need", abstract="attention mechanism for transformers"),
        ]
        result = await ranker.rank(papers, query="attention mechanism")
        assert len(result) == 3
        # 标题包含查询关键词的应排在前面
        assert "attention" in result[0].title.lower()

    async def test_rank_respects_limit(self):
        """应限制返回数量"""
        ranker = Ranker()
        papers = [_make_paper(f"Paper {i}", abstract="test query content") for i in range(20)]
        result = await ranker.rank(papers, query="test", limit=5)
        assert len(result) == 5

    async def test_rank_empty_list(self):
        """空列表应返回空列表"""
        ranker = Ranker()
        result = await ranker.rank([], query="test")
        assert result == []

    async def test_rank_sets_relevance_score(self):
        """排序后应设置 relevance_score"""
        ranker = Ranker()
        papers = [_make_paper("Test Paper", abstract="relevant to query")]
        result = await ranker.rank(papers, query="test")
        assert result[0].relevance_score is not None
        assert 0 <= result[0].relevance_score <= 1

    async def test_rank_attaches_traceable_quality_signals(self):
        ranker = Ranker()
        papers = [
            _make_paper("Paper A", citation_count=0, year=2025),
            _make_paper("Paper B", citation_count=10, year=2023),
            _make_paper("Paper C", citation_count=100, year=2020),
        ]
        result = await ranker.rank(papers, query="paper")
        assert all(paper.quality is not None for paper in result)
        most_cited = next(paper for paper in result if paper.citation_count == 100)
        assert most_cited.quality.citation_percentile > 0.8
        assert most_cited.quality.jcr_quartile is None
        assert most_cited.quality.cas_quartile is None
        assert most_cited.quality.partition_status == "unverified"

    async def test_rank_title_match_scores_higher(self):
        """标题匹配应比摘要匹配得分更高"""
        ranker = Ranker()
        papers = [
            _make_paper("Machine Learning", abstract="This paper is about deep learning and neural networks"),
            _make_paper("Deep Learning", abstract="This paper is about general topics"),
        ]
        result = await ranker.rank(papers, query="deep learning")
        assert result[0].title == "Deep Learning"

    async def test_rank_citations_break_ties(self):
        """相关性相同时，引用数高的应排在前面"""
        ranker = Ranker()
        papers = [
            _make_paper("Attention Paper A", citation_count=100),
            _make_paper("Attention Paper B", citation_count=10000),
        ]
        result = await ranker.rank(papers, query="attention")
        assert result[0].citation_count >= result[1].citation_count

    async def test_exact_citation_prefers_matching_author(self):
        ranker = Ranker(intent="exact_lookup")
        target = _make_paper(
            "BART: Denoising Sequence-to-Sequence Pre-training",
            citation_count=0,
            year=2019,
        )
        target.authors = ["Mike Lewis", "Yinhan Liu"]
        distractor = _make_paper(
            "A Modern BART Model",
            citation_count=10000,
            year=2025,
        )
        distractor.authors = ["Another Author"]

        result = await ranker.rank(
            [distractor, target],
            query="BART by Lewis et al.",
            limit=2,
        )

        assert result[0].title.startswith("BART:")

    async def test_named_paper_alias_prefers_exact_title(self):
        ranker = Ranker(intent="exact_lookup")
        target = _make_paper(
            "MS2: Multi-Document Summarization of Medical Studies",
            citation_count=0,
            year=2021,
        )
        distractor = _make_paper(
            "MS MARCO: Benchmarking Ranking Models",
            citation_count=10000,
            year=2025,
        )

        result = await ranker.rank(
            [distractor, target],
            query="the MS^2 DeYong2021 paper",
            limit=2,
        )

        assert result[0].title.startswith("MS2:")

    async def test_paper_about_alias_prefers_title_match(self):
        ranker = Ranker(intent="exact_lookup")
        target = _make_paper(
            "Objaverse: A Universe of Annotated 3D Objects",
            citation_count=0,
        )
        distractor = _make_paper(
            "A Survey of Large 3D Object Datasets",
            citation_count=10000,
        )

        result = await ranker.rank(
            [distractor, target],
            query="the paper about the Objaverse dataset",
            limit=2,
        )

        assert result[0].title.startswith("Objaverse:")

    async def test_rank_limit_larger_than_list(self):
        """limit 大于列表长度时应返回全部"""
        ranker = Ranker()
        papers = [_make_paper("Paper A"), _make_paper("Paper B")]
        result = await ranker.rank(papers, query="test", limit=100)
        assert len(result) == 2

    async def test_calculate_relevance_exact_title_match(self):
        """完全标题匹配应有高相关性"""
        ranker = Ranker()
        paper = _make_paper("attention mechanism", abstract="")
        score = await ranker._calculate_relevance(paper, "attention mechanism")
        assert score > 0.5

    async def test_calculate_relevance_no_match(self):
        """无匹配应有低相关性"""
        ranker = Ranker()
        paper = _make_paper("Quantum Physics", abstract="particle physics experiments")
        score = await ranker._calculate_relevance(paper, "deep learning neural networks")
        assert score < 0.1

    async def test_calculate_relevance_abstract_match(self):
        """摘要匹配应贡献相关性分数"""
        ranker = Ranker()
        paper = _make_paper("Some Paper", abstract="This paper studies deep learning methods")
        score = await ranker._calculate_relevance(paper, "deep learning")
        assert score > 0

    def test_filter_hard_constraints_supports_year_and_venue_alternatives(self):
        ranker = Ranker()
        papers = [
            _make_paper("ACL Paper", year=2024),
            _make_paper("Old ACL Paper", year=2019),
            _make_paper("EMNLP Paper", year=2022),
        ]
        papers[0].venue = "ACL 2024"
        papers[1].venue = "ACL 2019"
        papers[2].venue = "EMNLP 2022"
        constraints = [
            {"key": "year", "operator": "gte", "value": 2020},
            {"key": "venue", "operator": "in", "value": ["ACL", "EMNLP"]},
        ]
        result = ranker.filter_hard_constraints(papers, constraints)
        assert [paper.title for paper in result] == ["ACL Paper", "EMNLP Paper"]

    def test_no_constraints_do_not_add_free_score(self):
        assert Ranker()._calculate_constraint_score(_make_paper("Paper"), None) == 0.0
