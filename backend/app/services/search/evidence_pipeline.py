"""
证据流程管道

将 PDF 解析、证据提取、证据验证串联为完整的端到端流程。
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.schemas.query import Constraint

logger = logging.getLogger(__name__)


@dataclass
class PaperWithEvidence:
    """带证据的论文"""

    paper_id: str
    title: str
    abstract: str
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    pdf_url: Optional[str] = None
    is_open_access: bool = False
    citation_count: int = 0
    evidence: list[dict] = field(default_factory=list)
    overall_verdict: str = "unknown"  # "satisfied" | "violated" | "unknown"
    overall_confidence: float = 0.0
    evidence_quality: float = 0.0
    has_fulltext: bool = False


class EvidencePipeline:
    """
    证据流程管道

    完整的证据提取和验证流程：
    1. 先用摘要级验证所有论文
    2. 为 Top K 获取全文
    3. 用全文级验证增强证据
    4. 返回带证据的论文列表
    """

    def __init__(
        self,
        llm_gateway=None,
        pdf_fetcher=None,
        pdf_parser=None,
    ):
        """
        初始化证据管道。

        Args:
            llm_gateway: LLM 网关实例
            pdf_fetcher: PDF 获取器实例
            pdf_parser: PDF 解析器实例
        """
        self.llm_gateway = llm_gateway
        self.pdf_fetcher = pdf_fetcher
        self.pdf_parser = pdf_parser

        # 延迟初始化，避免循环导入
        self._extractor = None
        self._verifier = None

    @property
    def extractor(self):
        """延迟初始化证据提取器。"""
        if self._extractor is None:
            from app.services.evidence.extractor import EvidenceExtractor

            self._extractor = EvidenceExtractor(llm_gateway=self.llm_gateway)
        return self._extractor

    @property
    def verifier(self):
        """延迟初始化证据验证器。"""
        if self._verifier is None:
            from app.services.evidence.verifier import EvidenceVerifier

            self._verifier = EvidenceVerifier(llm_gateway=self.llm_gateway)
        return self._verifier

    def _get_parser(self):
        """获取 PDF 解析器实例。"""
        if self.pdf_parser:
            return self.pdf_parser
        try:
            from app.services.pdf.parser import PDFParser

            return PDFParser()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    async def enhance_with_evidence(
        self,
        papers: list[dict],
        constraints: list[dict],
        max_fulltext: int = 10,
    ) -> list[dict]:
        """
        为论文列表增强证据。

        Args:
            papers: 论文列表，每个元素包含：
                - paper_id: str
                - title: str
                - abstract: str
                - year: int (可选)
                - venue: str (可选)
                - doi: str (可选)
                - pdf_url: str (可选)
                - is_open_access: bool (可选)
                - citation_count: int (可选)
            constraints: 约束列表
            max_fulltext: 最多获取全文的论文数

        Returns:
            带证据的论文列表
        """
        if not papers:
            return []

        if not constraints:
            # 没有约束时直接返回原始论文
            return [
                {
                    **paper,
                    "evidence": [],
                    "overall_verdict": "unknown",
                    "overall_confidence": 0.0,
                }
                for paper in papers
            ]

        logger.info(
            f"Enhancing {len(papers)} papers with evidence for "
            f"{len(constraints)} constraints"
        )

        # 步骤1: 摘要级证据提取（所有论文）
        abstract_results = await self._extract_abstract_evidence(
            papers, constraints
        )

        # 步骤2: 选择 Top K 论文获取全文
        top_k_papers = self._select_top_k_for_fulltext(
            papers, abstract_results, max_fulltext
        )

        # 步骤3: 获取全文并解析
        fulltext_results = await self._extract_fulltext_evidence(
            top_k_papers, constraints
        )

        # 步骤4: 合并结果
        final_results = self._merge_results(
            papers, abstract_results, fulltext_results
        )

        # 步骤5: 验证证据质量
        verified_results = await self._verify_evidence(final_results)

        logger.info(
            f"Evidence enhancement complete: "
            f"{sum(1 for r in verified_results if r.get('has_fulltext'))} with fulltext, "
            f"{sum(1 for r in verified_results if r.get('overall_verdict') != 'unknown')} with verdict"
        )

        return verified_results

    async def enhance_single_paper(
        self,
        paper: dict,
        constraints: list[dict],
        force_fulltext: bool = False,
    ) -> dict:
        """
        为单篇论文增强证据。

        Args:
            paper: 论文信息
            constraints: 约束列表
            force_fulltext: 是否强制获取全文

        Returns:
            带证据的论文信息
        """
        results = await self.enhance_with_evidence(
            [paper], constraints, max_fulltext=1 if force_fulltext else 0
        )
        return results[0] if results else paper

    # ------------------------------------------------------------------
    # 内部方法：摘要级证据
    # ------------------------------------------------------------------

    async def _extract_abstract_evidence(
        self,
        papers: list[dict],
        constraints: list[dict],
    ) -> dict[str, list[dict]]:
        """
        从摘要中提取证据。

        Returns:
            {paper_id: [evidence_list]}
        """
        results: dict[str, list[dict]] = {}

        for paper in papers:
            paper_id = paper.get("paper_id", "")
            abstract = paper.get("abstract", "")

            if not abstract:
                results[paper_id] = []
                continue

            try:
                evidence_list = await self.extractor.extract_from_abstract(
                    abstract=abstract,
                    constraints=constraints,
                    paper_metadata={
                        "year": paper.get("year"),
                        "venue": paper.get("venue"),
                        "doi": paper.get("doi"),
                        "is_open_access": paper.get("is_open_access", False),
                        "author": paper.get("authors", []),
                        "citation_count": paper.get("citation_count", 0),
                    },
                )

                # 转换为字典格式
                results[paper_id] = [
                    {
                        "constraint_key": e.constraint_key,
                        "verdict": e.verdict,
                        "source_level": e.source_level,
                        "evidence_spans": [
                            {
                                "section_name": s.section_name,
                                "paragraph_index": s.paragraph_index,
                                "quote_text": s.quote_text,
                                "start_char": s.start_char,
                                "end_char": s.end_char,
                                "confidence": s.confidence,
                            }
                            for s in e.evidence_spans
                        ],
                        "confidence": e.confidence,
                        "reasoning": e.reasoning,
                    }
                    for e in evidence_list
                ]

            except Exception as e:
                logger.warning(
                    f"Abstract evidence extraction failed for {paper_id}: {e}"
                )
                results[paper_id] = []

        return results

    # ------------------------------------------------------------------
    # 内部方法：选择 Top K
    # ------------------------------------------------------------------

    def _select_top_k_for_fulltext(
        self,
        papers: list[dict],
        abstract_results: dict[str, list[dict]],
        max_fulltext: int,
    ) -> list[dict]:
        """
        选择最值得获取全文的 Top K 论文。

        选择策略：
        1. 有 PDF URL 且是 OA 的论文优先
        2. 摘要级证据置信度较高的论文优先
        3. 按引用数和年份综合排序
        """
        if max_fulltext <= 0:
            return []

        scored_papers: list[tuple[float, dict]] = []

        for paper in papers:
            paper_id = paper.get("paper_id", "")
            score = 0.0

            # 有 PDF URL 加分
            if paper.get("pdf_url"):
                score += 3.0

            # OA 加分
            if paper.get("is_open_access"):
                score += 2.0

            # 有 DOI 加分（可以通过 Unpaywall 获取）
            if paper.get("doi"):
                score += 1.0

            # 摘要级证据质量
            evidence_list = abstract_results.get(paper_id, [])
            if evidence_list:
                avg_confidence = sum(
                    e.get("confidence", 0) for e in evidence_list
                ) / len(evidence_list)
                score += avg_confidence * 2.0

                # 有 "satisfied" 证据的论文更有价值
                satisfied_count = sum(
                    1 for e in evidence_list if e.get("verdict") == "satisfied"
                )
                score += satisfied_count * 0.5

            # 引用数（对数缩放）
            citations = paper.get("citation_count", 0)
            if citations > 0:
                import math

                score += math.log10(citations + 1) * 0.5

            # 年份（越新越好）
            year = paper.get("year")
            if year:
                score += min((year - 2015) * 0.1, 1.0)

            scored_papers.append((score, paper))

        # 按分数降序排序
        scored_papers.sort(key=lambda x: x[0], reverse=True)

        # 返回 Top K
        selected = [p for _, p in scored_papers[:max_fulltext]]
        logger.info(
            f"Selected {len(selected)} papers for fulltext extraction "
            f"(scores: {[f'{s:.1f}' for s, _ in scored_papers[:max_fulltext]]})"
        )

        return selected

    # ------------------------------------------------------------------
    # 内部方法：全文级证据
    # ------------------------------------------------------------------

    async def _extract_fulltext_evidence(
        self,
        papers: list[dict],
        constraints: list[dict],
    ) -> dict[str, dict]:
        """
        获取全文并提取证据。

        Returns:
            {paper_id: {"full_text": str, "sections": list, "evidence": list}}
        """
        if not papers:
            return {}

        results: dict[str, dict] = {}

        # 获取 PDF
        if not self.pdf_fetcher:
            logger.warning("PDF fetcher not available, skipping fulltext extraction")
            return results

        from app.services.pdf.fetcher import PDFFetcher

        fetch_results = await self.pdf_fetcher.fetch_batch(
            papers,
            max_concurrent=3,
        )

        # 解析 PDF 并提取证据
        for paper, fetch_result in zip(papers, fetch_results):
            paper_id = paper.get("paper_id", "")

            if not fetch_result.success or not fetch_result.pdf_path:
                logger.debug(
                    f"PDF fetch failed for {paper_id}: {fetch_result.error}"
                )
                continue

            try:
                # 解析 PDF
                parser = self._get_parser()
                if not parser:
                    continue

                parsed_doc = await parser.parse(fetch_result.pdf_path)
                if not parsed_doc:
                    continue

                # 构建文档信息
                document = {
                    "title": parsed_doc.title or paper.get("title", ""),
                    "abstract": parsed_doc.abstract or paper.get("abstract", ""),
                    "full_text": parsed_doc.full_text,
                    "sections": [
                        {
                            "heading": s.heading,
                            "level": s.level,
                            "text": s.text,
                            "paragraph_index": s.paragraph_index,
                        }
                        for s in parsed_doc.sections
                    ],
                    "metadata": {
                        **parsed_doc.metadata,
                        "year": paper.get("year"),
                        "venue": paper.get("venue"),
                        "doi": paper.get("doi"),
                        "is_open_access": paper.get("is_open_access", False),
                        "citation_count": paper.get("citation_count", 0),
                    },
                    "year": paper.get("year"),
                    "venue": paper.get("venue"),
                    "is_open_access": paper.get("is_open_access", False),
                    "citation_count": paper.get("citation_count", 0),
                    "pdf_url": paper.get("pdf_url", ""),
                }

                # 提取证据
                evidence_list = await self.extractor.extract(
                    document=document,
                    constraints=constraints,
                    max_evidence_per_constraint=5,
                )

                results[paper_id] = {
                    "full_text": parsed_doc.full_text,
                    "sections": [
                        {
                            "heading": s.heading,
                            "level": s.level,
                            "text": s.text,
                            "paragraph_index": s.paragraph_index,
                        }
                        for s in parsed_doc.sections
                    ],
                    "evidence": [
                        {
                            "constraint_key": e.constraint_key,
                            "verdict": e.verdict,
                            "source_level": e.source_level,
                            "evidence_spans": [
                                {
                                    "section_name": s.section_name,
                                    "paragraph_index": s.paragraph_index,
                                    "quote_text": s.quote_text,
                                    "start_char": s.start_char,
                                    "end_char": s.end_char,
                                    "confidence": s.confidence,
                                }
                                for s in e.evidence_spans
                            ],
                            "confidence": e.confidence,
                            "reasoning": e.reasoning,
                        }
                        for e in evidence_list
                    ],
                    "references": parsed_doc.references,
                    "tables": parsed_doc.tables,
                    "figures": parsed_doc.figures,
                }

                logger.info(
                    f"Fulltext evidence extracted for {paper_id}: "
                    f"{len(evidence_list)} constraints, "
                    f"{len(parsed_doc.sections)} sections"
                )

            except Exception as e:
                logger.warning(
                    f"Fulltext evidence extraction failed for {paper_id}: {e}"
                )

        return results

    # ------------------------------------------------------------------
    # 内部方法：合并结果
    # ------------------------------------------------------------------

    def _merge_results(
        self,
        papers: list[dict],
        abstract_results: dict[str, list[dict]],
        fulltext_results: dict[str, dict],
    ) -> list[dict]:
        """
        合并摘要级和全文级证据。
        全文级证据优先级更高，替换同一约束的摘要级证据。
        """
        merged: list[dict] = []

        for paper in papers:
            paper_id = paper.get("paper_id", "")
            abstract_evidence = abstract_results.get(paper_id, [])
            fulltext_data = fulltext_results.get(paper_id)

            if fulltext_data:
                # 全文级证据
                fulltext_evidence = fulltext_data.get("evidence", [])

                # 合并：全文级覆盖摘要级
                evidence_map: dict[str, dict] = {}

                # 先加入摘要级
                for e in abstract_evidence:
                    key = e.get("constraint_key", "")
                    evidence_map[key] = e

                # 全文级覆盖
                for e in fulltext_evidence:
                    key = e.get("constraint_key", "")
                    evidence_map[key] = e

                merged_evidence = list(evidence_map.values())
                has_fulltext = True
            else:
                merged_evidence = abstract_evidence
                has_fulltext = False

            # 计算整体 verdict 和 confidence
            overall_verdict, overall_confidence = self._compute_overall(
                merged_evidence
            )

            merged.append(
                {
                    **paper,
                    "evidence": merged_evidence,
                    "overall_verdict": overall_verdict,
                    "overall_confidence": overall_confidence,
                    "has_fulltext": has_fulltext,
                }
            )

        return merged

    def _compute_overall(
        self, evidence_list: list[dict]
    ) -> tuple[str, float]:
        """
        计算整体 verdict 和 confidence。

        策略：
        - 如果所有约束都 satisfied -> "satisfied"
        - 如果有任一约束 violated -> "violated"
        - 否则 -> "unknown"
        """
        if not evidence_list:
            return "unknown", 0.0

        verdicts = [e.get("verdict", "unknown") for e in evidence_list]
        confidences = [e.get("confidence", 0.0) for e in evidence_list]

        satisfied_count = verdicts.count("satisfied")
        violated_count = verdicts.count("violated")
        total = len(verdicts)

        if violated_count > 0:
            overall_verdict = "violated"
        elif satisfied_count == total:
            overall_verdict = "satisfied"
        elif satisfied_count > 0:
            overall_verdict = "partially_satisfied"
        else:
            overall_verdict = "unknown"

        overall_confidence = sum(confidences) / total if total > 0 else 0.0

        return overall_verdict, round(overall_confidence, 2)

    # ------------------------------------------------------------------
    # 内部方法：验证证据
    # ------------------------------------------------------------------

    async def _verify_evidence(
        self, results: list[dict]
    ) -> list[dict]:
        """
        验证证据质量。
        """
        for paper in results:
            evidence_list = paper.get("evidence", [])
            if not evidence_list:
                continue

            try:
                # 验证一致性
                consistency = await self.verifier.verify_consistency(
                    evidence_list,
                    document_metadata=paper.get("metadata"),
                )

                if not consistency.get("is_consistent", True):
                    logger.warning(
                        f"Evidence inconsistency for {paper.get('paper_id')}: "
                        f"{consistency.get('issues', [])}"
                    )
                    paper["evidence_issues"] = consistency.get("issues", [])

            except Exception as e:
                logger.warning(f"Evidence verification failed: {e}")

        return results
