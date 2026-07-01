"""
研究知识库模型

存储用户的研究知识点和研究路线
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class KnowledgeBase(Base):
    """研究知识库表"""

    __tablename__ = "knowledge_base"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # 知识点标题
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="知识点标题",
    )

    # 分类
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="分类（如：联邦学习、隐私保护、医疗AI）",
    )

    # AI分析的详细内容
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AI分析的详细内容（中文）",
    )

    # 来源论文ID（可选）
    source_paper_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="来源论文ID",
    )

    # 来源论文标题
    source_paper_title: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="来源论文标题",
    )

    # 来源论文DOI
    source_paper_doi: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="来源论文DOI",
    )

    # 提取的研究点列表
    research_points: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="提取的研究点列表",
    )

    # 标签列表
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="标签列表",
    )

    # 用户备注
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="用户备注",
    )

    # 卡片类型: research_point/direction/architecture/paper/analysis
    card_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="卡片类型",
    )

    # 结构化卡片数据
    card_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="结构化卡片数据",
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
        return f"<KnowledgeBase(id={self.id}, title={self.title[:50]}...)>"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "content": self.content,
            "source_paper_id": self.source_paper_id,
            "source_paper_title": self.source_paper_title,
            "source_paper_doi": self.source_paper_doi,
            "research_points": self.research_points or [],
            "tags": self.tags or [],
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ResearchRoute(Base):
    """研究路线表"""

    __tablename__ = "research_routes"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # 路线标题
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="路线标题",
    )

    # 路线描述
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="路线描述",
    )

    # 关联的知识点ID列表
    knowledge_ids: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="关联的知识点ID列表",
    )

    # AI生成的路线分析
    ai_analysis: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI生成的路线分析（包含架构图）",
    )

    # 状态
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        index=True,
        comment="状态：active/completed/archived",
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
        return f"<ResearchRoute(id={self.id}, title={self.title[:50]}...)>"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "knowledge_ids": self.knowledge_ids or [],
            "ai_analysis": self.ai_analysis,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
