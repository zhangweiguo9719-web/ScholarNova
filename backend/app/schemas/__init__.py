"""
Pydantic Schemas

用于 API 请求/响应验证
"""

from app.schemas.evidence import EvidenceResponse, EvidenceResult, EvidenceSpan, EvidenceSpanCreate
from app.schemas.knowledge import (
    AIAnalyzeRequest,
    AIAnalyzeResponse,
    CategoryCount,
    KnowledgeCreate,
    KnowledgeListResponse,
    KnowledgeResponse,
    KnowledgeUpdate,
    RecommendRequest,
    RecommendResponse,
    RouteCreate,
    RouteListResponse,
    RouteResponse,
    RouteUpdate,
)
from app.schemas.paper import Paper, PaperDetail, PaperList, PaperReference
from app.schemas.query import (
    AnalysisRequest,
    AnalysisResult,
    CompareRequest,
    CompareResult,
    Constraint,
    QueryParseResult,
    SubQuery,
)
from app.schemas.search import (
    HealthResponse,
    ModelConfig,
    ModelTestRequest,
    ModelTestResponse,
    RecommendationFeedback,
    RecommendationRequest,
    RecommendationResponse,
    SearchRequest,
    SearchResponse,
    SearchRunDetail,
    SearchStatus,
    SuccessResponse,
)

__all__ = [
    # Query
    "QueryParseResult",
    "SubQuery",
    "Constraint",
    "AnalysisRequest",
    "AnalysisResult",
    "CompareRequest",
    "CompareResult",
    # Paper
    "Paper",
    "PaperDetail",
    "PaperList",
    "PaperReference",
    # Search
    "SearchRequest",
    "SearchResponse",
    "SearchRunDetail",
    "SearchStatus",
    "ModelConfig",
    "ModelTestRequest",
    "ModelTestResponse",
    "RecommendationRequest",
    "RecommendationResponse",
    "RecommendationFeedback",
    "HealthResponse",
    "SuccessResponse",
    # Evidence
    "EvidenceSpan",
    "EvidenceSpanCreate",
    "EvidenceResult",
    "EvidenceResponse",
    # Knowledge
    "KnowledgeCreate",
    "KnowledgeUpdate",
    "KnowledgeResponse",
    "KnowledgeListResponse",
    "CategoryCount",
    "RouteCreate",
    "RouteUpdate",
    "RouteResponse",
    "RouteListResponse",
    "AIAnalyzeRequest",
    "AIAnalyzeResponse",
    "RecommendRequest",
    "RecommendResponse",
]
