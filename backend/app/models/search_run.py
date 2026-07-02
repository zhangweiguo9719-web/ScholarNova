"""
搜索运行模型

存储文献检索任务的信息
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.evidence import EvidenceSpan
    from app.models.recommendation import Recommendation


class SearchRun(Base):
    """搜索运行模型"""

    __tablename__ = "search_runs"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # 用户会话标识（可选）
    user_session: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="用户会话标识",
    )

    # 用户原始查询
    raw_query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="用户原始查询",
    )

    # LLM 解析后的结构化查询
    parsed_query: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="LLM 解析后的结构化查询",
    )

    # LLM 生成的查询计划
    query_plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="LLM 生成的查询计划",
    )

    # 各数据源的状态
    source_status: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="各数据源的状态",
    )

    # 使用的模型名称
    model_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="使用的模型名称",
    )

    # 请求延迟（毫秒）
    latency_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="请求延迟（毫秒）",
    )

    # Token 使用量
    token_usage: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Token 使用量",
    )

    # 状态: pending/running/completed/failed
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="搜索状态",
    )

    # 请求的数据源列表
    sources: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="请求的数据源列表",
    )

    # 最大结果数
    max_results: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        comment="最大结果数",
    )

    # 过滤条件
    filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="过滤条件",
    )

    # 进度信息
    progress: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="进度信息",
    )

    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="开始执行时间",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="完成时间",
    )

    # 关系
    evidence_spans: Mapped[List["EvidenceSpan"]] = relationship(
        "EvidenceSpan",
        back_populates="search_run",
        cascade="all, delete-orphan",
    )

    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation",
        back_populates="search_run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SearchRun(id={self.id}, status={self.status})>"

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.status == "running"

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        """是否失败"""
        return self.status == "failed"

    def update_progress(self, progress: Dict[str, Any]) -> None:
        """更新进度"""
        self.progress = progress

    def mark_as_running(self) -> None:
        """标记为运行中"""
        self.status = "running"
        self.started_at = datetime.utcnow()

    def mark_as_completed(self) -> None:
        """标记为已完成"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()

    def mark_as_failed(self, error_message: str) -> None:
        """标记为失败"""
        self.status = "failed"
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
