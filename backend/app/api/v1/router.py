"""
API v1 路由注册
"""

from fastapi import APIRouter

from app.api.v1 import analysis, evidence, health, knowledge, model_config, network, papers, recommendations, search

# 创建 API 路由器
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(
    search.router,
    prefix="/search",
    tags=["search"],
)

api_router.include_router(
    papers.router,
    prefix="/papers",
    tags=["papers"],
)

api_router.include_router(
    analysis.router,
    prefix="/papers",
    tags=["analysis"],
)

api_router.include_router(
    evidence.router,
    prefix="/evidence",
    tags=["evidence"],
)

api_router.include_router(
    recommendations.router,
    prefix="/recommendations",
    tags=["recommendations"],
)

api_router.include_router(
    model_config.router,
    prefix="/model",
    tags=["model"],
)

api_router.include_router(
    health.router,
    tags=["health"],
)

api_router.include_router(
    knowledge.router,
    prefix="/knowledge",
    tags=["knowledge"],
)

api_router.include_router(
    network.router,
    prefix="/network",
    tags=["network"],
)
