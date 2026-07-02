"""
证据片段模型

存储从论文中提取的证据片段
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.paper import PaperEntity
    from app.models.search_run import SearchRun


class EvidenceSpan(Base):
    """证据片段模型"""

    __tablename__ = "evidence_spans"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # 关联的搜索运行
    search_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("search_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的搜索运行",
    )

    # 关联的论文
    paper_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("paper_entities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="关联的论文",
    )

    # 约束键（标识该证据对应哪个约束条件）
    constraint_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="约束键",
    )

    # 验证结论: supports/contradicts/neutral/insufficient
    verdict: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="验证结论",
    )

    # 数据源级别
    source_level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="数据源级别（如 abstract, fulltext, metadata）",
    )

    # 章节名称
    section_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="所在章节",
    )

    # 段落索引
    paragraph_index: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="段落索引",
    )

    # 引用原文
    quote_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="引用原文",
    )

    # 置信度 (0-1)
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="置信度",
    )

    # 使用的 LLM 模型
    llm_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="使用的 LLM 模型",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )

    # 关系
    search_run: Mapped["SearchRun"] = relationship(
        "SearchRun",
        back_populates="evidence_spans",
    )

    paper: Mapped["PaperEntity"] = relationship(
        "PaperEntity",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<EvidenceSpan(id={self.id}, verdict={self.verdict})>"

    @property
    def supports(self) -> bool:
        """是否支持"""
        return self.verdict == "supports"

    @property
    def contradicts(self) -> bool:
        """是否反驳"""
        return self.verdict == "contradicts"

    @property
    def is_neutral(self) -> bool:
        """是否中立"""
        return self.verdict == "neutral"

    @property
    def has_insufficient_evidence(self) -> bool:
        """证据是否不足"""
        return self.verdict == "insufficient"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": str(self.id),
            "search_run_id": str(self.search_run_id),
            "paper_id": str(self.paper_id),
            "constraint_key": self.constraint_key,
            "verdict": self.verdict,
            "source_level": self.source_level,
            "section_name": self.section_name,
            "paragraph_index": self.paragraph_index,
            "quote_text": self.quote_text,
            "confidence": self.confidence,
            "llm_model": self.llm_model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
