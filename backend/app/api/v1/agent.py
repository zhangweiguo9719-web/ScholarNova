"""Grounded research-assistant prototype."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_model_for_task
from app.core.rate_limiter import check_rate_limit
from app.database import get_db
from app.models.knowledge import KnowledgeBase, KnowledgeChunk
from app.services.features.knowledge import ensure_knowledge_features
from app.services.integrations.zotero import ZoteroLocalClient
from app.services.llm.gateway import LLMGateway

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
    source: Literal["knowledge", "zotero"]
    title: str
    doi: str | None = None
    item_id: str | None = None
    url: str | None = None


class AgentToolStep(BaseModel):
    tool: str
    status: Literal["completed", "skipped", "unavailable"]
    count: int = 0
    detail: str


class AgentChatResponse(BaseModel):
    answer: str
    citations: list[AgentCitation]
    tool_steps: list[AgentToolStep]
    response_type: Literal["research", "product_help"] = "research"
    provider: str | None = None
    model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
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
            "1. 准备材料：先在“搜索”页检索论文并完成分析，把需要长期使用的内容保存到 ScholarNova 知识库；也可以在“设置”中连接已经启动的本机 Zotero。\n"
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
        "1. Prepare evidence: analyze papers from Search and save useful findings to the ScholarNova knowledge base, or connect a running local Zotero from Settings.\n"
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


@dataclass(frozen=True)
class KnowledgeMaterial:
    knowledge: KnowledgeBase
    chunk: KnowledgeChunk
    score: int


def _knowledge_chunk_score(
    item: KnowledgeBase,
    chunk: KnowledgeChunk,
    terms: list[str],
) -> int:
    title = (item.title or "").casefold()
    category = (item.category or "").casefold()
    content = (chunk.content or "").casefold()
    tags = " ".join(item.tags or []).casefold()
    research_points = " ".join(item.research_points or []).casefold()
    return sum(
        8 * (term in title)
        + 4 * (term in category)
        + 3 * (term in tags)
        + 3 * (term in research_points)
        + 2 * min(3, content.count(term))
        for term in terms
    )


async def _knowledge_materials(
    db: AsyncSession,
    question: str,
    *,
    limit: int = 4,
) -> list[KnowledgeMaterial]:
    result = await db.execute(
        select(KnowledgeBase).order_by(KnowledgeBase.updated_at.desc()).limit(80)
    )
    items = list(result.scalars().all())
    if not items:
        return []
    terms = _query_terms(question)
    chunks = await ensure_knowledge_features(db, items)
    item_by_id = {item.id: item for item in items}
    ranked = sorted(
        (
            KnowledgeMaterial(
                knowledge=item_by_id[chunk.knowledge_id],
                chunk=chunk,
                score=_knowledge_chunk_score(item_by_id[chunk.knowledge_id], chunk, terms),
            )
            for chunk in chunks
            if chunk.knowledge_id in item_by_id
        ),
        key=lambda material: (
            material.score,
            str(material.knowledge.updated_at or ""),
            -material.chunk.position,
        ),
        reverse=True,
    )
    selected: list[KnowledgeMaterial] = []
    per_item: dict[str, int] = {}
    for material in ranked:
        if material.score <= 0:
            continue
        knowledge_id = material.knowledge.id
        if per_item.get(knowledge_id, 0) >= 2:
            continue
        selected.append(material)
        per_item[knowledge_id] = per_item.get(knowledge_id, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def _zotero_author_names(data: dict[str, Any]) -> str:
    names: list[str] = []
    for creator in data.get("creators") or []:
        if not isinstance(creator, dict):
            continue
        name = str(creator.get("name") or "").strip()
        if not name:
            name = " ".join(
                part
                for part in (
                    str(creator.get("firstName") or "").strip(),
                    str(creator.get("lastName") or "").strip(),
                )
                if part
            )
        if name:
            names.append(name)
    return ", ".join(names[:8])


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_research_agent(
    request: AgentChatRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
) -> AgentChatResponse:
    """Answer with traceable evidence gathered from local research tools."""
    limited = check_rate_limit(http_request, endpoint_type="analysis")
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
    citations: list[AgentCitation] = []
    steps: list[AgentToolStep] = []

    if request.use_knowledge:
        knowledge_materials = await _knowledge_materials(db, request.question)
        for material in knowledge_materials:
            item = material.knowledge
            chunk = material.chunk
            source_id = f"S{len(citations) + 1}"
            contexts.append(
                f"[{source_id}] ScholarNova 知识库\n"
                f"标题：{item.title}\n分类：{item.category}\n"
                f"特征版本：{chunk.feature_version}\n片段：{chunk.position + 1}\n"
                f"内容：{chunk.content}\n"
                f"研究点：{'；'.join(item.research_points or [])[:500]}"
            )
            citations.append(
                AgentCitation(
                    id=source_id,
                    source="knowledge",
                    title=item.source_paper_title or item.title,
                    doi=item.source_paper_doi,
                    item_id=item.id,
                )
            )
        steps.append(
            AgentToolStep(
                tool="knowledge_search",
                status="completed",
                count=len(knowledge_materials),
                detail=(
                    f"从 ScholarNova 知识特征层选择了 {len(knowledge_materials)} 个相关片段，"
                    f"覆盖 {len({material.knowledge.id for material in knowledge_materials})} 条知识记录"
                ),
            )
        )
    else:
        steps.append(
            AgentToolStep(
                tool="knowledge_search",
                status="skipped",
                detail="用户未启用知识库检索",
            )
        )

    if request.use_zotero:
        try:
            zotero_client = ZoteroLocalClient()
            zotero_items: list[dict[str, Any]] = []
            for zotero_query in _zotero_queries(request.question):
                zotero_items = await zotero_client.search_items(zotero_query, limit=4)
                if zotero_items:
                    break
            for item in zotero_items:
                data = item.get("data") or {}
                title = str(data.get("title") or "未命名 Zotero 文献").strip()
                source_id = f"S{len(citations) + 1}"
                contexts.append(
                    f"[{source_id}] Zotero 本地文献\n"
                    f"标题：{title}\n作者：{_zotero_author_names(data)}\n"
                    f"日期：{data.get('date') or '未知'}\n"
                    f"期刊/会议：{data.get('publicationTitle') or data.get('conferenceName') or '未知'}\n"
                    f"摘要：{str(data.get('abstractNote') or '')[:1400]}"
                )
                citations.append(
                    AgentCitation(
                        id=source_id,
                        source="zotero",
                        title=title,
                        doi=str(data.get("DOI") or "").strip() or None,
                        item_id=str(item.get("key") or "").strip() or None,
                        url=str(data.get("url") or "").strip() or None,
                    )
                )
            steps.append(
                AgentToolStep(
                    tool="zotero_search",
                    status="completed",
                    count=len(zotero_items),
                    detail=f"从本机 Zotero 选择了 {len(zotero_items)} 篇相关文献",
                )
            )
        except Exception:
            steps.append(
                AgentToolStep(
                    tool="zotero_search",
                    status="unavailable",
                    detail="Zotero 未启动或本地 API 尚未启用，已继续使用其他材料",
                )
            )
    else:
        steps.append(
            AgentToolStep(
                tool="zotero_search",
                status="skipped",
                detail="用户未启用 Zotero 检索",
            )
        )

    if not contexts:
        return AgentChatResponse(
            answer=(
                "当前没有找到可引用的本地材料。请先将论文保存到 ScholarNova 知识库，"
                "或启动 Zotero 并在“设置 → 高级”中允许本机应用与 Zotero 通讯。"
            ),
            citations=[],
            tool_steps=steps,
            grounded=False,
            created_at=datetime.now(),
        )

    model_config = get_model_for_task("assistant")
    gateway = LLMGateway(task="assistant")
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
    try:
        request_options: dict[str, Any] = {}
        if model_config.get("provider") == "zhipu":
            # Preserve the answer budget for visible grounded output instead
            # of letting GLM reasoning consume it before the final response.
            request_options["extra_body"] = {"thinking": {"type": "disabled"}}
        answer = await gateway.chat(
            messages=messages,
            temperature=0.2,
            max_tokens=1800,
            **request_options,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="科研问答模型暂时不可用，请检查模型配置后重试。",
        ) from exc

    usage = gateway.last_usage
    return AgentChatResponse(
        answer=answer.strip(),
        citations=citations,
        tool_steps=steps,
        provider=model_config.get("provider"),
        model=model_config.get("model"),
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        total_tokens=usage["total_tokens"],
        grounded=True,
        created_at=datetime.now(),
    )
