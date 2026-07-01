"""
分析相关 API 端点
"""

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.paper import PaperEntity
from app.schemas.query import AnalysisRequest, AnalysisResult
from app.core.rate_limiter import check_rate_limit

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_fallback_analysis(paper_info: dict, query: str) -> str:
    """Build an honest metadata-only analysis when the upstream LLM is unavailable."""
    title = paper_info.get("title") or "未知标题"
    authors = paper_info.get("authors") or "作者信息缺失"
    year = paper_info.get("year") or "年份信息缺失"
    venue = paper_info.get("venue") or "期刊/会议信息缺失"
    abstract = paper_info.get("abstract") or "摘要信息缺失"
    if abstract == "N/A":
        abstract = "摘要信息缺失"

    return f"""## 基础分析（模型服务暂时不可用）

> MiMo 服务本次未能在限定时间内完成请求。以下内容仅根据论文元数据和摘要整理，不包含摘要之外的推断。

### 论文信息
- **标题：** {title}
- **作者：** {authors}
- **年份：** {year}
- **期刊/会议：** {venue}

### 摘要要点
{abstract}

### 与当前研究问题的关系
当前问题为：**{query}**

受模型服务状态限制，本次只能确认上述摘要直接表达的信息。建议稍后点击“全面分析”重试，以获得研究方法、主要发现、优势与局限等深度分析。
"""


def _build_missing_content_analysis(paper_info: dict, query: str) -> str:
    """Avoid speculative analysis when the source provides no abstract or full text."""
    return f"""## 信息不足，未执行推断性分析

当前数据源只提供了论文元数据，没有可供核验的摘要或全文。为避免生成未经论文支持的方法、实验结论和局限性，本次未调用模型进行猜测。

### 可确认信息
- **标题：** {paper_info.get("title") or "未知标题"}
- **作者：** {paper_info.get("authors") or "作者信息缺失"}
- **年份：** {paper_info.get("year") or "年份信息缺失"}
- **期刊/会议：** {paper_info.get("venue") or "期刊/会议信息缺失"}

### 用户问题
{query}

建议优先选择带摘要或全文链接的论文后再执行全面分析。
"""


async def _find_paper_info(paper_id: str, db: AsyncSession) -> Optional[dict]:
    """从数据库或缓存中查找论文信息"""
    # 1. 先从数据库查
    result = await db.execute(select(PaperEntity).where(PaperEntity.id == paper_id))
    paper = result.scalar_one_or_none()
    if paper:
        return {
            "title": paper.title,
            "authors": ", ".join(paper.author_names),
            "year": paper.year,
            "venue": paper.venue,
            "abstract": paper.abstract or "N/A",
        }

    # 2. 从缓存中查找（遍历所有搜索结果）
    from app.core.cache import CacheManager
    import re
    cache = CacheManager()
    # 搜索所有可能的缓存键
    cached_papers = await cache._get_client()
    if hasattr(cached_papers, '_store'):
        # 内存缓存，遍历查找
        for key in list(cached_papers._store.keys()):
            if key.startswith("search_results:"):
                try:
                    papers_list = await cache.get(key.replace("scholar:", ""))
                    if papers_list:
                        for p in papers_list:
                            if p.get("id") == paper_id:
                                return {
                                    "title": p.get("title", "Unknown"),
                                    "authors": ", ".join(p.get("authors", [])),
                                    "year": p.get("year"),
                                    "venue": p.get("venue"),
                                    "abstract": p.get("abstract") or "N/A",
                                }
                except Exception:
                    pass
    return None


@router.post("/{paper_id}/analyze", response_model=AnalysisResult)
async def analyze_paper(
    paper_id: str,
    request: AnalysisRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResult:
    """单篇论文分析"""
    # 速率限制
    rate_limit_response = check_rate_limit(http_request, endpoint_type="analysis")
    if rate_limit_response:
        return rate_limit_response

    # 获取论文（数据库 + 缓存 fallback）
    paper_info = await _find_paper_info(paper_id, db)
    if not paper_info:
        raise HTTPException(status_code=404, detail="Paper not found")

    paper_text = f"""
Title: {paper_info['title']}
Authors: {paper_info['authors']}
Year: {paper_info['year']}
Venue: {paper_info['venue']}
Abstract: {paper_info['abstract']}
"""

    abstract = (paper_info.get("abstract") or "").strip()
    if not abstract or abstract == "N/A":
        return AnalysisResult(
            paper_id=paper_id,
            analysis_type=request.analysis_type,
            summary=_build_missing_content_analysis(paper_info, request.query),
            methodology=None,
            key_findings=[],
            strengths=[],
            weaknesses=[],
            relevance_to_query=None,
            created_at=datetime.utcnow(),
        )

    # 调用 LLM
    from app.services.llm.gateway import LLMGateway
    from app.config import get_model_for_task

    task_config = get_model_for_task("analysis")
    llm_gateway = LLMGateway(provider=task_config["provider"])
    llm_gateway.configure(
        api_key=task_config["api_key"],
        base_url=task_config["base_url"],
        model_name=task_config["model"],
    )

    prompt = f"""你是学术论文分析专家。请根据以下论文信息，按用户要求进行分析。

## 论文信息
{paper_text}

## 用户要求
{request.query}

请直接输出结构化的中文分析结果（纯文本，不用JSON格式）。
所有结论必须能由上方论文信息或摘要支持；没有全文依据时必须明确写“摘要未提供此信息”，禁止补写或猜测实验数据、模型结构和结论。"""

    try:
        response = await llm_gateway.chat(
            messages=[
                {"role": "system", "content": "你是学术论文分析专家。请用中文输出详细的分析结果。不要输出JSON，直接输出结构化的中文分析文本。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        return AnalysisResult(
            paper_id=paper_id,
            analysis_type=request.analysis_type,
            summary=response,
            methodology=None,
            key_findings=[],
            strengths=[],
            weaknesses=[],
            relevance_to_query=None,
            created_at=datetime.utcnow(),
        )
    except RuntimeError as e:
        logger.exception("Paper analysis LLM request exhausted retries", extra={"paper_id": paper_id})
        return AnalysisResult(
            paper_id=paper_id,
            analysis_type=request.analysis_type,
            summary=_build_fallback_analysis(paper_info, request.query),
            methodology=None,
            key_findings=[],
            strengths=[],
            weaknesses=[],
            relevance_to_query=None,
            created_at=datetime.utcnow(),
        )
    except Exception as e:
        logger.exception("Paper analysis failed", extra={"paper_id": paper_id})
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
