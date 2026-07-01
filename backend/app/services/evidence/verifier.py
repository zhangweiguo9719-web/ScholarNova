"""
证据验证器

验证证据质量和一致性。
包括：
1. 来源可追溯性检查
2. 原文引用验证
3. 置信度评估
4. 一致性检查（同一篇论文的不同约束证据是否矛盾）
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from app.schemas.evidence import Verdict

logger = logging.getLogger(__name__)


@dataclass
class VerifiedEvidenceResult:
    """验证后的证据结果"""

    constraint_key: str
    verdict: str  # "satisfied" | "violated" | "unknown"
    source_level: str  # "metadata" | "abstract" | "fulltext"
    evidence_spans: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    quality_score: float = 0.0  # 证据质量评分
    issues: list[str] = field(default_factory=list)  # 发现的问题


class EvidenceVerifier:
    """
    证据验证器

    验证证据质量和一致性。
    使用 LLM 辅助进行语义级别的验证。
    """

    def __init__(self, llm_gateway=None):
        """
        初始化验证器。

        Args:
            llm_gateway: LLM 网关实例
        """
        self.llm_gateway = llm_gateway

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    async def verify(
        self,
        claim: str,
        evidence_text: str,
        context: Optional[str] = None,
    ) -> dict:
        """
        验证单条声明与证据的关系（兼容旧接口）。

        Args:
            claim: 待验证的声明
            evidence_text: 证据文本
            context: 上下文信息

        Returns:
            验证结果，包含 verdict 和 confidence
        """
        if self.llm_gateway:
            return await self._verify_with_llm(claim, evidence_text, context)

        # 规则回退
        return self._verify_with_rules(claim, evidence_text)

    async def verify_evidence_spans(
        self,
        evidence_spans: list[dict],
        document_text: str,
    ) -> list[VerifiedEvidenceResult]:
        """
        验证一组证据片段的质量。

        Args:
            evidence_spans: 证据片段列表
            document_text: 原始文档文本

        Returns:
            验证后的证据结果列表
        """
        results: list[VerifiedEvidenceResult] = []

        for span in evidence_spans:
            # 1. 来源可追溯性检查
            traceability_issues = self._check_traceability(span)

            # 2. 原文引用验证
            quote_issues = self._check_quote_validity(span, document_text)

            # 3. 置信度评估
            adjusted_confidence = self._assess_confidence(
                span, traceability_issues, quote_issues
            )

            # 4. 综合质量评分
            quality_score = self._compute_quality_score(
                span, traceability_issues, quote_issues
            )

            issues = traceability_issues + quote_issues

            results.append(
                VerifiedEvidenceResult(
                    constraint_key=span.get("constraint_key", ""),
                    verdict=span.get("verdict", "unknown"),
                    source_level=span.get("source_level", ""),
                    evidence_spans=span.get("evidence_spans", []),
                    confidence=adjusted_confidence,
                    reasoning=span.get("reasoning", ""),
                    quality_score=quality_score,
                    issues=issues,
                )
            )

        return results

    async def verify_consistency(
        self,
        evidence_list: list[dict],
        document_metadata: Optional[dict] = None,
    ) -> dict:
        """
        检查同一论文中不同约束证据的一致性。

        Args:
            evidence_list: 证据列表
            document_metadata: 文档元数据

        Returns:
            一致性检查结果
        """
        issues: list[str] = []

        # 检查 verdict 矛盾
        satisfied_keys = [
            e["constraint_key"]
            for e in evidence_list
            if e.get("verdict") == "satisfied"
        ]
        violated_keys = [
            e["constraint_key"]
            for e in evidence_list
            if e.get("verdict") == "violated"
        ]

        # 检查同一约束的不同 verdict
        key_verdicts: dict[str, list[str]] = {}
        for e in evidence_list:
            key = e.get("constraint_key", "")
            verdict = e.get("verdict", "unknown")
            key_verdicts.setdefault(key, []).append(verdict)

        for key, verdicts in key_verdicts.items():
            unique_verdicts = set(verdicts)
            if "satisfied" in unique_verdicts and "violated" in unique_verdicts:
                issues.append(
                    f"Contradictory verdicts for constraint '{key}': "
                    f"both 'satisfied' and 'violated' found"
                )

        # 检查证据片段与元数据的一致性
        if document_metadata:
            metadata_issues = self._check_metadata_consistency(
                evidence_list, document_metadata
            )
            issues.extend(metadata_issues)

        # 使用 LLM 进行语义一致性检查
        if self.llm_gateway and len(evidence_list) >= 2:
            llm_issues = await self._check_semantic_consistency(evidence_list)
            issues.extend(llm_issues)

        return {
            "is_consistent": len(issues) == 0,
            "issues": issues,
            "total_evidence": len(evidence_list),
            "satisfied_count": len(satisfied_keys),
            "violated_count": len(violated_keys),
        }

    # ------------------------------------------------------------------
    # 来源可追溯性检查
    # ------------------------------------------------------------------

    def _check_traceability(self, span: dict) -> list[str]:
        """
        检查证据来源可追溯性。

        规则：
        - evidence_spans 中的每个片段必须有 section_name
        - source_level 必须是 metadata/abstract/fulltext 之一
        """
        issues: list[str] = []

        source_level = span.get("source_level", "")
        if source_level not in ("metadata", "abstract", "fulltext", ""):
            issues.append(f"Invalid source_level: '{source_level}'")

        evidence_spans = span.get("evidence_spans", [])
        for i, es in enumerate(evidence_spans):
            if isinstance(es, dict):
                section = es.get("section_name", "")
                if not section:
                    issues.append(f"Evidence span {i} missing section_name")
            elif hasattr(es, "section_name"):
                if not es.section_name:
                    issues.append(f"Evidence span {i} missing section_name")

        return issues

    # ------------------------------------------------------------------
    # 原文引用验证
    # ------------------------------------------------------------------

    def _check_quote_validity(
        self, span: dict, document_text: str
    ) -> list[str]:
        """
        检查原文引用的有效性。

        规则：
        - 引用文本必须在原文中存在
        - 引用不能太短（至少 10 个字符）
        - 引用不能是改写的
        """
        issues: list[str] = []
        evidence_spans = span.get("evidence_spans", [])

        for i, es in enumerate(evidence_spans):
            if isinstance(es, dict):
                quote = es.get("quote_text", "")
            elif hasattr(es, "quote_text"):
                quote = es.quote_text
            else:
                continue

            if not quote:
                issues.append(f"Evidence span {i} has empty quote_text")
                continue

            # 清理引文中的省略号标记
            clean_quote = quote.replace("...", "").strip()
            if len(clean_quote) < 10:
                issues.append(
                    f"Evidence span {i} quote too short: '{clean_quote[:30]}...'"
                )
                continue

            # 检查引文是否在原文中（模糊匹配）
            if document_text:
                # 先尝试精确匹配
                if clean_quote not in document_text:
                    # 尝试忽略大小写匹配
                    if clean_quote.lower() not in document_text.lower():
                        # 尝试部分匹配（取引文核心部分）
                        core_text = clean_quote[:50]
                        if core_text.lower() not in document_text.lower():
                            issues.append(
                                f"Evidence span {i} quote not found in document text"
                            )

        return issues

    # ------------------------------------------------------------------
    # 置信度评估
    # ------------------------------------------------------------------

    def _assess_confidence(
        self,
        span: dict,
        traceability_issues: list[str],
        quote_issues: list[str],
    ) -> float:
        """
        评估证据置信度。

        置信度等级：
        - 高置信度（0.8-1.0）：原文明确陈述
        - 中置信度（0.5-0.8）：原文间接支持
        - 低置信度（0.2-0.5）：原文部分支持
        - 不支持（0.0-0.2）：原文未提及或否定
        """
        base_confidence = span.get("confidence", 0.5)

        # 根据问题调整置信度
        penalty = 0.0
        penalty += len(traceability_issues) * 0.1
        penalty += len(quote_issues) * 0.15

        # 根据 source_level 调整
        source_level = span.get("source_level", "")
        if source_level == "metadata":
            # 元数据级证据通常更可靠
            base_confidence = max(base_confidence, 0.8)
        elif source_level == "abstract":
            base_confidence = max(base_confidence, 0.6)
        elif source_level == "fulltext":
            base_confidence = max(base_confidence, 0.5)

        # 根据 verdict 调整
        verdict = span.get("verdict", "unknown")
        if verdict == "unknown":
            base_confidence = min(base_confidence, 0.3)

        adjusted = max(0.0, min(1.0, base_confidence - penalty))
        return round(adjusted, 2)

    # ------------------------------------------------------------------
    # 质量评分
    # ------------------------------------------------------------------

    def _compute_quality_score(
        self,
        span: dict,
        traceability_issues: list[str],
        quote_issues: list[str],
    ) -> float:
        """
        计算证据质量评分（0-1）。
        综合考虑可追溯性、引用质量和置信度。
        """
        score = 1.0

        # 可追溯性扣分
        score -= len(traceability_issues) * 0.15

        # 引用质量扣分
        score -= len(quote_issues) * 0.2

        # 置信度加权
        confidence = span.get("confidence", 0.5)
        score = score * 0.6 + confidence * 0.4

        return round(max(0.0, min(1.0, score)), 2)

    # ------------------------------------------------------------------
    # 元数据一致性检查
    # ------------------------------------------------------------------

    def _check_metadata_consistency(
        self,
        evidence_list: list[dict],
        document_metadata: dict,
    ) -> list[str]:
        """
        检查证据与元数据的一致性。
        """
        issues: list[str] = []

        for evidence in evidence_list:
            source_level = evidence.get("source_level", "")
            verdict = evidence.get("verdict", "")

            # 如果是元数据级证据，检查引用的元数据是否正确
            if source_level == "metadata":
                spans = evidence.get("evidence_spans", [])
                for span in spans:
                    if isinstance(span, dict):
                        quote = span.get("quote_text", "")
                    elif hasattr(span, "quote_text"):
                        quote = span.quote_text
                    else:
                        continue

                    # 检查年份一致性
                    year_match = re.search(r"(\d{4})", quote)
                    if year_match:
                        cited_year = int(year_match.group(1))
                        meta_year = document_metadata.get("year")
                        if meta_year and int(meta_year) != cited_year:
                            issues.append(
                                f"Year mismatch: evidence cites {cited_year}, "
                                f"metadata says {meta_year}"
                            )

        return issues

    # ------------------------------------------------------------------
    # LLM 辅助验证
    # ------------------------------------------------------------------

    async def _verify_with_llm(
        self,
        claim: str,
        evidence_text: str,
        context: Optional[str] = None,
    ) -> dict:
        """使用 LLM 验证声明。"""
        if not self.llm_gateway:
            return {
                "verdict": Verdict.INSUFFICIENT,
                "confidence": 0.0,
                "explanation": "LLM gateway not available",
            }

        prompt = self._build_prompt(claim, evidence_text, context)

        try:
            response = await self.llm_gateway.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an academic evidence verifier. "
                            "Determine whether the evidence supports, contradicts, "
                            "or is neutral/insufficient regarding the claim. "
                            "Always respond in valid JSON format."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
            )

            return self._parse_verification_response(response)

        except Exception as e:
            logger.warning(f"LLM verification failed: {e}")
            return {
                "verdict": Verdict.INSUFFICIENT,
                "confidence": 0.0,
                "explanation": f"LLM verification error: {str(e)}",
            }

    def _build_prompt(
        self,
        claim: str,
        evidence_text: str,
        context: Optional[str] = None,
    ) -> str:
        """构建验证 prompt。"""
        prompt = f"""You are an academic evidence verifier. Your task is to determine whether
the provided evidence supports, contradicts, or is neutral/insufficient regarding the claim.

CLAIM: {claim}

EVIDENCE:
{evidence_text[:4000]}
"""
        if context:
            prompt += f"\nCONTEXT:\n{context[:2000]}\n"

        prompt += """
Please analyze the evidence and provide:
1. Verdict: "supports", "contradicts", "neutral", or "insufficient"
2. Confidence: a number between 0 and 1
3. Brief explanation of your reasoning

Response format (JSON):
{
    "verdict": "...",
    "confidence": 0.0,
    "explanation": "..."
}
"""
        return prompt

    def _parse_verification_response(self, response: str) -> dict:
        """解析 LLM 验证响应。"""
        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if not json_match:
                return {
                    "verdict": Verdict.INSUFFICIENT,
                    "confidence": 0.0,
                    "explanation": "Failed to parse LLM response",
                }

            data = json.loads(json_match.group())

            # 映射 verdict
            raw_verdict = data.get("verdict", "insufficient").lower()
            verdict_map = {
                "supports": Verdict.SUPPORTS,
                "support": Verdict.SUPPORTS,
                "contradicts": Verdict.CONTRADICTS,
                "contradict": Verdict.CONTRADICTS,
                "neutral": Verdict.NEUTRAL,
                "insufficient": Verdict.INSUFFICIENT,
            }
            verdict = verdict_map.get(raw_verdict, Verdict.INSUFFICIENT)

            return {
                "verdict": verdict,
                "confidence": float(data.get("confidence", 0.5)),
                "explanation": data.get("explanation", ""),
            }

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse verification response: {e}")
            return {
                "verdict": Verdict.INSUFFICIENT,
                "confidence": 0.0,
                "explanation": f"Response parsing error: {str(e)}",
            }

    async def _check_semantic_consistency(
        self, evidence_list: list[dict]
    ) -> list[str]:
        """使用 LLM 检查语义一致性。"""
        if not self.llm_gateway:
            return []

        # 构建一致性检查 prompt
        evidence_summaries = []
        for e in evidence_list[:10]:  # 限制数量
            key = e.get("constraint_key", "")
            verdict = e.get("verdict", "")
            reasoning = e.get("reasoning", "")
            evidence_summaries.append(
                f"- Constraint '{key}': {verdict} ({reasoning})"
            )

        prompt = f"""Check if the following evidence verdicts from the same paper are consistent:

{chr(10).join(evidence_summaries)}

Are there any logical contradictions? For example:
- A paper cannot both use and not use the same dataset
- A paper cannot both apply and not apply the same method

Response format (JSON):
{{
    "is_consistent": true/false,
    "issues": ["issue 1", "issue 2"]
}}
"""
        try:
            response = await self.llm_gateway.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an academic evidence consistency checker. "
                            "Always respond in valid JSON format."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
            )

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("issues", [])

        except Exception as e:
            logger.warning(f"LLM consistency check failed: {e}")

        return []

    # ------------------------------------------------------------------
    # 规则回退验证
    # ------------------------------------------------------------------

    def _verify_with_rules(self, claim: str, evidence_text: str) -> dict:
        """规则回退验证（不使用 LLM）。"""
        claim_lower = claim.lower()
        evidence_lower = evidence_text.lower()

        # 简单关键词匹配
        claim_words = set(claim_lower.split())
        evidence_words = set(evidence_lower.split())
        overlap = claim_words.intersection(evidence_words)

        if len(overlap) > len(claim_words) * 0.5:
            return {
                "verdict": Verdict.SUPPORTS,
                "confidence": 0.6,
                "explanation": f"Keyword overlap: {len(overlap)} words match",
            }
        elif len(overlap) > len(claim_words) * 0.2:
            return {
                "verdict": Verdict.NEUTRAL,
                "confidence": 0.4,
                "explanation": f"Partial keyword overlap: {len(overlap)} words match",
            }
        else:
            return {
                "verdict": Verdict.INSUFFICIENT,
                "confidence": 0.2,
                "explanation": "Insufficient keyword overlap",
            }
