"""
证据相关 API 端点
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.evidence import EvidenceSpan as EvidenceSpanModel
from app.schemas.evidence import EvidenceResponse, EvidenceSpan

router = APIRouter()


@router.get("/{run_id}/{paper_id}", response_model=EvidenceResponse)
async def get_evidence(
    run_id: str,
    paper_id: str,
    db: AsyncSession = Depends(get_db),
) -> EvidenceResponse:
    """
    获取证据

    获取指定论文在特定搜索运行中的证据片段
    """
    result = await db.execute(
        select(EvidenceSpanModel).where(
            EvidenceSpanModel.search_run_id == run_id,
            EvidenceSpanModel.paper_id == paper_id,
        )
    )
    evidence_spans = result.scalars().all()

    return EvidenceResponse(
        paper_id=paper_id,
        run_id=run_id,
        evidence_spans=[
            EvidenceSpan(
                id=span.id,
                run_id=span.search_run_id,
                paper_id=span.paper_id,
                claim=span.constraint_key or "",
                evidence_text=span.quote_text,
                verdict=span.verdict,
                confidence=span.confidence,
                page_number=span.paragraph_index,
                section=span.section_name,
                context=None,
                llm_model=span.llm_model,
                created_at=span.created_at,
            )
            for span in evidence_spans
        ],
    )
