"""
论文相关的 Pydantic Schemas
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PaperAuthor(BaseModel):
    """论文作者"""

    name: str = Field(..., description="作者姓名")
    affiliation: Optional[str] = Field(None, description="所属机构")
    orcid: Optional[str] = Field(None, description="ORCID")


class PaperReference(BaseModel):
    """论文引用"""

    id: str | UUID = Field(..., description="论文 ID")
    title: str = Field(..., description="论文标题")
    year: Optional[int] = Field(None, description="发表年份")
    citation_count: int = Field(0, description="引用数")


class PaperQuality(BaseModel):
    """可追溯的论文质量信号；未知的商业分区绝不推断。"""

    quality_score: float = Field(0, ge=0, le=1, description="开放指标综合质量分")
    citation_percentile: float = Field(
        0, ge=0, le=1, description="当前候选结果集内的引用百分位"
    )
    citation_velocity: float = Field(0, ge=0, description="年均引用数")
    impact_label: str = Field("limited_signal", description="引用影响力标签")
    citation_basis: str = Field(
        "result_set", description="百分位计算口径，当前为 result_set"
    )
    wos_indexed: Optional[bool] = Field(None, description="Web of Science 收录状态")
    jcr_quartile: Optional[str] = Field(None, description="经授权数据核验的 JCR 分区")
    cas_quartile: Optional[str] = Field(None, description="经授权数据核验的中科院分区")
    partition_year: Optional[int] = Field(None, description="分区数据年份")
    partition_status: str = Field(
        "unverified", description="分区核验状态：verified/unverified"
    )
    partition_source: Optional[str] = Field(None, description="分区数据来源")


class Paper(BaseModel):
    """论文基本信息"""

    id: str | UUID = Field(..., description="论文 ID")
    title: str = Field(..., description="论文标题")
    authors: List[str] = Field(default_factory=list, description="作者列表")
    abstract: Optional[str] = Field(None, description="摘要")
    year: Optional[int] = Field(None, description="发表年份")
    venue: Optional[str] = Field(None, description="发表期刊/会议")
    citation_count: int = Field(0, description="引用数")
    doi: Optional[str] = Field(None, description="DOI")
    url: Optional[str] = Field(None, description="论文链接")
    pdf_url: Optional[str] = Field(None, description="PDF 链接")
    source: str = Field(..., description="数据来源")
    corpus_id: Optional[str] = Field(
        None, description="Semantic Scholar CorpusId（官方评测对齐用）"
    )
    relevance_score: Optional[float] = Field(None, description="相关性分数", ge=0, le=1)
    is_open_access: bool = Field(False, description="是否开放获取")
    quality: Optional[PaperQuality] = Field(None, description="论文质量分析")


class PaperDetail(Paper):
    """论文详细信息"""

    references: List[PaperReference] = Field(default_factory=list, description="参考文献")
    citations: List[PaperReference] = Field(default_factory=list, description="引用")
    fields_of_study: List[str] = Field(default_factory=list, description="研究领域")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    publication_date: Optional[date] = Field(None, description="发表日期")
    volume: Optional[str] = Field(None, description="卷号")
    issue: Optional[str] = Field(None, description="期号")
    pages: Optional[str] = Field(None, description="页码")
    metadata: Optional[Dict[str, Any]] = Field(None, description="其他元数据")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class PaperList(BaseModel):
    """论文列表"""

    papers: List[Paper] = Field(..., description="论文列表")
    total: int = Field(..., description="总数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页数量")
    has_more: bool = Field(False, description="是否有更多")
