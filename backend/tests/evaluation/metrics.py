"""
评测指标

提供学术检索系统常用的评测指标计算函数。
"""

import math
from typing import List, Set


def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Recall@K: 在前 K 个结果中命中相关文档的比例

    Args:
        retrieved: 检索到的文档 ID 列表（按排序）
        relevant: 相关文档 ID 集合
        k: 截断位置

    Returns:
        Recall@K 分数 (0-1)
    """
    if not relevant:
        return 0.0

    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / len(relevant)


def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Precision@K: 在前 K 个结果中相关文档的比例

    Args:
        retrieved: 检索到的文档 ID 列表（按排序）
        relevant: 相关文档 ID 集合
        k: 截断位置

    Returns:
        Precision@K 分数 (0-1)
    """
    if k <= 0:
        return 0.0

    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / k


def dcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    DCG@K (Discounted Cumulative Gain)

    Args:
        retrieved: 检索到的文档 ID 列表（按排序）
        relevant: 相关文档 ID 集合
        k: 截断位置

    Returns:
        DCG 分数
    """
    score = 0.0
    for i, doc_id in enumerate(retrieved[:k]):
        if doc_id in relevant:
            score += 1.0 / math.log2(i + 2)  # i+2 因为 log2(1) = 0
    return score


def ndcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    nDCG@K (Normalized Discounted Cumulative Gain)

    Args:
        retrieved: 检索到的文档 ID 列表（按排序）
        relevant: 相关文档 ID 集合
        k: 截断位置

    Returns:
        nDCG 分数 (0-1)
    """
    actual_dcg = dcg_at_k(retrieved, relevant, k)

    # 理想排序：所有相关文档排在最前面
    ideal_retrieved = list(relevant)[:k]
    ideal_dcg = dcg_at_k(ideal_retrieved, relevant, k)

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg


def constraint_satisfaction_rate(
    papers: List[dict],
    constraints: dict,
) -> float:
    """
    约束满足率: 检索结果满足给定约束条件的比例

    Args:
        papers: 论文列表（字典格式）
        constraints: 约束条件字典，支持:
            - min_citations: 最小引用数
            - date_from: 起始年份
            - date_to: 结束年份
            - open_access: 是否开放获取
            - required_fields: 必须包含的研究领域

    Returns:
        约束满足率 (0-1)
    """
    if not papers:
        return 0.0

    satisfied = 0
    for paper in papers:
        if _check_constraints(paper, constraints):
            satisfied += 1

    return satisfied / len(papers)


def _check_constraints(paper: dict, constraints: dict) -> bool:
    """检查单篇论文是否满足约束条件"""
    if "min_citations" in constraints:
        if paper.get("citation_count", 0) < constraints["min_citations"]:
            return False

    if "date_from" in constraints:
        year = paper.get("year")
        if year is None or year < constraints["date_from"]:
            return False

    if "date_to" in constraints:
        year = paper.get("year")
        if year is None or year > constraints["date_to"]:
            return False

    if "open_access" in constraints:
        if constraints["open_access"] and not paper.get("is_open_access", False):
            return False

    if "required_fields" in constraints:
        paper_fields = set(paper.get("fields_of_study", []))
        required = set(constraints["required_fields"])
        if not required.intersection(paper_fields):
            return False

    return True


def evidence_precision(
    claims: List[str],
    evidence_spans: List[dict],
) -> float:
    """
    Evidence Precision: 证据片段与声明的相关性

    Args:
        claims: 声明列表
        evidence_spans: 证据片段列表，每个包含 claim 和 verdict 字段

    Returns:
        证据精确率 (0-1)
    """
    if not evidence_spans:
        return 0.0

    relevant_count = 0
    for span in evidence_spans:
        # 证据的 verdict 不是 insufficient 且 claim 匹配
        if span.get("verdict") != "insufficient":
            for claim in claims:
                if _text_overlap(claim, span.get("claim", "")):
                    relevant_count += 1
                    break

    return relevant_count / len(evidence_spans)


def unsupported_claim_rate(
    claims: List[str],
    evidence_spans: List[dict],
) -> float:
    """
    Unsupported Claim Rate: 没有充分证据支持的声明比例

    Args:
        claims: 声明列表
        evidence_spans: 证据片段列表

    Returns:
        无支持声明比例 (0-1)，越低越好
    """
    if not claims:
        return 0.0

    unsupported = 0
    for claim in claims:
        has_support = False
        for span in evidence_spans:
            if (
                _text_overlap(claim, span.get("claim", ""))
                and span.get("verdict") == "supports"
                and span.get("confidence", 0) >= 0.5
            ):
                has_support = True
                break
        if not has_support:
            unsupported += 1

    return unsupported / len(claims)


def _text_overlap(text1: str, text2: str) -> bool:
    """检查两段文本是否有足够的重叠"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return False
    overlap = len(words1.intersection(words2))
    return overlap / min(len(words1), len(words2)) > 0.3
