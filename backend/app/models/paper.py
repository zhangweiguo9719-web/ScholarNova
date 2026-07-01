"""
论文实体模型

存储论文的元数据信息
"""

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, func
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column
import json

from app.database import Base


class PaperEntity(Base):
    """论文实体模型"""

    __tablename__ = "paper_entities"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # 规范化 DOI（用于去重）
    canonical_doi: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="规范化 DOI",
    )

    # 规范化数据（合并多个来源的数据）
    canonical_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="规范化数据",
    )

    # 版本聚类（同一论文的不同版本）
    version_cluster: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="版本聚类信息",
    )

    # 外部数据源 ID
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="外部数据源 ID",
    )

    # 论文标题
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="论文标题",
    )

    # 摘要
    abstract: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="摘要",
    )

    # 作者列表
    authors: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment="作者列表",
    )

    # 发表年份
    year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="发表年份",
    )

    # 发表期刊/会议
    venue: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="发表期刊/会议",
    )

    # DOI
    doi: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="DOI",
    )

    # 论文链接
    url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="论文链接",
    )

    # PDF 链接
    pdf_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="PDF 链接",
    )

    # 数据来源
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="数据来源",
    )

    # 引用数
    citation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,
        comment="引用数",
    )

    # 是否开放获取
    is_open_access: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否开放获取",
    )

    # 研究领域
    fields_of_study: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="研究领域",
    )

    # 关键词
    keywords: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="关键词",
    )

    # 发表日期
    publication_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="发表日期",
    )

    # 卷号
    volume: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="卷号",
    )

    # 期号
    issue: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="期号",
    )

    # 页码
    pages: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="页码",
    )

    # 参考文献
    references: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment="参考文献",
    )

    # 其他元数据
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="其他元数据",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<PaperEntity(id={self.id}, title={self.title[:50]}...)>"

    @property
    def author_names(self) -> List[str]:
        """获取作者姓名列表"""
        if not self.authors:
            return []
        return [author.get("name", "") for author in self.authors]

    @property
    def first_author(self) -> Optional[str]:
        """获取第一作者"""
        names = self.author_names
        return names[0] if names else None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "external_id": self.external_id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "doi": self.doi,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "source": self.source,
            "citation_count": self.citation_count,
            "is_open_access": self.is_open_access,
            "fields_of_study": self.fields_of_study,
            "keywords": self.keywords,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
        }
