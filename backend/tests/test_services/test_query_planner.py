"""
查询规划器测试
"""

import pytest

from app.schemas.query import DataSource
from app.services.search.query_planner import QueryPlanner


class TestQueryPlanner:
    """QueryPlanner 测试套件"""

    async def test_plan_returns_query_parse_result(self, mock_llm_gateway):
        """plan 应返回 QueryParseResult"""
        planner = QueryPlanner(llm_gateway=mock_llm_gateway)
        result = await planner.plan(
            query="transformer attention mechanism",
            sources=[DataSource.SEMANTIC_SCHOLAR],
        )
        assert result.original_query == "transformer attention mechanism"
        assert result.strategy is not None

    async def test_plan_generates_sub_queries_per_source(self, mock_llm_gateway):
        """应为每个数据源生成一个子查询"""
        planner = QueryPlanner(llm_gateway=mock_llm_gateway)
        sources = [DataSource.SEMANTIC_SCHOLAR, DataSource.OPENALEX, DataSource.CROSSREF]
        result = await planner.plan(
            query="deep learning",
            sources=sources,
        )
        assert len(result.sub_queries) == len(sources)

    async def test_plan_sub_queries_have_correct_source(self, mock_llm_gateway):
        """子查询应关联到正确的数据源"""
        planner = QueryPlanner(llm_gateway=mock_llm_gateway)
        sources = [DataSource.SEMANTIC_SCHOLAR, DataSource.OPENALEX]
        result = await planner.plan(query="NLP", sources=sources)

        result_sources = {sq.source for sq in result.sub_queries}
        expected_sources = set(sources)
        assert result_sources == expected_sources

    async def test_plan_sub_queries_have_rationale(self, mock_llm_gateway):
        """每个子查询应包含 rationale"""
        planner = QueryPlanner(llm_gateway=mock_llm_gateway)
        result = await planner.plan(
            query="test query",
            sources=[DataSource.SEMANTIC_SCHOLAR],
        )
        for sq in result.sub_queries:
            assert sq.rationale
            assert len(sq.rationale) > 0

    async def test_plan_extracts_keywords(self, mock_llm_gateway):
        """应提取关键词"""
        planner = QueryPlanner(llm_gateway=mock_llm_gateway)
        result = await planner.plan(
            query="attention mechanism in transformers",
            sources=[DataSource.SEMANTIC_SCHOLAR],
        )
        assert len(result.keywords) > 0

    async def test_plan_with_empty_sources(self, mock_llm_gateway):
        """空数据源列表应返回空子查询"""
        planner = QueryPlanner(llm_gateway=mock_llm_gateway)
        result = await planner.plan(
            query="test query",
            sources=[],
        )
        assert len(result.sub_queries) == 0

    async def test_plan_intent_is_set(self, mock_llm_gateway):
        """应设置查询意图"""
        planner = QueryPlanner(llm_gateway=mock_llm_gateway)
        result = await planner.plan(
            query="test query",
            sources=[DataSource.SEMANTIC_SCHOLAR],
        )
        assert result.intent is not None

    async def test_plan_without_llm_gateway(self):
        """没有 LLM 网关时应使用默认实现"""
        planner = QueryPlanner(llm_gateway=None)
        result = await planner.plan(
            query="test query",
            sources=[DataSource.SEMANTIC_SCHOLAR],
        )
        assert result.original_query == "test query"

    def test_build_prompt(self, mock_llm_gateway):
        """_build_prompt 应生成包含查询和数据源的 prompt"""
        planner = QueryPlanner(llm_gateway=mock_llm_gateway)
        prompt = planner._build_prompt(
            query="attention mechanism",
            sources=[DataSource.SEMANTIC_SCHOLAR, DataSource.OPENALEX],
        )
        assert "attention mechanism" in prompt
        assert "semantic_scholar" in prompt
        assert "openalex" in prompt

    @pytest.mark.parametrize(
        ("query", "canonical"),
        [
            (
                "the AlphaGeometry paper",
                "Solving olympiad geometry without human demonstrations",
            ),
            (
                "the gpt-2 paper",
                "Language Models are Unsupervised Multitask Learners",
            ),
            (
                "the cnn paper",
                "ImageNet classification with deep convolutional neural networks",
            ),
            (
                "the squad paper",
                "SQuAD: 100,000+ Questions for Machine Comprehension of Text",
            ),
        ],
    )
    def test_resolve_well_known_paper_aliases(self, query, canonical):
        assert QueryPlanner.resolve_paper_alias(query) == canonical

    @pytest.mark.parametrize(
        "query",
        [
            "BART by Lewis et al.",
            "the MS^2 DeYong2021 paper",
            "the paper about the Objaverse dataset",
            "SPIKE syntactic search paper",
            "the gpt-2 paper",
        ],
    )
    def test_confident_single_paper_lookup(self, query):
        assert QueryPlanner.is_confident_single_paper_lookup(query)

    def test_ambiguous_acronym_lookup_keeps_multiple_results(self):
        assert not QueryPlanner.is_confident_single_paper_lookup("the SPIKE paper")

    async def test_complex_query_extracts_multidimensional_constraints(self):
        planner = QueryPlanner()
        result = await planner.plan(
            query="查找 2020-2024 年 ACL 使用 Transformer 在 PaperFindingBench 上的论文",
            sources=[DataSource.SEMANTIC_SCHOLAR, DataSource.OPENALEX],
        )

        assert "ACL" in {venue.upper() for venue in result.entities["venues"]}
        assert any("paperfindingbench" == item.lower() for item in result.entities["datasets"])
        assert any("transformer" == item.lower() for item in result.entities["methods"])
        assert {(item.operator, item.value) for item in result.constraints if item.key == "year"} == {
            ("gte", 2020),
            ("lte", 2024),
        }

    async def test_venue_alternatives_use_or_constraint(self):
        planner = QueryPlanner()
        result = await planner.plan(
            query="2020-2024 ACL 或 EMNLP 的文献检索论文",
            sources=[DataSource.OPENALEX],
        )
        venue = next(item for item in result.constraints if item.key == "venue")
        assert venue.operator == "in"
        assert {item.upper() for item in venue.value} == {"ACL", "EMNLP"}
        assert "literature search" in result.expanded_queries[0].lower()

    async def test_refinement_queries_are_bounded_per_source(self):
        planner = QueryPlanner()
        sources = [DataSource.SEMANTIC_SCHOLAR, DataSource.OPENALEX]
        result = await planner.plan(
            query="大语言模型在交通流预测中的使用",
            sources=sources,
        )
        refinements = planner.build_refinement_subqueries(result, sources)

        assert len(refinements) <= len(sources)
        assert {item.source for item in refinements}.issubset(set(sources))
        translated = planner._translate_to_english("大语言模型在交通流预测中的使用")
        assert "large language model" in translated
        assert "traffic flow prediction" in translated

    async def test_source_queries_keep_all_high_information_facets(self):
        planner = QueryPlanner()
        result = await planner.plan(
            query=(
                "visual question answering papers using Earth Mover's Distance "
                "(EMD) as an evaluation metric"
            ),
            sources=[DataSource.CROSSREF, DataSource.OPENALEX, DataSource.ARXIV],
        )
        for sub_query in result.sub_queries:
            normalized = sub_query.query.lower()
            assert "visual" in normalized
            assert "question" in normalized
            assert "earth" in normalized
            assert "mover" in normalized
            assert "emd" in normalized

    async def test_semantic_scholar_query_removes_hyphens(self):
        planner = QueryPlanner()
        result = await planner.plan(
            query="papers about data-efficient pre-training methods",
            sources=[DataSource.SEMANTIC_SCHOLAR],
        )
        assert "-" not in result.sub_queries[0].query

    async def test_author_citation_query_is_exact_lookup(self):
        planner = QueryPlanner()
        result = await planner.plan(
            query="BART by Lewis et al.",
            sources=[DataSource.SEMANTIC_SCHOLAR, DataSource.ARXIV],
        )

        assert result.intent == "exact_lookup"
        assert all("et" not in item.query.lower().split() for item in result.sub_queries)
        assert all("al" not in item.query.lower().split() for item in result.sub_queries)

    async def test_named_paper_query_is_exact_lookup(self):
        planner = QueryPlanner()
        result = await planner.plan(
            query="the Multi-news fabri2019multinews paper",
            sources=[DataSource.ARXIV, DataSource.CROSSREF],
        )

        assert result.intent == "exact_lookup"
        assert all(item.query == "Multi news" for item in result.sub_queries)

    @pytest.mark.parametrize(
        "query",
        [
            "SPIKE syntactic search paper",
            "the paper about the Objaverse dataset",
        ],
    )
    async def test_short_named_paper_forms_are_exact_lookup(self, query):
        planner = QueryPlanner()
        result = await planner.plan(
            query=query,
            sources=[DataSource.SEMANTIC_SCHOLAR, DataSource.ARXIV],
        )

        assert result.intent == "exact_lookup"
