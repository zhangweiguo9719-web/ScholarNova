"""Grounded research-assistant prototype."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_model_for_task
from app.core.rate_limiter import check_rate_limit
from app.database import get_db
from app.models.knowledge import KnowledgeBase
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


def _knowledge_score(item: KnowledgeBase, terms: list[str]) -> int:
    title = (item.title or "").casefold()
    category = (item.category or "").casefold()
    content = (item.content or "").casefold()
    tags = " ".join(item.tags or []).casefold()
    return sum(
        5 * (term in title)
        + 3 * (term in category)
        + 2 * (term in tags)
        + (term in content)
        for term in terms
    )


async def _knowledge_materials(
    db: AsyncSession,
    question: str,
    *,
    limit: int = 4,
) -> list[KnowledgeBase]:
    result = await db.execute(
        select(KnowledgeBase).order_by(KnowledgeBase.updated_at.desc()).limit(80)
    )
    items = list(result.scalars().all())
    if not items:
        return []
    terms = _query_terms(question)
    ranked = sorted(
        items,
        key=lambda item: (
            _knowledge_score(item, terms),
            str(item.updated_at or ""),
        ),
        reverse=True,
    )
    relevant = [item for item in ranked if _knowledge_score(item, terms) > 0]
    return (relevant or ranked)[:limit]


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

    contexts: list[str] = []
    citations: list[AgentCitation] = []
    steps: list[AgentToolStep] = []

    if request.use_knowledge:
        knowledge_items = await _knowledge_materials(db, request.question)
        for item in knowledge_items:
            source_id = f"S{len(citations) + 1}"
            contexts.append(
                f"[{source_id}] ScholarNova 知识库\n"
                f"标题：{item.title}\n分类：{item.category}\n"
                f"内容：{(item.content or '')[:1800]}\n"
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
                count=len(knowledge_items),
                detail=f"从 ScholarNova 知识库选择了 {len(knowledge_items)} 条相关材料",
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
