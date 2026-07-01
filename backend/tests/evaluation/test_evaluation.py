"""
评测测试框架

对核心指标和评测流程进行单元测试。
"""

import json
import os
import pytest

from tests.evaluation.metrics import (
    recall_at_k,
    precision_at_k,
    ndcg_at_k,
    constraint_satisfaction_rate,
    evidence_precision,
    unsupported_claim_rate,
)


# ---------------------------------------------------------------------------
# 加载测试数据
# ---------------------------------------------------------------------------

_FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")


def _load_json(filename: str):
    path = os.path.join(_FIXTURES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestRecallAtK:
    """Recall@K 指标测试"""

    def test_perfect_recall(self):
        """所有相关文档都在前 K 个结果中"""
        retrieved = ["a", "b", "c", "d", "e"]
        relevant = {"a", "b", "c"}
        assert recall_at_k(retrieved, relevant, k=3) == 1.0

    def test_zero_recall(self):
        """没有相关文档命中"""
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=3) == 0.0

    def test_partial_recall(self):
        """部分命中"""
        retrieved = ["a", "x", "b", "y"]
        relevant = {"a", "b", "c"}
        assert recall_at_k(retrieved, relevant, k=3) == pytest.approx(2 / 3)

    def test_k_larger_than_list(self):
        """K 大于列表长度"""
        retrieved = ["a", "b"]
        relevant = {"a", "b", "c"}
        assert recall_at_k(retrieved, relevant, k=10) == pytest.approx(2 / 3)

    def test_empty_relevant(self):
        """空相关集合应返回 0"""
        assert recall_at_k(["a", "b"], set(), k=2) == 0.0

    def test_empty_retrieved(self):
        """空检索结果应返回 0"""
        assert recall_at_k([], {"a"}, k=5) == 0.0


class TestPrecisionAtK:
    """Precision@K 指标测试"""

    def test_perfect_precision(self):
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b", "c"}
        assert precision_at_k(retrieved, relevant, k=3) == 1.0

    def test_zero_precision(self):
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b"}
        assert precision_at_k(retrieved, relevant, k=3) == 0.0

    def test_partial_precision(self):
        retrieved = ["a", "x", "b"]
        relevant = {"a", "b"}
        assert precision_at_k(retrieved, relevant, k=3) == pytest.approx(2 / 3)

    def test_k_zero(self):
        assert precision_at_k(["a"], {"a"}, k=0) == 0.0


class TestNDCGAtK:
    """nDCG@K 指标测试"""

    def test_perfect_ranking(self):
        """理想排序的 nDCG 应为 1.0"""
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b", "c"}
        assert ndcg_at_k(retrieved, relevant, k=3) == pytest.approx(1.0)

    def test_worst_ranking(self):
        """相关文档排在最后，nDCG 应较低"""
        retrieved = ["x", "y", "a"]
        relevant = {"a"}
        # DCG = 1/log2(4) = 0.5
        # ideal DCG = 1/log2(2) = 1.0
        assert ndcg_at_k(retrieved, relevant, k=3) == pytest.approx(0.5)

    def test_empty_relevant(self):
        """空相关集合应返回 0"""
        assert ndcg_at_k(["a", "b"], set(), k=2) == 0.0

    def test_single_relevant_at_top(self):
        """单个相关文档在最前面"""
        retrieved = ["a", "x", "y"]
        relevant = {"a"}
        assert ndcg_at_k(retrieved, relevant, k=3) == pytest.approx(1.0)


class TestConstraintSatisfactionRate:
    """约束满足率指标测试"""

    def test_all_satisfied(self):
        """所有论文满足约束"""
        papers = [
            {"citation_count": 100, "year": 2023, "is_open_access": True},
            {"citation_count": 200, "year": 2022, "is_open_access": True},
        ]
        constraints = {"min_citations": 50, "date_from": 2020}
        assert constraint_satisfaction_rate(papers, constraints) == 1.0

    def test_none_satisfied(self):
        """无论文满足约束"""
        papers = [
            {"citation_count": 10, "year": 2015},
            {"citation_count": 5, "year": 2010},
        ]
        constraints = {"min_citations": 100, "date_from": 2020}
        assert constraint_satisfaction_rate(papers, constraints) == 0.0

    def test_partial_satisfaction(self):
        """部分满足"""
        papers = [
            {"citation_count": 100, "year": 2023},
            {"citation_count": 10, "year": 2023},
        ]
        constraints = {"min_citations": 50}
        assert constraint_satisfaction_rate(papers, constraints) == 0.5

    def test_open_access_constraint(self):
        """开放获取约束"""
        papers = [
            {"is_open_access": True},
            {"is_open_access": False},
        ]
        constraints = {"open_access": True}
        assert constraint_satisfaction_rate(papers, constraints) == 0.5

    def test_date_range_constraint(self):
        """日期范围约束"""
        papers = [
            {"year": 2022},
            {"year": 2018},
            {"year": 2023},
        ]
        constraints = {"date_from": 2020, "date_to": 2024}
        assert constraint_satisfaction_rate(papers, constraints) == pytest.approx(2 / 3)

    def test_empty_papers(self):
        """空论文列表应返回 0"""
        assert constraint_satisfaction_rate([], {"min_citations": 10}) == 0.0

    def test_fields_constraint(self):
        """研究领域约束"""
        papers = [
            {"fields_of_study": ["Computer Science", "Mathematics"]},
            {"fields_of_study": ["Biology"]},
        ]
        constraints = {"required_fields": ["Computer Science"]}
        assert constraint_satisfaction_rate(papers, constraints) == 0.5


class TestEvidencePrecision:
    """Evidence Precision 指标测试"""

    def test_perfect_evidence(self):
        """所有证据都相关"""
        claims = ["The model improves accuracy"]
        spans = [
            {"claim": "The model improves accuracy", "verdict": "supports"},
            {"claim": "The model improves accuracy", "verdict": "contradicts"},
        ]
        assert evidence_precision(claims, spans) == 1.0

    def test_insufficient_evidence(self):
        """insufficient verdict 不应计入"""
        claims = ["claim one"]
        spans = [
            {"claim": "claim one", "verdict": "insufficient"},
        ]
        assert evidence_precision(claims, spans) == 0.0

    def test_empty_spans(self):
        assert evidence_precision(["claim"], []) == 0.0


class TestUnsupportedClaimRate:
    """Unsupported Claim Rate 指标测试"""

    def test_all_supported(self):
        """所有声明都有支持证据"""
        claims = ["claim A"]
        spans = [
            {"claim": "claim A", "verdict": "supports", "confidence": 0.9},
        ]
        assert unsupported_claim_rate(claims, spans) == 0.0

    def test_all_unsupported(self):
        """所有声明都没有支持证据"""
        claims = ["claim A", "claim B"]
        spans = [
            {"claim": "claim A", "verdict": "contradicts", "confidence": 0.8},
        ]
        assert unsupported_claim_rate(claims, spans) == 1.0

    def test_empty_claims(self):
        assert unsupported_claim_rate([], [{"verdict": "supports"}]) == 0.0

    def test_low_confidence_support(self):
        """低置信度的支持不应算作有支持"""
        claims = ["claim A"]
        spans = [
            {"claim": "claim A", "verdict": "supports", "confidence": 0.3},
        ]
        assert unsupported_claim_rate(claims, spans) == 1.0


class TestWithFixtureData:
    """使用 fixture 数据的集成测试"""

    def test_sample_queries_loaded(self):
        """应能加载 sample_queries.json"""
        queries = _load_json("sample_queries.json")
        assert len(queries) == 30

    def test_sample_papers_loaded(self):
        """应能加载 sample_papers.json"""
        papers = _load_json("sample_papers.json")
        assert len(papers) == 50

    def test_queries_have_levels(self):
        """查询样本应覆盖 Level 1-5"""
        queries = _load_json("sample_queries.json")
        levels = {q["level"] for q in queries}
        assert levels == {1, 2, 3, 4, 5}

    def test_papers_have_diverse_sources(self):
        """论文样本应来自多个数据源"""
        papers = _load_json("sample_papers.json")
        sources = {p["source"] for p in papers}
        assert len(sources) >= 2

    def test_constraint_satisfaction_with_fixture_data(self):
        """使用 fixture 数据测试约束满足率"""
        papers = _load_json("sample_papers.json")
        constraints = {"min_citations": 1000, "date_from": 2020}
        rate = constraint_satisfaction_rate(papers, constraints)
        assert 0 <= rate <= 1
