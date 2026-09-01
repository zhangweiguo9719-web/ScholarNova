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
) -> CitationVerification:
    """Check that factual answer segments use only provided source markers."""
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
        return CitationVerification(
            status="failed",
            coverage=0.0,
            claim_count=0,
            cited_claim_count=0,
            uncited_claim_count=0,
            used_citation_ids=tuple(sorted(used)),
            invalid_citation_ids=invalid,
        )

    coverage = cited_claims / claim_count
    if coverage == 1.0 and not invalid:
        status: VerificationStatus = "verified"
    elif cited_claims > 0 and coverage >= 0.5:
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
