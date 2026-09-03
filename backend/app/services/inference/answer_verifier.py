"""Deterministic citation checks and a no-model evidence fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

VerificationStatus = Literal["verified", "partial", "failed", "not_applicable"]

_CITATION = re.compile(r"\[(s\d+)\]", re.IGNORECASE)
_CLAIM_SPLIT = re.compile(r"(?<=[。！？.!?])|\n+")
_TRAILING_CITATIONS = re.compile(
    r"([。！？.!?])\s*((?:\[s\d+\]\s*)+)",
    re.IGNORECASE,
)
_MARKUP_PREFIX = re.compile(r"^(?:[-*#>]+|\d+[.)、])\s*")
_HEADING = re.compile(
    r"^(?:直接结论|证据与说明|仍需确认的问题|参考材料|说明|"
    r"direct conclusion|evidence(?: and notes)?|questions? to confirm|"
    r"retrieved evidence|note)\s*[:：]?$",
    re.IGNORECASE,
)
_META_PREFIXES = (
    "回答模型暂时不可用",
    "以下内容为检索到的原始证据",
    "这是检索结果而非模型归纳",
    "说明：",
    "the answer model is temporarily unavailable",
    "the following items are retrieved evidence",
    "these are retrieval results rather than a model synthesis",
    "note:",
)

# 总结/列举/总览类问题标记：这类问题的回答职责是概括检索到的材料，
# 未逐句引用属于正常现象，不应判为"引用校验失败"。
_OVERVIEW_MARKERS = (
    # 中文
    "有哪些", "有什么", "总结", "概括", "列举", "列出", "总览", "概览",
    "包含哪些", "包含什么", "有什么研究", "都有什么", "现在有哪些",
    # 英文
    "what do i have", "what are", "list", "summarize", "summarise",
    "overview", "summarize my", "what's in", "what is in",
)


def _is_overview_question(question: str) -> bool:
    normalized = (question or "").casefold().strip()
    if not normalized:
        return False
    if len(normalized) <= 24 and any(m in normalized for m in _OVERVIEW_MARKERS):
        return True
    return any(normalized.startswith(m) for m in _OVERVIEW_MARKERS)


@dataclass(frozen=True, slots=True)
class CitationVerification:
    """Citation-integrity result; it does not claim semantic entailment."""

    status: VerificationStatus
    coverage: float
    claim_count: int
    cited_claim_count: int
    uncited_claim_count: int
    used_citation_ids: tuple[str, ...] = ()
    invalid_citation_ids: tuple[str, ...] = ()

    @property
    def detail(self) -> str:
        if self.status == "not_applicable":
            return "本回答不需要论文引用校验"
        invalid = (
            f"；无效编号 {', '.join(self.invalid_citation_ids)}"
            if self.invalid_citation_ids
            else ""
        )
        return (
            f"引用覆盖 {self.cited_claim_count}/{self.claim_count} "
            f"({self.coverage:.0%})，未引用事实句 {self.uncited_claim_count}{invalid}"
        )


def _claim_segments(answer: str) -> list[str]:
    claims: list[str] = []
    normalized = _TRAILING_CITATIONS.sub(r"\2\1", answer.replace("\r", ""))
    for raw_segment in _CLAIM_SPLIT.split(normalized):
        segment = _MARKUP_PREFIX.sub("", raw_segment.strip())
        if not segment or _HEADING.fullmatch(segment):
            continue
        plain = _CITATION.sub("", segment).strip(" ：:;；,.，。")
        if len(plain) < 8:
            continue
        lowered = plain.casefold()
        if lowered.startswith(_META_PREFIXES):
            continue
        claims.append(segment)
    return claims


def verify_answer_citations(
    answer: str,
    allowed_citation_ids: Sequence[str],
    *,
    question: str | None = None,
) -> CitationVerification:
    """Check that factual answer segments use only provided source markers.

    ``question`` 用于识别"总结/列举/总览"类问题：这类回答的职责是概括
    检索到的材料，未逐句引用属于正常现象。此时把失败阈值放宽为 partial，
    避免把"我的知识库有哪些"这类问题误报为引用校验失败。
    """
    lenient = _is_overview_question(question) if question else False
    allowed = {source_id.upper() for source_id in allowed_citation_ids}
    claims = _claim_segments(answer)
    used = {
        match.upper()
        for match in _CITATION.findall(answer)
    }
    invalid = tuple(sorted(used - allowed))
    cited_claims = 0
    for claim in claims:
        claim_ids = {match.upper() for match in _CITATION.findall(claim)}
        if claim_ids & allowed:
            cited_claims += 1

    claim_count = len(claims)
    if claim_count == 0:
        status: VerificationStatus = "not_applicable" if lenient else "failed"
        return CitationVerification(
            status=status,
            coverage=0.0,
            claim_count=0,
            cited_claim_count=0,
            uncited_claim_count=0,
            used_citation_ids=tuple(sorted(used)),
            invalid_citation_ids=invalid,
        )

    coverage = cited_claims / claim_count
    used_allowed = used & allowed
    if coverage == 1.0 and not invalid:
        status = "verified"
    elif invalid:
        # 引用了未提供的来源编号，无论何种问题类型都判失败（防幻觉保护）
        status = "failed"
    elif cited_claims > 0 and coverage >= 0.5:
        status = "partial"
    elif lenient and (cited_claims > 0 or bool(used_allowed)):
        # 总结/列举类：回答职责是概括材料，开头或整体引用一次来源即可视为正常
        status = "partial"
    else:
        status = "failed"
    return CitationVerification(
        status=status,
        coverage=round(coverage, 4),
        claim_count=claim_count,
        cited_claim_count=cited_claims,
        uncited_claim_count=claim_count - cited_claims,
        used_citation_ids=tuple(sorted(used & allowed)),
        invalid_citation_ids=invalid,
    )


def build_retrieval_fallback(
    question: str,
    evidence: Sequence[tuple[str, str, str]],
) -> str:
    """Return bounded, directly traceable evidence when the model is offline."""
    is_chinese = bool(re.search(r"[\u4e00-\u9fff]", question))
    if is_chinese:
        lines = [
            "回答模型暂时不可用，以下内容为检索到的原始证据：",
            "",
        ]
    else:
        lines = [
            "The answer model is temporarily unavailable. "
            "The following items are retrieved evidence:",
            "",
        ]
    for index, (source_id, title, content) in enumerate(evidence[:6], start=1):
        snippet = " ".join(content.split())[:240].rstrip(" ,，.;；")
        lines.append(f"{index}. {title}: {snippet} [{source_id}]")
    lines.extend(
        [
            "",
            (
                "说明：这是检索结果而非模型归纳，请根据来源编号返回原文核验。"
                if is_chinese
                else (
                    "Note: These are retrieval results rather than a model synthesis; "
                    "verify them against the cited originals."
                )
            ),
        ]
    )
    return "\n".join(lines)
