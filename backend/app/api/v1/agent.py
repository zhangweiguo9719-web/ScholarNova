"""Grounded research-assistant prototype."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_model_for_task
from app.core.rate_limiter import check_rate_limit
from app.database import get_db
from app.models.knowledge import KnowledgeBase
from app.models.paper import PaperChunk, PaperEntity
from app.services.features.knowledge import ensure_knowledge_features
from app.services.inference import (
    AllModelsUnavailableError,
    build_retrieval_fallback,
    chat_with_fallback,
    verify_answer_citations,
)
from app.services.integrations.zotero import ZoteroLocalClient
from app.services.llm.gateway import LLMGateway
from app.services.retrieval.adapters import from_knowledge, from_paper, from_zotero
from app.services.retrieval.contracts import RetrievalChunk
from app.services.retrieval.hybrid import rank_chunks_hybrid

router = APIRouter()


class AgentMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class AgentChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    history: list[AgentMessage] = Field(default_factory=list, max_length=8)
    use_knowledge: bool = True
    use_zotero: bool = True


class AgentCitation(BaseModel):
    id: str
    source: Literal["knowledge", "paper", "zotero"]
    title: str
    doi: str | None = None
    item_id: str | None = None
    url: str | None = None
    section: str | None = None
    page: int | None = None
    chunk_index: int | None = None


class AgentToolStep(BaseModel):
    tool: str
    status: Literal["completed", "skipped", "unavailable"]
    count: int = 0
    detail: str


class AgentModelAttempt(BaseModel):
    role: Literal["primary", "fallback"]
    provider: str
    model: str
    status: Literal["completed", "unavailable"]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0
    error_type: str | None = None


class AgentChatResponse(BaseModel):
    answer: str
    citations: list[AgentCitation]
    tool_steps: list[AgentToolStep]
    response_type: Literal["research", "product_help"] = "research"
    provider: str | None = None
    model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    retrieval_tokens: int = 0
    total_tokens: int = 0
    retrieval_mode: Literal["bm25", "hybrid"] = "bm25"
    inference_mode: Literal["model", "deterministic_fallback", "none"] = "none"
    verification_status: Literal[
        "verified", "partial", "failed", "not_applicable"
    ] = "not_applicable"
    citation_coverage: float = 0.0
    uncited_claim_count: int = 0
    invalid_citation_ids: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    model_fallback_used: bool = False
    model_route: Literal["primary", "fallback", "deterministic", "none"] = "none"
    model_attempts: list[AgentModelAttempt] = Field(default_factory=list)
    grounded: bool = True
    created_at: datetime


_EN_TERM = re.compile(r"[a-z0-9][a-z0-9+._-]{1,}")
_ZH_RUN = re.compile(r"[\u4e00-\u9fff]{2,}")
_ZH_STOP = {"什么", "如何", "哪些", "是否", "这个", "研究", "论文", "文献", "可以"}
_EN_STOP = {
    "about", "appear", "based", "compare", "from", "have", "literature",
    "papers", "research", "show", "summarize", "that", "the", "these",
    "what", "which", "with", "zotero",
}

_PRODUCT_HELP_PATTERNS = (
    re.compile(r"(?:这个|目前|scholarnova).{0,8}(?:智能体|平台|系统).{0,8}(?:怎么|如何|怎样).{0,4}(?:用|使用|操作)"),
    re.compile(r"(?:怎么|如何|怎样).{0,6}(?:使用|操作).{0,8}(?:这个)?(?:智能体|scholarnova|平台|系统)"),
    re.compile(r"(?:智能体|scholarnova|平台|系统).{0,8}(?:使用方法|操作流程|使用说明|功能介绍)"),
    re.compile(r"how (?:do i|to|can i) use (?:this |the )?(?:assistant|scholarnova|platform|app)"),
    re.compile(r"(?:scholarnova|this assistant).{0,12}(?:user guide|how .*works|what can .*do)"),
)


def _is_product_help(question: str) -> bool:
    normalized = " ".join(question.casefold().split())
    return any(pattern.search(normalized) for pattern in _PRODUCT_HELP_PATTERNS)


def _product_help_answer(question: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", question):
        return (
            "目前这个智能体的使用方式如下：\n\n"
            "1. 准备材料：先在“搜索”页检索论文并完成分析；导入过的授权 PDF 会建立本地全文检索片段，需要长期使用的结论还可以保存到 ScholarNova 知识库；也可以在“设置”中连接已经启动的本机 Zotero。\n"
            "2. 选择来源：进入“智能体”页面后，按需开启“ScholarNova 知识库”和“本机 Zotero”。未连接 Zotero 时可以只使用知识库。\n"
            "3. 提出科研问题：适合询问现有材料的研究共识、方法差异、研究空白、证据对比和可验证研究问题。问题越具体，检索越准确。\n"
            "4. 核验回答：科研回答中的 [S1]、[S2] 对应下方引用材料。重要结论仍应返回原论文核验。\n"
            "5. 注意边界：智能体只依据实际检索到的本地材料回答；材料不足时会明确说明，不会自动修改 Zotero，也不会用无关论文拼凑答案。\n\n"
            "可以从这些问题开始：\n"
            "• 总结知识库中关于某个主题的主要研究空白。\n"
            "• 比较 Zotero 文献中两种方法的证据与局限。\n"
            "• 基于现有材料提出三个可验证的研究问题。"
        )
    return (
        "Here is how to use the assistant:\n\n"
        "1. Prepare evidence: analyze papers from Search; authorized imported PDFs are indexed locally, useful findings can be saved to the ScholarNova knowledge base, and a running local Zotero can be connected from Settings.\n"
        "2. Choose sources: enable the ScholarNova knowledge base, local Zotero, or both on the Assistant page.\n"
        "3. Ask a focused research question about consensus, method differences, research gaps, evidence, or testable next steps.\n"
        "4. Verify the answer: [S1] and [S2] point to the source cards shown below the response. Check important claims against the original paper.\n"
        "5. Know the boundary: the assistant answers only from retrieved local evidence, reports insufficient material, and never modifies Zotero automatically."
    )


def _query_terms(question: str) -> list[str]:
    lowered = question.casefold()
    terms = {term for term in _EN_TERM.findall(lowered) if term not in _EN_STOP}
    for run in _ZH_RUN.findall(lowered):
        if run not in _ZH_STOP:
            terms.add(run)
        for size in (2, 3, 4):
            for index in range(max(0, len(run) - size + 1)):
                token = run[index:index + size]
                if token not in _ZH_STOP:
                    terms.add(token)
    return sorted(terms, key=len, reverse=True)[:48]


def _zotero_queries(question: str) -> list[str]:
    """Build a small fallback sequence for Zotero's strict quick-search syntax."""
    queries = [question.strip()]
    queries.extend(
        term
        for term in _EN_TERM.findall(question.casefold())
        if term not in _EN_STOP
    )
    queries.extend(term for term in _query_terms(question) if len(term) >= 3)
    return list(dict.fromkeys(query for query in queries if query))[:4]


async def _knowledge_candidates(
    db: AsyncSession,
) -> list[RetrievalChunk]:
    result = await db.execute(
        select(KnowledgeBase).order_by(KnowledgeBase.updated_at.desc()).limit(80)
    )
    items = list(result.scalars().all())
    if not items:
        return []
    chunks = await ensure_knowledge_features(db, items)
    item_by_id = {item.id: item for item in items}
    return [
        from_knowledge(item_by_id[chunk.knowledge_id], chunk)
        for chunk in chunks
        if chunk.knowledge_id in item_by_id
    ]


async def _paper_candidates(db: AsyncSession) -> list[RetrievalChunk]:
    result = await db.execute(
        select(PaperEntity, PaperChunk)
        .join(PaperChunk, PaperChunk.paper_id == PaperEntity.id)
        .order_by(PaperChunk.created_at.desc(), PaperChunk.position)
        .limit(600)
    )
    return [from_paper(paper, chunk) for paper, chunk in result.all()]


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_research_agent(
    request: AgentChatRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
) -> AgentChatResponse:
    """Answer with traceable evidence gathered from local research tools."""
    limited = check_rate_limit(http_request, endpoint_type="agent")
    if limited:
        return limited

    if _is_product_help(request.question):
        return AgentChatResponse(
            answer=_product_help_answer(request.question),
            citations=[],
            tool_steps=[
                AgentToolStep(
                    tool="product_help",
                    status="completed",
                    count=1,
                    detail="根据 ScholarNova 内置使用指南回答，未调用论文检索或模型",
                )
            ],
            response_type="product_help",
            grounded=False,
            created_at=datetime.now(),
        )

    contexts: list[str] = []
    evidence_items: list[tuple[str, str, str]] = []
    citations: list[AgentCitation] = []
    steps: list[AgentToolStep] = []
    knowledge_candidates: list[RetrievalChunk] = []
    paper_candidates: list[RetrievalChunk] = []
    zotero_candidates: list[RetrievalChunk] = []
    zotero_status: Literal["completed", "skipped", "unavailable"] = "skipped"
    zotero_detail = "用户未启用 Zotero 检索"

    if request.use_knowledge:
        knowledge_candidates = await _knowledge_candidates(db)
        paper_candidates = await _paper_candidates(db)

    if request.use_zotero:
        try:
            zotero_client = ZoteroLocalClient()
            zotero_items: list[dict[str, Any]] = []
            for zotero_query in _zotero_queries(request.question):
                zotero_items = await zotero_client.search_items(zotero_query, limit=4)
                if zotero_items:
                    break
            zotero_candidates = [
                candidate
                for item in zotero_items
                if (candidate := from_zotero(item)) is not None
            ]
            zotero_status = "completed"
            zotero_detail = f"从本机 Zotero 获得 {len(zotero_candidates)} 个候选片段"
        except Exception:
            zotero_status = "unavailable"
            zotero_detail = "Zotero 未启动或本地 API 尚未启用，已继续使用其他材料"

    retrieval = await rank_chunks_hybrid(
        db,
        request.question,
        [*knowledge_candidates, *paper_candidates, *zotero_candidates],
        limit=6,
        max_per_document=2,
    )
    ranked = retrieval.ranked
    selected_knowledge = sum(item.chunk.source == "knowledge" for item in ranked)
    selected_papers = sum(item.chunk.source == "paper" for item in ranked)
    selected_zotero = sum(item.chunk.source == "zotero" for item in ranked)
    steps.append(
        AgentToolStep(
            tool="semantic_retrieval",
            status=retrieval.semantic_status,
            count=len(ranked) if retrieval.mode == "hybrid" else 0,
            detail=retrieval.detail,
        )
    )
    ranking_name = "BM25 + Embedding RRF" if retrieval.mode == "hybrid" else "BM25"
    steps.append(
        AgentToolStep(
            tool="paper_fulltext_search",
            status="completed" if request.use_knowledge else "skipped",
            count=selected_papers,
            detail=(
                f"{ranking_name} 从 {len(paper_candidates)} 个已解析 PDF 片段中选择了 "
                f"{selected_papers} 个相关片段"
                if request.use_knowledge
                else "用户未启用 ScholarNova 本地材料检索"
            ),
        )
    )
    steps.append(
        AgentToolStep(
            tool="knowledge_search",
            status="completed" if request.use_knowledge else "skipped",
            count=selected_knowledge,
            detail=(
                f"{ranking_name} 从 {len(knowledge_candidates)} 个知识片段中选择了 "
                f"{selected_knowledge} 个相关片段"
                if request.use_knowledge
                else "用户未启用知识库检索"
            ),
        )
    )
    steps.append(
        AgentToolStep(
            tool="zotero_search",
            status=zotero_status,
            count=selected_zotero,
            detail=(
                f"{zotero_detail}，统一排序后保留 {selected_zotero} 个"
                if zotero_status == "completed"
                else zotero_detail
            ),
        )
    )

    for ranked_item in ranked:
        chunk = ranked_item.chunk
        metadata = chunk.metadata
        source_id = f"S{len(citations) + 1}"
        if chunk.source == "knowledge":
            contexts.append(
                f"[{source_id}] ScholarNova 知识库\n"
                f"标题：{chunk.title}\n分类：{metadata.get('category') or '未分类'}\n"
                f"特征版本：{chunk.feature_version}\n片段：{chunk.position + 1}\n"
                f"内容：{chunk.content}\n"
                f"研究点：{metadata.get('research_points') or '未记录'}"
            )
            citations.append(
                AgentCitation(
                    id=source_id,
                    source="knowledge",
                    title=chunk.title,
                    doi=metadata.get("doi"),
                    item_id=metadata.get("knowledge_id"),
                    chunk_index=chunk.position + 1,
                )
            )
        elif chunk.source == "paper":
            location = metadata.get("heading") or metadata.get("kind") or "正文"
            if metadata.get("page") is not None:
                location = f"{location}，第 {metadata['page']} 页"
            contexts.append(
                f"[{source_id}] ScholarNova 已解析 PDF\n"
                f"标题：{chunk.title}\n位置：{location}\n"
                f"特征版本：{chunk.feature_version}\n内容：{chunk.content}"
            )
            citations.append(
                AgentCitation(
                    id=source_id,
                    source="paper",
                    title=chunk.title,
                    doi=metadata.get("doi"),
                    item_id=metadata.get("paper_id"),
                    url=metadata.get("url"),
                    section=metadata.get("heading") or metadata.get("kind"),
                    page=metadata.get("page"),
                )
            )
        elif chunk.source == "zotero":
            contexts.append(
                f"[{source_id}] Zotero 本地文献\n"
                f"标题：{chunk.title}\n作者：{metadata.get('authors') or '未知'}\n"
                f"日期：{metadata.get('date') or '未知'}\n"
                f"期刊/会议：{metadata.get('venue') or '未知'}\n"
                f"摘要：{chunk.content or '摘要暂缺，请回到原文核验'}"
            )
            citations.append(
                AgentCitation(
                    id=source_id,
                    source="zotero",
                    title=chunk.title,
                    doi=metadata.get("doi"),
                    item_id=metadata.get("item_id"),
                    url=metadata.get("url"),
                )
            )
        evidence_items.append((source_id, chunk.title, chunk.content))

    steps.append(
        AgentToolStep(
            tool="evidence_pack",
            status="completed" if contexts else "skipped",
            count=len(contexts),
            detail=(
                f"已打包 {len(contexts)} 个带稳定来源编号的证据片段"
                if contexts
                else "没有检索到可打包证据"
            ),
        )
    )

    if not contexts:
        return AgentChatResponse(
            answer=(
                "当前没有找到可引用的本地材料。请先将论文保存到 ScholarNova 知识库，"
                "导入有权使用的 PDF，或启动 Zotero 并在“设置 → 高级”中允许本机应用与 Zotero 通讯。"
            ),
            citations=[],
            tool_steps=steps,
            retrieval_tokens=retrieval.embedding_tokens,
            total_tokens=retrieval.embedding_tokens,
            retrieval_mode=retrieval.mode,
            grounded=False,
            created_at=datetime.now(),
        )

    model_config = get_model_for_task("assistant")
    source_text = "\n\n".join(contexts)
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "你是 ScholarNova 科研问答智能体。只能依据提供的本地材料回答，"
                "每个事实性结论必须在句末标注 [S1] 这类来源编号。"
                "材料不足时明确说明，不得虚构论文、实验结果或引用。"
                "回答使用与用户问题相同的语言，并使用便于直接阅读的纯文本，"
                "不要使用 Markdown 加粗或标题符号。"
            ),
        }
    ]
    messages.extend(message.model_dump() for message in request.history[-6:])
    messages.append(
        {
            "role": "user",
            "content": (
                f"用户问题：{request.question}\n\n"
                f"可引用材料：\n{source_text}\n\n"
                "请先给出直接结论，再给出证据和仍需确认的问题。"
            ),
        }
    )
    inference_mode: Literal["model", "deterministic_fallback"] = "model"
    fallback_used = False
    model_fallback_used = False
    model_route: Literal["primary", "fallback", "deterministic"] = "primary"
    model_attempts: list[dict[str, Any]] = []
    try:
        routed = await chat_with_fallback(
            task="assistant",
            messages=messages,
            temperature=0.2,
            max_tokens=1800,
            gateway_factory=LLMGateway,
        )
        answer = routed.content
        usage = routed.usage
        model_config = routed.profile
        model_fallback_used = routed.fallback_used
        model_route = "fallback" if routed.fallback_used else "primary"
        model_attempts = [attempt.to_dict() for attempt in routed.attempts]
        steps.append(
            AgentToolStep(
                tool="answer_generation",
                status="completed",
                count=1,
                detail=(
                    f"主模型不可用，已由备用模型 {model_config.get('provider')}/"
                    f"{model_config.get('model')} 生成回答"
                    if routed.fallback_used
                    else f"使用主模型 {model_config.get('provider')}/"
                    f"{model_config.get('model')} 生成回答"
                ),
            )
        )
    except AllModelsUnavailableError as exc:
        answer = build_retrieval_fallback(request.question, evidence_items)
        inference_mode = "deterministic_fallback"
        fallback_used = True
        model_route = "deterministic"
        usage = exc.usage
        model_attempts = [attempt.to_dict() for attempt in exc.attempts]
        steps.append(
            AgentToolStep(
                tool="answer_generation",
                status="unavailable",
                count=0,
                detail="回答模型暂时不可用，已返回确定性检索证据，不中断本次问答",
            )
        )

    verification = verify_answer_citations(
        answer,
        [citation.id for citation in citations],
        question=request.question,
    )
    steps.append(
        AgentToolStep(
            tool="answer_verification",
            status="completed",
            count=verification.cited_claim_count,
            detail=verification.detail,
        )
    )
    return AgentChatResponse(
        answer=answer.strip(),
        citations=citations,
        tool_steps=steps,
        provider=model_config.get("provider"),
        model=model_config.get("model"),
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        retrieval_tokens=retrieval.embedding_tokens,
        total_tokens=usage["total_tokens"] + retrieval.embedding_tokens,
        retrieval_mode=retrieval.mode,
        inference_mode=inference_mode,
        verification_status=verification.status,
        citation_coverage=verification.coverage,
        uncited_claim_count=verification.uncited_claim_count,
        invalid_citation_ids=list(verification.invalid_citation_ids),
        fallback_used=fallback_used,
        model_fallback_used=model_fallback_used,
        model_route=model_route,
        model_attempts=model_attempts,
        grounded=verification.status == "verified",
        created_at=datetime.now(),
    )
