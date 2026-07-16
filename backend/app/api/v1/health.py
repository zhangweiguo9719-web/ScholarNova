"""
健康检查 API 端点
"""

import asyncio
import time
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.search import HealthResponse

router = APIRouter()
_data_source_cache: tuple[float, dict[str, str]] = (0.0, {})


async def _check_redis() -> str:
    """检查 Redis 连接状态"""
    try:
        from app.core.cache import CacheManager

        cache = CacheManager()
        client = await cache._get_client()
        await asyncio.wait_for(client.ping(), timeout=2.0)
        return "connected"
    except Exception:
        return "disconnected"


async def _check_llm() -> str:
    """检查 LLM 服务状态"""
    try:
        from app.config import settings

        # 检查是否有配置的 API Key
        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            return "available"
        return "unavailable"
    except Exception:
        return "unavailable"


async def _probe_data_source(client, name: str, url: str) -> tuple[str, str]:
    """Probe one academic source without blocking checks for the other sources."""
    try:
        response = await client.get(url)
        return name, "available" if response.status_code == 200 else "degraded"
    except Exception:
        return name, "unavailable"


@router.get("/health/live")
async def liveness_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Lightweight local liveness check for desktop/startup probes."""
    try:
        await db.execute(text("SELECT 1"))
        database = "connected"
    except Exception:
        database = "disconnected"

    return {
        "status": "ok" if database == "connected" else "degraded",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {"database": database},
    }


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """
    健康检查

    检查服务及其依赖的健康状态
    """
    services = {}

    # 检查数据库连接
    try:
        await db.execute(text("SELECT 1"))
        services["database"] = "connected"
    except Exception:
        services["database"] = "disconnected"

    # 检查 Redis 连接
    services["redis"] = await _check_redis()

    # 检查 LLM 服务
    services["llm"] = await _check_llm()

    # 检查数据源可用性
    global _data_source_cache
    cached_at, cached_sources = _data_source_cache
    data_sources = dict(cached_sources) if time.monotonic() - cached_at < 30 else {}
    if not data_sources:
        try:
            import httpx

            timeout = httpx.Timeout(8.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                probes = await asyncio.gather(
                    _probe_data_source(
                        client,
                        "semantic_scholar",
                        "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1",
                    ),
                    _probe_data_source(
                        client,
                        "openalex",
                        "https://api.openalex.org/works?search=test&per_page=1",
                    ),
                    _probe_data_source(
                        client,
                        "crossref",
                        "https://api.crossref.org/works?query=test&rows=1",
                    ),
                    _probe_data_source(
                        client,
                        "arxiv",
                        "https://export.arxiv.org/api/query?search_query=all:test&max_results=1",
                    ),
                )
                data_sources.update(probes)
                _data_source_cache = (time.monotonic(), dict(data_sources))

        except Exception:
            for source in ["semantic_scholar", "openalex", "crossref", "arxiv"]:
                data_sources[source] = "unknown"

    services.update(data_sources)

    # 确定整体状态
    critical_services = ["database", "redis"]
    critical_ok = all(
        services.get(s) in ("connected", "available")
        for s in critical_services
    )
    llm_ok = services.get("llm") == "available"

    if critical_ok and llm_ok:
        status = "healthy"
    elif critical_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        version="1.0.0",
        timestamp=datetime.utcnow(),
        services=services,
    )
