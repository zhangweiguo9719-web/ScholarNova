"""
分析相关 API 端点
"""

import asyncio
import base64
import logging
import re
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
            "doi": paper.doi,
            "url": paper.url,
            "pdf_url": paper.pdf_url,
            "source": paper.source,
        }

    # 2. 从缓存中查找（遍历所有搜索结果）
    from app.core.cache import CacheManager
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
                                    "doi": p.get("doi"),
                                    "url": p.get("url"),
                                    "pdf_url": p.get("pdf_url"),
                                    "source": p.get("source"),
                                }
                except Exception:
                    pass
    return None


def _arxiv_id(paper_info: dict) -> Optional[str]:
    for value in (paper_info.get("pdf_url"), paper_info.get("url")):
        match = re.search(r"arxiv\.org/(?:abs|pdf)/([^/?#]+)", value or "", re.I)
        if match:
            return match.group(1).removesuffix(".pdf")
    return None


def _document_text(parsed) -> str:
    """Build a section-aware context that covers the paper within a safe budget."""
    budget = 48_000
    parts: list[str] = []
    priority = (
        "abstract", "introduction", "method", "approach", "experiment",
        "result", "discussion", "limitation", "conclusion",
    )
    sections = list(parsed.sections or [])
    sections.sort(key=lambda item: next(
        (index for index, key in enumerate(priority) if key in item.heading.casefold()),
        len(priority),
    ))
    for section in sections:
        value = f"\n### {section.heading}\n{section.text.strip()}"
        remaining = budget - sum(len(item) for item in parts)
        if remaining <= 0:
            break
        parts.append(value[:remaining])
    if not parts:
        parts.append((parsed.full_text or "")[:budget])

    if parsed.figures:
        captions = "\n".join(
            f"- {item.get('caption', '')}" for item in parsed.figures[:20]
        )
        parts.append(f"\n### Figure captions\n{captions}")
    if parsed.tables:
        tables: list[str] = []
        for item in parsed.tables[:8]:
            rows = item.get("rows", [])[:12]
            tables.append(
                f"Table page {item.get('page')}: {item.get('caption', '')}\n"
                + "\n".join(" | ".join(row) for row in rows)
            )
        parts.append("\n### Extracted tables\n" + "\n\n".join(tables))
    return "\n".join(parts)


def _visual_pages(pdf_path, max_pages: int = 3) -> list[str]:
    """Render figure-bearing PDF pages for vision-capable models."""
    try:
        import pymupdf

        doc = pymupdf.open(str(pdf_path))
        candidates: list[int] = []
        for index, page in enumerate(doc):
            text = page.get_text().casefold()
            if page.get_images(full=True) and re.search(r"\b(fig(?:ure)?\.?|table)\s*\d+", text):
                candidates.append(index)
            if len(candidates) >= max_pages:
                break
        images: list[str] = []
        for index in candidates:
            pixmap = doc[index].get_pixmap(matrix=pymupdf.Matrix(0.9, 0.9), alpha=False)
            encoded = base64.b64encode(pixmap.tobytes("jpeg")).decode("ascii")
            images.append(f"data:image/jpeg;base64,{encoded}")
        doc.close()
        return images
    except Exception:
        logger.warning("PDF visual-page rendering failed", exc_info=True)
        return []


async def _load_document_context(paper_info: dict) -> tuple[str, list[str], str]:
    """Fetch and parse a legal OA PDF; never bypass institutional access."""
    from app.config import settings
    from app.services.pdf.fetcher import PDFFetcher
    from app.services.pdf.parser import PDFParser

    fetcher = PDFFetcher(
        unpaywall_email=settings.OPENALEX_EMAIL or settings.CROSSREF_EMAIL
    )
    try:
        fetched = await asyncio.wait_for(
            fetcher.fetch(
                doi=paper_info.get("doi"),
                arxiv_id=_arxiv_id(paper_info),
                pdf_url=paper_info.get("pdf_url"),
                venue=paper_info.get("venue"),
                title=paper_info.get("title"),
            ),
            timeout=45,
        )
        if not fetched.success or not fetched.pdf_path:
            return "", [], "abstract"
        parsed = await asyncio.wait_for(PDFParser().parse(fetched.pdf_path), timeout=30)
        if not parsed or len((parsed.full_text or "").strip()) < 500:
            return "", [], "abstract"
        visuals = await asyncio.to_thread(_visual_pages, fetched.pdf_path)
        return _document_text(parsed), visuals, f"fulltext:{fetched.source}"
    except Exception:
        logger.warning("OA full-text preparation failed; using abstract", exc_info=True)
        return "", [], "abstract"


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

    document_text, visual_pages, coverage = await _load_document_context(paper_info)
    paper_text = f"""
Title: {paper_info['title']}
Authors: {paper_info['authors']}
Year: {paper_info['year']}
Venue: {paper_info['venue']}
Abstract: {paper_info['abstract']}
"""

    abstract = (paper_info.get("abstract") or "").strip()
    if (not abstract or abstract == "N/A") and not document_text:
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

    source_note = (
        "已获取并解析开放获取 PDF 正文、章节、表格和图注"
        if document_text
        else "未取得合法开放全文，本次仅基于元数据和摘要"
    )
    visual_note = (
        f"另附 {len(visual_pages)} 个包含图表的 PDF 页面图像，请结合图像内容分析"
        if visual_pages
        else "未提供可供视觉模型读取的页面图像；只能依据图注和表格文本"
    )
    prompt = f"""你是学术论文分析专家。请根据以下可核验材料，按用户要求进行分析。

## 论文信息
{paper_text}

## 材料覆盖范围
- {source_note}
- {visual_note}
- 获取模式：{coverage}

## 论文正文与图表文本
{document_text or '未取得全文；请严格限制在摘要信息内。'}

## 用户要求
{request.query}

请直接输出结构化的中文分析结果（纯文本，不用JSON格式）。
开头必须用“材料覆盖：全文/摘要”明确本次依据，并说明是否读取了图表页面。
所有结论必须能由上方材料支持；材料未提供时必须明确写“材料未提供此信息”，禁止补写或猜测实验数据、模型结构和结论。
分析应覆盖研究问题、方法、数据与实验设置、主要结果、图表证据、优点、局限及与用户问题的关系。"""

    try:
        user_content: object = prompt
        if visual_pages:
            user_content = [
                {"type": "text", "text": prompt},
                *(
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url, "detail": "low"},
                    }
                    for image_url in visual_pages
                ),
            ]
        messages = [
            {
                "role": "system",
                "content": (
                    "你是严谨的学术论文分析专家。请用中文输出结构化分析，"
                    "区分正文、表格、图像和摘要证据，不得猜测。"
                ),
            },
            {"role": "user", "content": user_content},
        ]
        try:
            response = await llm_gateway.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=3072,
            )
        except Exception:
            if not visual_pages:
                raise
            logger.info(
                "Configured analysis model rejected visual input; retrying with parsed text",
                extra={"paper_id": paper_id},
            )
            response = await llm_gateway.chat(
                messages=[messages[0], {"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=3072,
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
    except RuntimeError:
        logger.exception(
            "Paper analysis LLM request exhausted retries",
            extra={"paper_id": paper_id},
        )
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
