"""
论文相关 API 端点
"""

import csv
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.paper import PaperEntity
from app.schemas.paper import Paper, PaperDetail, PaperQuality

router = APIRouter()
_translation_cache: dict[tuple[str, str], str] = {}


class TranslateRequest(BaseModel):
    text: str
    target_lang: str = "zh"


class TranslateResponse(BaseModel):
    translated: str
    cached: bool = False


class JournalQualityRequest(BaseModel):
    venue: str
    quality: Optional[PaperQuality] = None


class RankingImportRequest(BaseModel):
    filename: str
    content: str


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(req: TranslateRequest) -> TranslateResponse:
    """Translate academic text through the model configured for translation."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="翻译内容不能为空")
    if len(text) > 12_000:
        raise HTTPException(status_code=422, detail="单次翻译不能超过 12000 个字符")

    target_lang = req.target_lang.casefold()
    target = "Chinese (Simplified)" if target_lang.startswith("zh") else "English"
    cache_key = (text, target)
    if cache_key in _translation_cache:
        return TranslateResponse(translated=_translation_cache[cache_key], cached=True)

    from app.services.llm.gateway import LLMGateway

    gateway = LLMGateway(task="translation")
    try:
        result = await gateway.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate the academic text to {target}. Preserve technical terms, "
                        "abbreviations, formulas, and factual meaning. Output only the translation."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        translated = result.strip()
        if not translated:
            raise ValueError("empty translation")
        if len(_translation_cache) >= 256:
            _translation_cache.pop(next(iter(_translation_cache)))
        _translation_cache[cache_key] = translated
        return TranslateResponse(translated=translated)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"翻译失败，请检查翻译模型配置: {type(exc).__name__}",
        ) from exc


@router.post("/journal-quality", response_model=PaperQuality)
async def get_journal_quality(req: JournalQualityRequest) -> PaperQuality:
    """Return licensed imported partitions plus clearly labelled open metrics."""
    venue = req.venue.strip()
    if not venue:
        raise HTTPException(status_code=422, detail="期刊名称不能为空")
    from app.services.journal_quality import lookup_journal_quality

    return await lookup_journal_quality(venue, req.quality)


@router.get("/journal-rankings/status")
async def get_journal_ranking_status() -> dict:
    from app.services.journal_quality import ranking_status

    return ranking_status()


@router.post("/journal-rankings/import")
async def import_journal_rankings(req: RankingImportRequest) -> dict:
    from app.services.journal_quality import import_ranking_content

    try:
        return import_ranking_content(req.content, req.filename)
    except (ValueError, UnicodeError, csv.Error, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{paper_id}", response_model=PaperDetail)
async def get_paper(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
) -> PaperDetail:
    """
    获取论文详情（数据库 + 缓存 fallback）
    """
    # 先从数据库查
    result = await db.execute(select(PaperEntity).where(PaperEntity.id == paper_id))
    paper = result.scalar_one_or_none()

    # 从缓存 fallback
    if not paper:
        from app.core.cache import CacheManager
        cache = CacheManager()
        client = await cache._get_client()
        if hasattr(client, '_store'):
            for key in list(client._store.keys()):
                if "search_results" in key:
                    try:
                        papers_list = await cache.get(key.replace("scholar:", ""))
                        if papers_list:
                            for p in papers_list:
                                if p.get("id") == paper_id:
                                    return PaperDetail(
                                        id=paper_id,
                                        title=p.get("title", ""),
                                        authors=p.get("authors", []),
                                        abstract=p.get("abstract"),
                                        year=p.get("year"),
                                        venue=p.get("venue"),
                                        citation_count=p.get("citation_count", 0),
                                        doi=p.get("doi"),
                                        url=p.get("url"),
                                        pdf_url=p.get("pdf_url"),
                                        source=p.get("source", ""),
                                        is_open_access=p.get("is_open_access", False),
                                        relevance_score=p.get("relevance_score"),
                                        references=[], citations=[],
                                        fields_of_study=[], keywords=[],
                                        publication_date=None, volume=None,
                                        issue=None, pages=None, metadata=None,
                                        created_at=None, updated_at=None,
                                    )
                    except Exception:
                        pass

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return PaperDetail(
        id=paper.id,
        title=paper.title,
        authors=paper.author_names,
        abstract=paper.abstract,
        year=paper.year,
        venue=paper.venue,
        citation_count=paper.citation_count,
        doi=paper.doi,
        url=paper.url,
        pdf_url=paper.pdf_url,
        source=paper.source,
        is_open_access=paper.is_open_access,
        references=[],
        citations=[],
        fields_of_study=paper.fields_of_study or [],
        keywords=paper.keywords or [],
        publication_date=paper.publication_date,
        volume=paper.volume,
        issue=paper.issue,
        pages=paper.pages,
        metadata=paper.extra_metadata or {},
        created_at=paper.created_at,
        updated_at=paper.updated_at,
    )


@router.get("", response_model=list[Paper])
async def list_papers(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[Paper]:
    """
    获取论文列表

    分页获取论文列表
    """
    offset = (page - 1) * page_size
    result = await db.execute(
        select(PaperEntity)
        .order_by(PaperEntity.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    papers = result.scalars().all()

    return [
        Paper(
            id=paper.id,
            title=paper.title,
            authors=paper.author_names,
            abstract=paper.abstract,
            year=paper.year,
            venue=paper.venue,
            citation_count=paper.citation_count,
            doi=paper.doi,
            url=paper.url,
            pdf_url=paper.pdf_url,
            source=paper.source,
            is_open_access=paper.is_open_access,
        )
        for paper in papers
    ]
