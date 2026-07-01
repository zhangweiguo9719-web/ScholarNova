"""
论文相关 API 端点
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.paper import PaperEntity
from app.schemas.paper import Paper, PaperDetail

router = APIRouter()


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


# ---- 翻译 ----

from pydantic import BaseModel as PydanticBaseModel

class TranslateRequest(PydanticBaseModel):
    text: str
    target_lang: str = "zh"

class TranslateResponse(PydanticBaseModel):
    translated: str

@router.post("/translate", response_model=TranslateResponse)
async def translate_text(req: TranslateRequest):
    """调用 LLM 翻译文本"""
    from app.services.llm.gateway import LLMGateway
    from app.config import settings

    # 如果文本全是中文，翻译成英文
    has_cjk = any('一' <= c <= '鿿' for c in req.text)
    if has_cjk:
        target = "English"
    else:
        target = "Chinese (Simplified)"

    gateway = LLMGateway()
    gateway.configure(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
        model_name=settings.OPENAI_DEFAULT_MODEL,
    )

    try:
        result = await gateway.chat(
            messages=[
                {"role": "system", "content": f"You are a professional academic translator. Translate the following text to {target}. Keep the academic tone. Output ONLY the translation, no explanation."},
                {"role": "user", "content": req.text},
            ],
            temperature=0.3,
            max_tokens=2048,
        )
        return TranslateResponse(translated=result.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")
