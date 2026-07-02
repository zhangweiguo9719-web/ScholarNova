"""
推荐模型

存储系统生成的文献推荐和用户反馈
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.paper import PaperEntity
    from app.models.search_run import SearchRun


class Recommendation(Base):
    """推荐模型"""

    __tablename__ = "recommendations"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # 来源搜索运行
    search_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("search_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="来源搜索运行",
    )

    # 推荐的论文
    paper_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("paper_entities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="推荐的论文",
    )

    # 排名
    rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="排名",
    )

    # 推荐分数 (0-1)
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="推荐分数",
    )

    # 分数分解
    score_breakdown: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="分数分解",
    )

    # 推荐角色
    recommendation_role: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="推荐角色（如 core, supplementary, contrasting）",
    )

    # 推荐理由
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="推荐理由",
    )

    # 是否被忽略
    is_dismissed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否被忽略",
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
        back_populates="recommendations",
    )

    paper: Mapped["PaperEntity"] = relationship(
        "PaperEntity",
        lazy="joined",
    )

    feedbacks: Mapped[list["RecommendationFeedback"]] = relationship(
        "RecommendationFeedback",
        back_populates="recommendation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Recommendation(id={self.id}, rank={self.rank}, score={self.score})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": str(self.id),
            "search_run_id": str(self.search_run_id),
            "paper_id": str(self.paper_id),
            "rank": self.rank,
            "score": self.score,
            "score_breakdown": self.score_breakdown,
            "recommendation_role": self.recommendation_role,
            "reason": self.reason,
            "is_dismissed": self.is_dismissed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RecommendationFeedback(Base):
    """推荐反馈模型"""

    __tablename__ = "recommendation_feedback"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # 关联的推荐
    recommendation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的推荐",
    )

    # 用户 ID
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="用户 ID",
    )

    # 反馈类型: helpful/not_helpful/saved/dismissed
    feedback_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="反馈类型",
    )

    # 评论
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="评论",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )

    # 关系
    recommendation: Mapped["Recommendation"] = relationship(
        "Recommendation",
        back_populates="feedbacks",
    )

    def __repr__(self) -> str:
        return f"<RecommendationFeedback(id={self.id}, type={self.feedback_type})>"

    @property
    def is_positive(self) -> bool:
        """是否为正面反馈"""
        return self.feedback_type in ("helpful", "saved")

    @property
    def is_negative(self) -> bool:
        """是否为负面反馈"""
        return self.feedback_type in ("not_helpful", "dismissed")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": str(self.id),
            "recommendation_id": str(self.recommendation_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "feedback_type": self.feedback_type,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
