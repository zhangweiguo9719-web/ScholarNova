"""
分析相关 API 端点
"""

import asyncio
import base64
import hashlib
import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.paper import PaperEntity
from app.schemas.query import AnalysisRequest, AnalysisResult
from app.core.rate_limiter import check_rate_limit

router = APIRouter()
logger = logging.getLogger(__name__)
MAX_PDF_UPLOAD_SIZE = 50 * 1024 * 1024


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
        caption_pages: list[int] = []
        image_pages: list[int] = []
        for index, page in enumerate(doc):
            text = page.get_text().casefold()
            if re.search(r"(?:\b(?:fig(?:ure)?\.?|table)|[图表])\s*[0-9一二三四五六七八九十]+", text):
                caption_pages.append(index)
            elif page.get_images(full=True):
                image_pages.append(index)
        # Caption-bearing pages also cover vector diagrams, which do not appear
        # in PyMuPDF's raster-image list. Raster pages are only a fallback.
        candidates = (caption_pages + image_pages)[:max_pages]
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


def _uploaded_pdf_path(paper_id: str):
    """Return a stable, non-user-controlled path for an imported paper PDF."""
    from app.config import runtime_path

    directory = runtime_path("fulltext")
    directory.mkdir(parents=True, exist_ok=True)
    filename = hashlib.sha256(paper_id.encode("utf-8")).hexdigest() + ".pdf"
    return directory / filename


async def _load_document_context(
    paper_id: str, paper_info: dict
) -> tuple[str, list[str], str, Optional[str]]:
    """Fetch and parse a legal OA PDF; never bypass institutional access."""
    from app.config import settings
    from app.services.pdf.fetcher import PDFFetcher
    from app.services.pdf.parser import PDFParser

    imported_path = _uploaded_pdf_path(paper_id)
    pdf_path = imported_path if imported_path.exists() else None
    source = "uploaded" if pdf_path else ""
    fetch_error: Optional[str] = None
    try:
        if not pdf_path:
            fetcher = PDFFetcher(
                unpaywall_email=settings.OPENALEX_EMAIL or settings.CROSSREF_EMAIL,
                semantic_scholar_api_key=settings.SEMANTIC_SCHOLAR_API_KEY,
                openalex_email=settings.OPENALEX_EMAIL,
                openalex_api_key=settings.OPENALEX_API_KEY,
            )
            fetched = await asyncio.wait_for(
                fetcher.fetch(
                    doi=paper_info.get("doi"),
                    arxiv_id=_arxiv_id(paper_info),
                    pdf_url=paper_info.get("pdf_url"),
                    venue=paper_info.get("venue"),
                    title=paper_info.get("title"),
                ),
                timeout=75,
            )
            if not fetched.success or not fetched.pdf_path:
                return "", [], "abstract", fetched.error
            pdf_path = fetched.pdf_path
            source = fetched.source

        parsed = await asyncio.wait_for(PDFParser().parse(pdf_path), timeout=30)
        if not parsed or len((parsed.full_text or "").strip()) < 500:
            return "", [], "abstract", "PDF 可打开，但未提取到足够的正文文字"
        visuals = await asyncio.to_thread(_visual_pages, pdf_path)
        return _document_text(parsed), visuals, f"fulltext:{source}", None
    except Exception as exc:
        logger.warning("OA full-text preparation failed; using abstract", exc_info=True)
        fetch_error = f"全文解析失败：{exc}"
        return "", [], "abstract", fetch_error


@router.get("/{paper_id}/fulltext/status")
async def get_fulltext_status(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Report whether a user-imported PDF is ready for full-text analysis."""
    if not await _find_paper_info(paper_id, db):
        raise HTTPException(status_code=404, detail="Paper not found")
    pdf_path = _uploaded_pdf_path(paper_id)
    return {
        "available": pdf_path.exists(),
        "source": "uploaded" if pdf_path.exists() else None,
        "file_size": pdf_path.stat().st_size if pdf_path.exists() else 0,
    }


@router.post("/{paper_id}/fulltext")
async def upload_fulltext(
    paper_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Persist a user-provided PDF so the analysis Agent can read its full text."""
    if not await _find_paper_info(paper_id, db):
        raise HTTPException(status_code=404, detail="Paper not found")
    content = await file.read(MAX_PDF_UPLOAD_SIZE + 1)
    await file.close()
    if len(content) > MAX_PDF_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="PDF 不能超过 50 MB")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="文件不是有效的 PDF")

    try:
        import pymupdf

        document = pymupdf.open(stream=content, filetype="pdf")
        page_count = document.page_count
        document.close()
        if page_count < 1:
            raise ValueError("PDF 没有页面")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF 无法解析：{exc}") from exc

    pdf_path = _uploaded_pdf_path(paper_id)
    temporary_path = pdf_path.with_suffix(".tmp")
    temporary_path.write_bytes(content)
    temporary_path.replace(pdf_path)
    return {
        "available": True,
        "source": "uploaded",
        "file_size": len(content),
        "page_count": page_count,
    }


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

    document_text, visual_pages, coverage, document_error = await _load_document_context(
        paper_id, paper_info
    )
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
            document_coverage="abstract",
            document_source=None,
            document_error=document_error,
            visual_pages_read=0,
            model_completed=False,
            created_at=datetime.utcnow(),
        )

    # 调用 LLM
    from app.services.llm.gateway import LLMGateway
    from app.config import get_model_for_task

    analysis_config = get_model_for_task("analysis")
    analysis_gateway = LLMGateway(provider=analysis_config["provider"])
    analysis_gateway.configure(
        api_key=analysis_config["api_key"],
        base_url=analysis_config["base_url"],
        model_name=analysis_config["model"],
    )

    visual_gateway = analysis_gateway
    if visual_pages:
        vision_config = get_model_for_task("vision")
        visual_gateway = LLMGateway(provider=vision_config["provider"])
        visual_gateway.configure(
            api_key=vision_config["api_key"],
            base_url=vision_config["base_url"],
            model_name=vision_config["model"],
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
        used_visual_pages = len(visual_pages)
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
            response_gateway = visual_gateway
            response = await visual_gateway.chat(
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
            used_visual_pages = 0
            response_gateway = analysis_gateway
            text_only_prompt = prompt.replace(
                visual_note,
                "当前配置的模型未接受页面图像；本次仅依据正文、图注和表格文本分析",
            )
            response = await analysis_gateway.chat(
                messages=[messages[0], {"role": "user", "content": text_only_prompt}],
                temperature=0.3,
                max_tokens=3072,
            )

        usage = response_gateway.last_usage
        return AnalysisResult(
            paper_id=paper_id,
            analysis_type=request.analysis_type,
            summary=response,
            methodology=None,
            key_findings=[],
            strengths=[],
            weaknesses=[],
            relevance_to_query=None,
            document_coverage="fulltext" if document_text else "abstract",
            document_source=coverage,
            document_error=document_error,
            visual_pages_read=used_visual_pages,
            model_completed=True,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            total_tokens=usage["total_tokens"],
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
            document_coverage="fulltext" if document_text else "abstract",
            document_source=coverage,
            document_error=document_error or "全文材料已准备，但模型服务未完成本次分析",
            visual_pages_read=0,
            model_completed=False,
            created_at=datetime.utcnow(),
        )
    except Exception as e:
        logger.exception("Paper analysis failed", extra={"paper_id": paper_id})
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
