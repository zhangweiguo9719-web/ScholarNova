"""
证据相关的 Pydantic Schemas
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    """验证结论"""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"
    INSUFFICIENT = "insufficient"


class EvidenceSpanBase(BaseModel):
    """证据片段基础"""

    claim: str = Field(..., description="被验证的声明")
    evidence_text: str = Field(..., description="原文证据片段")
    verdict: Verdict = Field(..., description="验证结论")
    confidence: float = Field(..., description="置信度", ge=0, le=1)
    page_number: Optional[int] = Field(None, description="页码")
    section: Optional[str] = Field(None, description="所在章节")
    context: Optional[str] = Field(None, description="上下文信息")


class EvidenceSpanCreate(EvidenceSpanBase):
    """创建证据片段"""

    run_id: str = Field(..., description="搜索运行 ID")
    paper_id: str = Field(..., description="论文 ID")
    llm_model: Optional[str] = Field(None, description="使用的 LLM 模型")


class EvidenceSpan(EvidenceSpanBase):
    """证据片段"""

    id: str = Field(..., description="证据 ID")
    run_id: str = Field(..., description="搜索运行 ID")
    paper_id: str = Field(..., description="论文 ID")
    llm_model: Optional[str] = Field(None, description="使用的 LLM 模型")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class EvidenceResult(BaseModel):
    """证据结果"""

    paper_id: str = Field(..., description="论文 ID")
    claims: List[str] = Field(..., description="验证的声明列表")
    evidence_spans: List[EvidenceSpan] = Field(..., description="证据列表")
    overall_verdict: Verdict = Field(..., description="整体验证结论")
    overall_confidence: float = Field(..., description="整体置信度", ge=0, le=1)


class EvidenceResponse(BaseModel):
    """证据响应"""

    paper_id: str = Field(..., description="论文 ID")
    run_id: str = Field(..., description="搜索运行 ID")
    evidence_spans: List[EvidenceSpan] = Field(..., description="证据列表")

    @property
    def supporting_evidence(self) -> List[EvidenceSpan]:
        """获取支持性证据"""
        return [e for e in self.evidence_spans if e.verdict == Verdict.SUPPORTS]

    @property
    def contradicting_evidence(self) -> List[EvidenceSpan]:
        """获取反驳性证据"""
        return [e for e in self.evidence_spans if e.verdict == Verdict.CONTRADICTS]

    @property
    def average_confidence(self) -> float:
        """计算平均置信度"""
        if not self.evidence_spans:
            return 0.0
        return sum(e.confidence for e in self.evidence_spans) / len(self.evidence_spans)

    @property
    def has_strong_support(self) -> bool:
        """是否有强支持证据"""
        return any(
            e.verdict == Verdict.SUPPORTS and e.confidence >= 0.8
            for e in self.evidence_spans
        )
