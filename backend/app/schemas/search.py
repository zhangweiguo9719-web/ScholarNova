"""
搜索相关的 Pydantic Schemas
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.evidence import EvidenceSpan
from app.schemas.paper import Paper
from app.schemas.query import Constraint, DataSource, QueryParseResult


class SearchStatus(str, Enum):
    """搜索状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SearchRequest(BaseModel):
    """搜索请求"""

    query: str = Field(..., description="用户的自然语言查询", min_length=1, max_length=2000)
    constraints: List[Constraint] = Field(
        default_factory=list,
        description="约束条件列表",
    )
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="用户偏好设置（如排序偏好、语言偏好等）",
    )
    max_results: int = Field(50, description="最大返回结果数", ge=1, le=500)
    sources: List[DataSource] = Field(
        default=[DataSource.CROSSREF, DataSource.OPENALEX],
        description="指定数据源",
    )
    date_from: Optional[str] = Field(None, description="起始日期 (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    min_citations: Optional[int] = Field(None, description="最小引用数", ge=0)
    open_access_only: bool = Field(False, description="仅开放获取论文")


class SearchProgress(BaseModel):
    """搜索进度"""

    total_sources: int = Field(0, description="总数据源数")
    completed_sources: int = Field(0, description="已完成数据源数")
    total_papers: int = Field(0, description="总论文数")
    deduplicated_papers: int = Field(0, description="去重后论文数")
    current_phase: str = Field("pending", description="当前阶段")
    search_rounds: int = Field(0, description="实际检索轮次")
    api_calls: int = Field(0, description="学术检索 API 调用次数")
    latency_ms: float = Field(0, description="当前端到端耗时（毫秒）")


class SearchResponse(BaseModel):
    """搜索响应"""

    run_id: str = Field(..., description="搜索运行 ID")
    status: SearchStatus = Field(..., description="搜索状态")
    query_plan: Optional[QueryParseResult] = Field(None, description="查询计划")
    papers: List[Paper] = Field(default_factory=list, description="搜索结果论文列表")
    matched_constraints: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="匹配的约束条件",
    )
    evidence: List[EvidenceSpan] = Field(
        default_factory=list,
        description="证据片段列表",
    )
    recommendation_reason: Optional[str] = Field(None, description="推荐理由")
    uncertainty: Optional[float] = Field(None, description="不确定性分数", ge=0, le=1)
    coverage: Optional[float] = Field(None, description="覆盖率", ge=0, le=1)
    message: str = Field(..., description="状态消息")


class SearchRunDetail(BaseModel):
    """搜索运行详情"""

    run_id: str = Field(..., description="搜索运行 ID")
    status: SearchStatus = Field(..., description="搜索状态")
    original_query: str = Field(..., description="原始查询")
    query_plan: Optional[Dict[str, Any]] = Field(None, description="查询计划")
    progress: Optional[SearchProgress] = Field(None, description="进度信息")
    results: List[Paper] = Field(default_factory=list, description="搜索结果")
    source_status: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="各轮各数据源检索状态",
    )
    runtime_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="API 调用、轮次、延迟和结果质量分层等运行指标",
    )
    result_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="面向复杂查询的结构化结果摘要",
    )
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")


LLMProviderName = Literal[
    "openai",
    "anthropic",
    "ollama",
    "mimo",
    "deepseek",
    "zhipu",
    "qwen",
    "moonshot",
    "sensenova",
    "custom",
]


class TaskModelConfig(BaseModel):
    """单个任务的模型配置"""

    provider: LLMProviderName = Field("openai", description="LLM 提供商")
    model_name: Optional[str] = Field(None, description="模型名称")
    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, description="自定义 API 地址")


class ModelConfig(BaseModel):
    """多模型配置（支持按任务类型分配不同模型）"""

    # 主配置（所有任务的默认）
    provider: LLMProviderName = Field(..., description="默认 LLM 提供商")
    model_name: str = Field(..., min_length=1, description="默认模型名称")
    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, description="自定义 API 地址")
    temperature: float = Field(0.7, description="温度参数", ge=0, le=2)
    max_tokens: int = Field(4096, description="最大 token 数", ge=1, le=128000)

    # 按任务类型配置（可选，覆盖主配置）
    tasks: Optional[Dict[str, TaskModelConfig]] = Field(None, description="按任务类型配置模型")


class ModelTestRequest(BaseModel):
    """模型测试请求"""

    provider: LLMProviderName = Field(..., description="LLM 提供商")
    model_name: str = Field(..., min_length=1, description="模型名称")
    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, description="自定义 API 地址")


class ModelTestResponse(BaseModel):
    """模型测试响应"""

    success: bool = Field(..., description="测试是否成功")
    latency_ms: Optional[float] = Field(None, description="响应延迟（毫秒）")
    model_info: Optional[Dict[str, Any]] = Field(None, description="模型信息")
    error: Optional[str] = Field(None, description="错误信息")


class RecommendationRequest(BaseModel):
    """推荐请求"""

    user_id: Optional[str] = Field(None, description="用户 ID")
    context: Optional[str] = Field(None, description="推荐上下文")
    limit: int = Field(10, description="推荐数量", ge=1, le=50)


class RecommendationItem(BaseModel):
    """推荐项"""

    id: str = Field(..., description="推荐 ID")
    paper: Paper = Field(..., description="推荐的论文")
    score: float = Field(..., description="推荐分数", ge=0, le=1)
    reason: str = Field(..., description="推荐理由")


class RecommendationResponse(BaseModel):
    """推荐响应"""

    recommendations: List[RecommendationItem] = Field(..., description="推荐列表")
    has_more: bool = Field(False, description="是否有更多")


class RecommendationFeedback(BaseModel):
    """推荐反馈"""

    recommendation_id: str = Field(..., description="推荐 ID")
    feedback_type: str = Field(
        ...,
        description="反馈类型",
        pattern="^(helpful|not_helpful|saved|dismissed)$",
    )
    comment: Optional[str] = Field(None, description="评论", max_length=500)


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本号")
    timestamp: datetime = Field(..., description="检查时间")
    services: Dict[str, str] = Field(..., description="依赖服务状态")


class SuccessResponse(BaseModel):
    """成功响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")
