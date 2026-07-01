"""
证据提取器

从论文全文中提取约束证据。
支持三级提取策略：
1. 元数据级约束（直接判断）
2. 摘要级约束（从摘要提取）
3. 全文级约束（从全文提取）

对于无法通过规则判断的约束，调用 LLM 进行语义理解。
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.schemas.query import Constraint

logger = logging.getLogger(__name__)

# 已知数据集名称（常见的学术数据集）
_KNOWN_DATASETS: set[str] = {
    "imagenet",
    "mnist",
    "cifar-10",
    "cifar-100",
    "cifar10",
    "cifar100",
    "coco",
    "ms coco",
    "ms-coco",
    "pascal voc",
    "voc",
    "squad",
    "squad 2.0",
    "glue",
    "superglue",
    "common crawl",
    "wmt",
    "librispeech",
    "cityscapes",
    "ade20k",
    "kinetics",
    "ucf101",
    "celeba",
    "lsun",
    "openimages",
    "open images",
    "imagenet-1k",
    "imagenet-21k",
    "yelp",
    "amazon reviews",
    "movielens",
    "flickr",
    "reddit",
    "wikipedia",
    "bookcorpus",
    "the pile",
    "red pajama",
    "dolly",
    "alpaca",
    "natural questions",
    "triviaqa",
    "hellaswag",
    "mmlu",
    "arc",
    "winogrande",
    "gsm8k",
    "math",
    "humaneval",
    "mbpp",
    "imagenet-a",
    "imagenet-r",
    "imagenetv2",
    "object365",
    "openwebtext",
    "c4",
    "pg-19",
    "gutenberg",
    "arxiv",
    "semantic scholar",
    "pubmed",
    "scierc",
    "chemprot",
    "ag news",
    "sst-2",
    "sst",
    "cola",
    "qnli",
    "qqp",
    "mnli",
    "rte",
    "wnli",
    "mrpc",
    "stsb",
    "boolq",
    "cb",
    "copa",
    "multirc",
    "record",
    "wic",
    "wsc",
}

# 实验相关关键词
_EXPERIMENT_KEYWORDS: set[str] = {
    "comparison",
    "baseline",
    "benchmark",
    "outperform",
    "compared with",
    "compared to",
    "state-of-the-art",
    "sota",
    "ablation",
    "evaluation",
    "results show",
    "experimental results",
    "our method",
    "our approach",
    "our model",
    "we achieve",
    "we obtain",
    "we demonstrate",
    "we show",
    "significantly",
    "improvement",
    "accuracy",
    "f1 score",
    "precision",
    "recall",
    "bleu",
    "rouge",
    "perplexity",
}

# 实验节标题模式
_EXPERIMENT_SECTION_PATTERNS: list[str] = [
    "experiment",
    "evaluation",
    "results",
    "ablation",
    "comparison",
    "performance",
    "benchmark",
]

# 数据集描述模式
_DATASET_DESCRIPTION_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"(?:we\s+)?(?:use|employ|evaluate|train|test|experiment)\s+(?:on|with|using)\s+(?:the\s+)?([A-Z][A-Za-z0-9\-\s]+?)(?:\s+dataset|\s+benchmark|\s+corpus|\s+data)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:dataset|benchmark|corpus)(?:\s+of|\s+consisting|\s+containing|\s+with)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:trained|evaluated|tested)\s+on\s+(?:the\s+)?([A-Z][A-Za-z0-9\-\s]+?)(?:\s+dataset)?",
        re.IGNORECASE,
    ),
]


@dataclass
class EvidenceSpan:
    """证据片段"""

    section_name: str
    paragraph_index: int
    quote_text: str  # 原文引用
    start_char: int = 0  # 在原文中的位置
    end_char: int = 0
    confidence: float = 0.0


@dataclass
class VerifiedEvidence:
    """经过验证的证据"""

    constraint_key: str
    verdict: str  # "satisfied" | "violated" | "unknown"
    source_level: str  # "metadata" | "abstract" | "fulltext"
    evidence_spans: list[EvidenceSpan] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""


class EvidenceExtractor:
    """
    证据提取器

    从论文全文中提取与约束条件相关的证据。
    采用三级提取策略：元数据 -> 摘要 -> 全文。
    对于规则无法判断的约束，调用 LLM 进行语义理解。
    """

    def __init__(self, llm_gateway=None):
        """
        初始化提取器。

        Args:
            llm_gateway: LLM 网关实例
        """
        self.llm_gateway = llm_gateway

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    async def extract(
        self,
        document: dict,
        constraints: list[dict],
        max_evidence_per_constraint: int = 5,
    ) -> list[VerifiedEvidence]:
        """
        从文档中提取所有约束的证据。

        Args:
            document: 文档信息字典，应包含：
                - title: str
                - abstract: str
                - full_text: str
                - sections: list[dict] (heading, level, text, paragraph_index)
                - metadata: dict (author, doi, year, ...)
                - venue: str (可选)
                - year: int (可选)
                - is_open_access: bool (可选)
                - pdf_url: str (可选)
            constraints: 约束列表，每个约束为 dict 或 Constraint 对象
            max_evidence_per_constraint: 每个约束最多提取的证据数

        Returns:
            VerifiedEvidence 列表
        """
        results: list[VerifiedEvidence] = []

        for constraint_dict in constraints:
            # 兼容 dict 和 Constraint 对象
            if isinstance(constraint_dict, dict):
                constraint = Constraint(**constraint_dict)
            else:
                constraint = constraint_dict

            evidence = await self._extract_for_constraint(
                document, constraint, max_evidence_per_constraint
            )
            results.append(evidence)

        return results

    async def extract_from_abstract(
        self,
        abstract: str,
        constraints: list[dict],
        paper_metadata: Optional[dict] = None,
    ) -> list[VerifiedEvidence]:
        """
        仅从摘要中提取证据（用于摘要级预筛选）。

        Args:
            abstract: 摘要文本
            constraints: 约束列表
            paper_metadata: 论文元数据（可选）

        Returns:
            VerifiedEvidence 列表
        """
        document = {
            "title": "",
            "abstract": abstract,
            "full_text": abstract,
            "sections": [],
            "metadata": paper_metadata or {},
        }
        return await self.extract(document, constraints, max_evidence_per_constraint=3)

    # ------------------------------------------------------------------
    # 内部方法：单个约束的证据提取
    # ------------------------------------------------------------------

    async def _extract_for_constraint(
        self,
        document: dict,
        constraint: Constraint,
        max_evidence: int,
    ) -> VerifiedEvidence:
        """
        为单个约束提取证据。
        按优先级尝试：元数据 -> 摘要 -> 全文 -> LLM。
        """
        key = constraint.key.lower()

        # 1. 元数据级约束
        metadata_result = self._check_metadata_constraint(document, constraint)
        if metadata_result and metadata_result.confidence > 0.5:
            return metadata_result

        # 2. 摘要级约束
        abstract_result = self._check_abstract_constraint(
            document, constraint, max_evidence
        )
        if abstract_result and abstract_result.confidence > 0.5:
            return abstract_result

        # 3. 全文级约束
        fulltext_result = self._check_fulltext_constraint(
            document, constraint, max_evidence
        )
        if fulltext_result and fulltext_result.confidence > 0.5:
            return fulltext_result

        # 4. LLM 辅助提取
        if self.llm_gateway:
            llm_result = await self._extract_with_llm(
                document, constraint, max_evidence
            )
            if llm_result and llm_result.confidence > 0.3:
                return llm_result

        # 返回最佳结果，或 unknown
        best = fulltext_result or abstract_result or metadata_result
        if best:
            return best

        return VerifiedEvidence(
            constraint_key=constraint.key,
            verdict="unknown",
            source_level="",
            evidence_spans=[],
            confidence=0.0,
            reasoning="No evidence found for this constraint.",
        )

    # ------------------------------------------------------------------
    # 元数据级约束
    # ------------------------------------------------------------------

    def _check_metadata_constraint(
        self, document: dict, constraint: Constraint
    ) -> Optional[VerifiedEvidence]:
        """
        检查元数据级约束（时间、文献类型、OA 状态等）。
        """
        key = constraint.key.lower()
        op = constraint.operator.lower()
        value = constraint.value

        # 时间约束
        if key in ("year", "publication_year", "pub_year", "date"):
            return self._check_year_constraint(document, constraint)

        # 文献类型 / 会议 / 期刊
        if key in ("venue", "journal", "conference", "source", "publication"):
            return self._check_venue_constraint(document, constraint)

        # OA 状态
        if key in ("open_access", "oa", "is_open_access"):
            return self._check_oa_constraint(document, constraint)

        # 作者
        if key in ("author", "authors"):
            return self._check_author_constraint(document, constraint)

        # 引用数
        if key in ("citations", "citation_count", "min_citations"):
            return self._check_citation_constraint(document, constraint)

        # DOI
        if key in ("doi",):
            doi = document.get("metadata", {}).get("doi", "")
            if doi:
                return VerifiedEvidence(
                    constraint_key=constraint.key,
                    verdict="satisfied",
                    source_level="metadata",
                    evidence_spans=[
                        EvidenceSpan(
                            section_name="metadata",
                            paragraph_index=0,
                            quote_text=f"DOI: {doi}",
                            confidence=0.95,
                        )
                    ],
                    confidence=0.95,
                    reasoning=f"DOI found in metadata: {doi}",
                )

        return None

    def _check_year_constraint(
        self, document: dict, constraint: Constraint
    ) -> Optional[VerifiedEvidence]:
        """检查年份约束。"""
        year = document.get("year") or document.get("metadata", {}).get("year")
        if year is None:
            return None

        try:
            year = int(year)
        except (ValueError, TypeError):
            return None

        op = constraint.operator.lower()
        target = constraint.value

        try:
            target_year = int(target)
        except (ValueError, TypeError):
            return None

        verdict = "unknown"
        if op in ("gte", ">="):
            verdict = "satisfied" if year >= target_year else "violated"
        elif op in ("lte", "<="):
            verdict = "satisfied" if year <= target_year else "violated"
        elif op in ("eq", "==", "="):
            verdict = "satisfied" if year == target_year else "violated"
        elif op == "gt":
            verdict = "satisfied" if year > target_year else "violated"
        elif op == "lt":
            verdict = "satisfied" if year < target_year else "violated"
        elif op in ("in", "between"):
            if isinstance(target, list) and len(target) == 2:
                verdict = (
                    "satisfied"
                    if target[0] <= year <= target[1]
                    else "violated"
                )

        return VerifiedEvidence(
            constraint_key=constraint.key,
            verdict=verdict,
            source_level="metadata",
            evidence_spans=[
                EvidenceSpan(
                    section_name="metadata",
                    paragraph_index=0,
                    quote_text=f"Publication year: {year}",
                    confidence=0.95,
                )
            ],
            confidence=0.95,
            reasoning=f"Publication year {year} vs constraint {op} {target}",
        )

    def _check_venue_constraint(
        self, document: dict, constraint: Constraint
    ) -> Optional[VerifiedEvidence]:
        """检查会议/期刊约束。"""
        venue = document.get("venue", "") or document.get("metadata", {}).get(
            "venue", ""
        )
        if not venue:
            return None

        op = constraint.operator.lower()
        target = str(constraint.value).lower()

        if op in ("eq", "contains", "==", "="):
            satisfied = target in venue.lower() or venue.lower() in target
        elif op == "in":
            if isinstance(constraint.value, list):
                satisfied = any(
                    target_item.lower() in venue.lower()
                    for target_item in constraint.value
                )
            else:
                satisfied = False
        else:
            satisfied = False

        return VerifiedEvidence(
            constraint_key=constraint.key,
            verdict="satisfied" if satisfied else "violated",
            source_level="metadata",
            evidence_spans=[
                EvidenceSpan(
                    section_name="metadata",
                    paragraph_index=0,
                    quote_text=f"Venue: {venue}",
                    confidence=0.9,
                )
            ],
            confidence=0.9,
            reasoning=f"Venue '{venue}' vs constraint {op} '{target}'",
        )

    def _check_oa_constraint(
        self, document: dict, constraint: Constraint
    ) -> Optional[VerifiedEvidence]:
        """检查开放获取约束。"""
        is_oa = document.get("is_open_access", None)
        pdf_url = document.get("pdf_url", "")

        # 如果有 pdf_url，通常意味着是 OA
        if is_oa is None and pdf_url:
            is_oa = True

        if is_oa is None:
            return None

        target = constraint.value
        if isinstance(target, str):
            target = target.lower() in ("true", "1", "yes")

        satisfied = bool(is_oa) == bool(target)

        return VerifiedEvidence(
            constraint_key=constraint.key,
            verdict="satisfied" if satisfied else "violated",
            source_level="metadata",
            evidence_spans=[
                EvidenceSpan(
                    section_name="metadata",
                    paragraph_index=0,
                    quote_text=f"Open Access: {is_oa}",
                    confidence=0.85,
                )
            ],
            confidence=0.85,
            reasoning=f"OA status: {is_oa}, constraint requires: {target}",
        )

    def _check_author_constraint(
        self, document: dict, constraint: Constraint
    ) -> Optional[VerifiedEvidence]:
        """检查作者约束。"""
        authors = document.get("authors", [])
        if not authors:
            authors_raw = document.get("metadata", {}).get("author", "")
            if authors_raw:
                authors = [
                    a.strip() for a in re.split(r"[;,]", authors_raw) if a.strip()
                ]

        if not authors:
            return None

        target = str(constraint.value).lower()
        op = constraint.operator.lower()

        matched = [
            a for a in authors if target in a.lower() or a.lower() in target
        ]

        if op in ("eq", "contains", "==", "="):
            satisfied = len(matched) > 0
        else:
            satisfied = len(matched) > 0

        return VerifiedEvidence(
            constraint_key=constraint.key,
            verdict="satisfied" if satisfied else "violated",
            source_level="metadata",
            evidence_spans=[
                EvidenceSpan(
                    section_name="metadata",
                    paragraph_index=0,
                    quote_text=f"Authors: {', '.join(authors[:5])}",
                    confidence=0.85,
                )
            ],
            confidence=0.85,
            reasoning=f"Author match for '{target}': {len(matched)} found",
        )

    def _check_citation_constraint(
        self, document: dict, constraint: Constraint
    ) -> Optional[VerifiedEvidence]:
        """检查引用数约束。"""
        citations = document.get("citation_count")
        if citations is None:
            return None

        try:
            citations = int(citations)
        except (ValueError, TypeError):
            return None

        op = constraint.operator.lower()
        target = constraint.value

        try:
            target_val = int(target)
        except (ValueError, TypeError):
            return None

        verdict = "unknown"
        if op in ("gte", ">="):
            verdict = "satisfied" if citations >= target_val else "violated"
        elif op in ("lte", "<="):
            verdict = "satisfied" if citations <= target_val else "violated"
        elif op in ("gt", ">"):
            verdict = "satisfied" if citations > target_val else "violated"

        return VerifiedEvidence(
            constraint_key=constraint.key,
            verdict=verdict,
            source_level="metadata",
            evidence_spans=[
                EvidenceSpan(
                    section_name="metadata",
                    paragraph_index=0,
                    quote_text=f"Citation count: {citations}",
                    confidence=0.9,
                )
            ],
            confidence=0.9,
            reasoning=f"Citation count {citations} vs {op} {target_val}",
        )

    # ------------------------------------------------------------------
    # 摘要级约束
    # ------------------------------------------------------------------

    def _check_abstract_constraint(
        self,
        document: dict,
        constraint: Constraint,
        max_evidence: int,
    ) -> Optional[VerifiedEvidence]:
        """
        从摘要中提取约束证据。
        适用于数据集名称、方法名称、实验类型等。
        """
        abstract = document.get("abstract", "")
        if not abstract:
            return None

        key = constraint.key.lower()
        value = str(constraint.value).lower()

        # 数据集名称约束
        if key in ("dataset", "datasets", "data", "benchmark"):
            return self._check_dataset_in_text(
                abstract, constraint, "abstract", max_evidence
            )

        # 方法名称约束
        if key in ("method", "methods", "approach", "technique", "model"):
            return self._check_method_in_text(
                abstract, constraint, "abstract", max_evidence
            )

        # 实验类型约束
        if key in ("experiment", "experiment_type", "has_comparison", "has_baseline"):
            return self._check_experiment_type_in_text(
                abstract, constraint, "abstract"
            )

        # 通用关键词搜索
        return self._search_keywords_in_text(
            abstract, constraint, "abstract", max_evidence
        )

    def _check_dataset_in_text(
        self,
        text: str,
        constraint: Constraint,
        source_level: str,
        max_evidence: int,
    ) -> Optional[VerifiedEvidence]:
        """在文本中搜索数据集名称。"""
        target = str(constraint.value).lower()
        op = constraint.operator.lower()

        # 检查是否包含已知数据集名
        found_datasets: list[str] = []
        spans: list[EvidenceSpan] = []

        for dataset in _KNOWN_DATASETS:
            if dataset in text.lower():
                found_datasets.append(dataset)
                # 找到原文引用
                idx = text.lower().find(dataset)
                start = max(0, idx - 50)
                end = min(len(text), idx + len(dataset) + 50)
                quote = text[start:end].strip()
                spans.append(
                    EvidenceSpan(
                        section_name=source_level,
                        paragraph_index=0,
                        quote_text=f"...{quote}...",
                        start_char=start,
                        end_char=end,
                        confidence=0.8,
                    )
                )

        # 也搜索目标值本身
        if target and target not in [d.lower() for d in found_datasets]:
            if target in text.lower():
                idx = text.lower().find(target)
                start = max(0, idx - 50)
                end = min(len(text), idx + len(target) + 50)
                quote = text[start:end].strip()
                spans.append(
                    EvidenceSpan(
                        section_name=source_level,
                        paragraph_index=0,
                        quote_text=f"...{quote}...",
                        start_char=start,
                        end_char=end,
                        confidence=0.75,
                    )
                )
                found_datasets.append(target)

        if not found_datasets:
            return None

        # 判断是否满足约束
        if op in ("eq", "contains", "==", "="):
            satisfied = target in [d.lower() for d in found_datasets]
        elif op in ("in",):
            if isinstance(constraint.value, list):
                satisfied = any(
                    v.lower() in [d.lower() for d in found_datasets]
                    for v in constraint.value
                )
            else:
                satisfied = False
        else:
            satisfied = len(found_datasets) > 0

        return VerifiedEvidence(
            constraint_key=constraint.key,
            verdict="satisfied" if satisfied else "violated",
            source_level=source_level,
            evidence_spans=spans[:max_evidence],
            confidence=0.7,
            reasoning=f"Datasets found in {source_level}: {found_datasets}",
        )

    def _check_method_in_text(
        self,
        text: str,
        constraint: Constraint,
        source_level: str,
        max_evidence: int,
    ) -> Optional[VerifiedEvidence]:
        """在文本中搜索方法名称。"""
        target = str(constraint.value).lower()
        op = constraint.operator.lower()

        if target not in text.lower():
            return None

        # 找到原文引用
        spans: list[EvidenceSpan] = []
        search_text = text.lower()
        pos = 0
        while True:
            idx = search_text.find(target, pos)
            if idx == -1:
                break
            start = max(0, idx - 60)
            end = min(len(text), idx + len(target) + 60)
            quote = text[start:end].strip()
            spans.append(
                EvidenceSpan(
                    section_name=source_level,
                    paragraph_index=0,
                    quote_text=f"...{quote}...",
                    start_char=start,
                    end_char=end,
                    confidence=0.75,
                )
            )
            pos = idx + len(target)
            if len(spans) >= max_evidence:
                break

        return VerifiedEvidence(
            constraint_key=constraint.key,
            verdict="satisfied",
            source_level=source_level,
            evidence_spans=spans,
            confidence=0.7,
            reasoning=f"Method '{target}' found in {source_level}",
        )

    def _check_experiment_type_in_text(
        self,
        text: str,
        constraint: Constraint,
        source_level: str,
    ) -> Optional[VerifiedEvidence]:
        """检查文本中是否包含实验相关关键词。"""
        text_lower = text.lower()
        found_keywords: list[str] = []
        spans: list[EvidenceSpan] = []

        for kw in _EXPERIMENT_KEYWORDS:
            if kw in text_lower:
                found_keywords.append(kw)
                idx = text_lower.find(kw)
                start = max(0, idx - 40)
                end = min(len(text), idx + len(kw) + 40)
                quote = text[start:end].strip()
                spans.append(
                    EvidenceSpan(
                        section_name=source_level,
                        paragraph_index=0,
                        quote_text=f"...{quote}...",
                        start_char=start,
                        end_char=end,
                        confidence=0.7,
                    )
                )

        if not found_keywords:
            return None

        # 如果约束要求特定实验类型
        target = str(constraint.value).lower()
        if target in ("comparison", "has_baseline", "has_comparison"):
            has_comparison = any(
                kw in found_keywords
                for kw in ["comparison", "baseline", "compared with", "compared to"]
            )
            verdict = "satisfied" if has_comparison else "violated"
        else:
            verdict = "satisfied"

        return VerifiedEvidence(
            constraint_key=constraint.key,
            verdict=verdict,
            source_level=source_level,
            evidence_spans=spans[:3],
            confidence=0.65,
            reasoning=f"Experiment keywords found: {found_keywords[:5]}",
        )

    def _search_keywords_in_text(
        self,
        text: str,
        constraint: Constraint,
        source_level: str,
        max_evidence: int,
    ) -> Optional[VerifiedEvidence]:
        """通用关键词搜索。"""
        target = str(constraint.value).lower()
        if not target or target not in text.lower():
            return None

        spans: list[EvidenceSpan] = []
        search_text = text.lower()
        pos = 0
        while True:
            idx = search_text.find(target, pos)
            if idx == -1:
                break
            start = max(0, idx - 60)
            end = min(len(text), idx + len(target) + 60)
            quote = text[start:end].strip()
            spans.append(
                EvidenceSpan(
                    section_name=source_level,
                    paragraph_index=0,
                    quote_text=f"...{quote}...",
                    start_char=start,
                    end_char=end,
                    confidence=0.6,
                )
            )
            pos = idx + len(target)
            if len(spans) >= max_evidence:
                break

        return VerifiedEvidence(
            constraint_key=constraint.key,
            verdict="satisfied",
            source_level=source_level,
            evidence_spans=spans,
            confidence=0.6,
            reasoning=f"Keyword '{target}' found in {source_level}",
        )

    # ------------------------------------------------------------------
    # 全文级约束
    # ------------------------------------------------------------------

    def _check_fulltext_constraint(
        self,
        document: dict,
        constraint: Constraint,
        max_evidence: int,
    ) -> Optional[VerifiedEvidence]:
        """
        从全文中提取约束证据。
        优先在实验相关章节中搜索。
        """
        key = constraint.key.lower()
        sections = document.get("sections", [])
        full_text = document.get("full_text", "")

        if not full_text and not sections:
            return None

        # 对于实验相关约束，优先搜索实验章节
        if key in (
            "experiment",
            "experiment_type",
            "has_comparison",
            "has_baseline",
            "dataset",
            "datasets",
            "benchmark",
            "method",
            "methods",
        ):
            # 先在实验章节中搜索
            for section in sections:
                heading = section.get("heading", "").lower()
                if any(p in heading for p in _EXPERIMENT_SECTION_PATTERNS):
                    section_text = section.get("text", "")
                    result = self._search_in_section(
                        section_text,
                        constraint,
                        section.get("heading", "Experiments"),
                        section.get("paragraph_index", 0),
                        max_evidence,
                    )
                    if result and result.confidence > 0.5:
                        return result

        # 在全文中搜索
        if full_text:
            return self._search_keywords_in_text(
                full_text, constraint, "fulltext", max_evidence
            )

        return None

    def _search_in_section(
        self,
        text: str,
        constraint: Constraint,
        section_name: str,
        paragraph_index: int,
        max_evidence: int,
    ) -> Optional[VerifiedEvidence]:
        """在单个章节中搜索约束证据。"""
        key = constraint.key.lower()
        value = str(constraint.value).lower()

        if not text:
            return None

        # 数据集搜索
        if key in ("dataset", "datasets", "data", "benchmark"):
            return self._check_dataset_in_text(
                text, constraint, section_name, max_evidence
            )

        # 方法搜索
        if key in ("method", "methods", "approach", "technique", "model"):
            return self._check_method_in_text(
                text, constraint, section_name, max_evidence
            )

        # 通用搜索
        if value and value in text.lower():
            spans: list[EvidenceSpan] = []
            search_text = text.lower()
            pos = 0
            while True:
                idx = search_text.find(value, pos)
                if idx == -1:
                    break
                start = max(0, idx - 60)
                end = min(len(text), idx + len(value) + 60)
                quote = text[start:end].strip()
                spans.append(
                    EvidenceSpan(
                        section_name=section_name,
                        paragraph_index=paragraph_index,
                        quote_text=f"...{quote}...",
                        start_char=start,
                        end_char=end,
                        confidence=0.65,
                    )
                )
                pos = idx + len(value)
                if len(spans) >= max_evidence:
                    break

            if spans:
                return VerifiedEvidence(
                    constraint_key=constraint.key,
                    verdict="satisfied",
                    source_level="fulltext",
                    evidence_spans=spans,
                    confidence=0.65,
                    reasoning=f"Found '{value}' in {section_name}",
                )

        return None

    # ------------------------------------------------------------------
    # LLM 辅助提取
    # ------------------------------------------------------------------

    async def _extract_with_llm(
        self,
        document: dict,
        constraint: Constraint,
        max_evidence: int,
    ) -> Optional[VerifiedEvidence]:
        """
        使用 LLM 进行语义级别的证据提取。
        当规则方法无法确定时调用。
        """
        if not self.llm_gateway:
            return None

        # 准备文本（截断以适应 LLM 上下文窗口）
        abstract = document.get("abstract", "")
        full_text = document.get("full_text", "")

        # 优先使用摘要，如果太短则加上全文前部分
        text_for_llm = abstract
        if len(text_for_llm) < 500 and full_text:
            text_for_llm = full_text[:6000]

        if not text_for_llm:
            return None

        prompt = self._build_extraction_prompt(constraint, text_for_llm, max_evidence)

        try:
            response = await self.llm_gateway.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an academic evidence extractor. "
                            "Extract evidence from the paper text that relates to the given constraint. "
                            "Always respond in valid JSON format."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
            )

            return self._parse_llm_response(constraint, response)

        except Exception as e:
            logger.warning(f"LLM evidence extraction failed: {e}")
            return None

    def _build_extraction_prompt(
        self, constraint: Constraint, text: str, max_evidence: int
    ) -> str:
        """构建 LLM 证据提取 prompt。"""
        return f"""Analyze the following academic paper text and extract evidence related to this constraint:

CONSTRAINT:
- Key: {constraint.key}
- Operator: {constraint.operator}
- Value: {constraint.value}
- Description: {constraint.description or 'N/A'}

PAPER TEXT:
{text[:6000]}

Please extract up to {max_evidence} evidence passages that are relevant to the constraint.

For each evidence passage:
1. Quote the EXACT original text (do not paraphrase)
2. Identify which section it comes from
3. Assess confidence (0.0-1.0)

Response format (JSON):
{{
    "verdict": "satisfied|violated|unknown",
    "confidence": 0.0,
    "reasoning": "Brief explanation",
    "evidence": [
        {{
            "quote": "exact text from the paper",
            "section": "section name",
            "confidence": 0.0
        }}
    ]
}}
"""

    def _parse_llm_response(
        self, constraint: Constraint, response: str
    ) -> Optional[VerifiedEvidence]:
        """解析 LLM 响应。"""
        try:
            # 尝试从响应中提取 JSON
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            # 解析证据列表
            spans: list[EvidenceSpan] = []
            for item in data.get("evidence", []):
                spans.append(
                    EvidenceSpan(
                        section_name=item.get("section", "unknown"),
                        paragraph_index=0,
                        quote_text=item.get("quote", ""),
                        confidence=float(item.get("confidence", 0.5)),
                    )
                )

            # 映射 verdict
            raw_verdict = data.get("verdict", "unknown").lower()
            verdict_map = {
                "supports": "satisfied",
                "satisfied": "satisfied",
                "contradicts": "violated",
                "violated": "violated",
                "neutral": "unknown",
                "insufficient": "unknown",
                "unknown": "unknown",
            }
            verdict = verdict_map.get(raw_verdict, "unknown")

            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning", "")

            return VerifiedEvidence(
                constraint_key=constraint.key,
                verdict=verdict,
                source_level="fulltext",
                evidence_spans=spans,
                confidence=confidence,
                reasoning=reasoning,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return None

    # ------------------------------------------------------------------
    # 工具方法（兼容旧接口）
    # ------------------------------------------------------------------

    def _split_into_sections(self, text: str) -> list[dict]:
        """
        将论文分割为章节（兼容旧接口）。
        """
        sections: list[dict] = []
        current_section: dict = {"title": "Unknown", "content": ""}

        lines = text.split("\n")
        for line in lines:
            if line.strip() and line.strip().isupper() and len(line.strip()) < 50:
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {"title": line.strip(), "content": ""}
            else:
                current_section["content"] += line + "\n"

        if current_section["content"]:
            sections.append(current_section)

        return sections

    def _extract_key_sentences(
        self, text: str, query: str, max_sentences: int = 3
    ) -> list[str]:
        """
        提取关键句子（兼容旧接口）。
        """
        query_words = set(query.lower().split())
        sentences = text.split(".")

        scored_sentences: list[tuple[int, str]] = []
        for sentence in sentences:
            if not sentence.strip():
                continue
            sentence_words = set(sentence.lower().split())
            matches = len(query_words.intersection(sentence_words))
            if matches > 0:
                scored_sentences.append((matches, sentence.strip()))

        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored_sentences[:max_sentences]]
