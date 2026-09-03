"""
研究知识库相关 API 端点
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge import KnowledgeBase, ResearchRoute
from app.services.features.knowledge import (
    delete_knowledge_features,
    rebuild_knowledge_features,
)
from app.services.inference import AllModelsUnavailableError, chat_with_fallback
from app.schemas.knowledge import (
    AIAnalyzeRequest,
    AIAnalyzeResponse,
    CategoryCount,
    KnowledgeCreate,
    KnowledgeListResponse,
    KnowledgeResponse,
    KnowledgeUpdate,
    RecommendRequest,
    RecommendResponse,
    RouteCreate,
    RouteListResponse,
    RouteResponse,
    RouteUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _knowledge_fallback(knowledge_list: list, query: str | None = None) -> str:
    """Return a grounded research outline without inventing unsupported claims."""
    lines = []
    for index, item in enumerate(knowledge_list, 1):
        points = list(item.research_points or [])[:3]
        detail = "；".join(points) if points else (item.content or "")[:180]
        lines.append(f"{index}. {item.title}：{detail or '仅有标题，缺少可分析内容'}")
    extra = f"\n\n用户补充要求：{query}" if query else ""
    materials = chr(10).join(lines) or "暂无关联知识条目"
    return f"""## 基于现有知识的规则整理（模型暂不可用）

主模型与备用模型均未完成请求。以下内容只重组已保存的知识条目，不新增论文、实验结果或研究结论。

### 当前材料
{materials}{extra}

### 可执行的下一步
1. 核对上述条目是否覆盖同一研究问题、方法、数据和评价指标。
2. 对缺少全文或实验细节的条目补充合法来源 PDF，再执行证据检索。
3. 基于已核验关键词发起新一轮多源论文搜索，并人工确认候选论文后加入知识库。
"""


def _recommendation_fallback(knowledge_list: list) -> str:
    """Build search directions rather than fabricating bibliographic records."""
    terms: list[str] = []
    for item in knowledge_list:
        for value in [item.title, *(item.research_points or []), *(item.tags or [])]:
            value = str(value or "").strip()
            if value and value not in terms:
                terms.append(value)
    suggestions = "\n".join(
        f"{index}. {term}" for index, term in enumerate(terms[:8], 1)
    ) or "1. 请先为知识条目补充研究点或标签"
    return f"""## 可核验检索方向（模型暂不可用）

系统不会在缺少学术检索结果时编造论文题目或 DOI。可将以下已有主题用于 ScholarNova 多源检索：

{suggestions}

检索后请以 Semantic Scholar、OpenAlex、Crossref 或 arXiv 返回的真实元数据为准。
"""


# ============================================================
# 知识库 CRUD 端点
# ============================================================

@router.post("", response_model=KnowledgeResponse, status_code=201)
async def create_knowledge(
    request: KnowledgeCreate,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeResponse:
    """
    创建知识条目（可选 AI 润色）
    """
    content = request.content
    research_points = list(request.research_points)
    tags = list(request.tags)

    # AI 润色：精炼内容、提取研究点、生成标签
    if request.auto_polish and request.content:
        try:
            polish_prompt = f"""请对以下学术笔记进行润色和结构化提取：

原文：
{request.content[:1000]}

请输出 JSON 格式：
{{"polished_content": "精炼后的核心内容（200字以内）", "research_points": ["研究点1", "研究点2"], "tags": ["标签1", "标签2"]}}"""

            routed = await chat_with_fallback(
                task="analysis",
                messages=[
                    {"role": "system", "content": "你是学术笔记润色专家。输出JSON格式。"},
                    {"role": "user", "content": polish_prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            result = routed.content

            # 解析 LLM 结果
            import json as json_mod
            try:
                cleaned = result.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
                polished = json_mod.loads(cleaned)
                content = polished.get("polished_content", content)
                if polished.get("research_points"):
                    research_points = polished["research_points"]
                if polished.get("tags"):
                    tags = polished["tags"]
            except Exception:
                pass  # 解析失败就用原内容
        except Exception:
            pass  # LLM 失败就用原内容

    knowledge = KnowledgeBase(
        title=request.title,
        category=request.category,
        content=content,
        source_paper_id=request.source_paper_id,
        source_paper_title=request.source_paper_title,
        source_paper_doi=request.source_paper_doi,
        research_points=research_points,
        tags=tags,
        notes=request.notes,
        card_type=request.card_type,
        card_data=request.card_data,
    )
    db.add(knowledge)
    await db.flush()
    await rebuild_knowledge_features(db, knowledge)
    await db.commit()
    await db.refresh(knowledge)

    return KnowledgeResponse(
        id=knowledge.id,
        title=knowledge.title,
        category=knowledge.category,
        content=knowledge.content,
        source_paper_id=knowledge.source_paper_id,
        source_paper_title=knowledge.source_paper_title,
        source_paper_doi=knowledge.source_paper_doi,
        research_points=knowledge.research_points or [],
        tags=knowledge.tags or [],
        notes=knowledge.notes,
        created_at=knowledge.created_at,
        updated_at=knowledge.updated_at,
    )


@router.get("", response_model=KnowledgeListResponse)
async def list_knowledge(
    category: Optional[str] = Query(None, description="按分类筛选"),
    keyword: Optional[str] = Query(None, description="按关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeListResponse:
    """
    获取知识列表

    支持分类筛选和关键词搜索
    """
    # 构建查询
    query = select(KnowledgeBase)

    if category:
        query = query.where(KnowledgeBase.category == category)

    if keyword:
        query = query.where(
            KnowledgeBase.title.contains(keyword)
            | KnowledgeBase.content.contains(keyword)
        )

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(KnowledgeBase.created_at.desc())
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    knowledge_list = result.scalars().all()

    # 获取所有分类及论文数
    category_query = (
        select(
            KnowledgeBase.category,
            func.count(KnowledgeBase.id).label("count")
        )
        .group_by(KnowledgeBase.category)
    )
    category_result = await db.execute(category_query)
    categories = [
        CategoryCount(name=row[0], count=row[1])
        for row in category_result.all()
    ]

    return KnowledgeListResponse(
        items=[
            KnowledgeResponse(
                id=k.id,
                title=k.title,
                category=k.category,
                content=k.content,
                source_paper_id=k.source_paper_id,
                source_paper_title=k.source_paper_title,
                source_paper_doi=k.source_paper_doi,
                research_points=k.research_points or [],
                tags=k.tags or [],
                notes=k.notes,
                created_at=k.created_at,
                updated_at=k.updated_at,
            )
            for k in knowledge_list
        ],
        total=total,
        categories=categories,
    )


@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db),
) -> List[CategoryCount]:
    """
    获取所有分类及论文数
    """
    category_query = (
        select(
            KnowledgeBase.category,
            func.count(KnowledgeBase.id).label("count")
        )
        .group_by(KnowledgeBase.category)
    )
    category_result = await db.execute(category_query)
    return [
        CategoryCount(name=row[0], count=row[1])
        for row in category_result.all()
    ]


# ============================================================
# 研究路线 CRUD 端点（必须在 /{kid} 之前注册）
# ============================================================

@router.post("/routes", response_model=RouteResponse, status_code=201)
async def create_route(
    request: RouteCreate,
    db: AsyncSession = Depends(get_db),
) -> RouteResponse:
    """创建研究路线"""
    route = ResearchRoute(
        title=request.title,
        description=request.description,
        knowledge_ids=request.knowledge_ids,
        status="active",
    )
    db.add(route)
    await db.commit()
    await db.refresh(route)
    return RouteResponse(
        id=route.id, title=route.title, description=route.description,
        knowledge_ids=route.knowledge_ids or [], ai_analysis=route.ai_analysis,
        status=route.status, created_at=route.created_at, updated_at=route.updated_at,
    )


@router.get("/routes", response_model=RouteListResponse)
async def list_routes(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> RouteListResponse:
    """获取研究路线列表"""
    query = select(ResearchRoute)
    if status:
        query = query.where(ResearchRoute.status == status)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(ResearchRoute.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    routes = (await db.execute(query)).scalars().all()
    return RouteListResponse(
        items=[RouteResponse(
            id=r.id, title=r.title, description=r.description,
            knowledge_ids=r.knowledge_ids or [], ai_analysis=r.ai_analysis,
            status=r.status, created_at=r.created_at, updated_at=r.updated_at,
        ) for r in routes],
        total=total,
    )


@router.get("/routes/{route_id}", response_model=RouteResponse)
async def get_route(route_id: str, db: AsyncSession = Depends(get_db)) -> RouteResponse:
    """获取研究路线详情"""
    route = (await db.execute(select(ResearchRoute).where(ResearchRoute.id == route_id))).scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return RouteResponse(
        id=route.id, title=route.title, description=route.description,
        knowledge_ids=route.knowledge_ids or [], ai_analysis=route.ai_analysis,
        status=route.status, created_at=route.created_at, updated_at=route.updated_at,
    )


@router.put("/routes/{route_id}", response_model=RouteResponse)
async def update_route(route_id: str, request: RouteUpdate, db: AsyncSession = Depends(get_db)) -> RouteResponse:
    """更新研究路线"""
    route = (await db.execute(select(ResearchRoute).where(ResearchRoute.id == route_id))).scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    if request.title is not None: route.title = request.title
    if request.description is not None: route.description = request.description
    if request.knowledge_ids is not None: route.knowledge_ids = request.knowledge_ids
    if request.status is not None: route.status = request.status
    await db.commit()
    await db.refresh(route)
    return RouteResponse(
        id=route.id, title=route.title, description=route.description,
        knowledge_ids=route.knowledge_ids or [], ai_analysis=route.ai_analysis,
        status=route.status, created_at=route.created_at, updated_at=route.updated_at,
    )


@router.delete("/routes/{route_id}")
async def delete_route(route_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """删除研究路线"""
    route = (await db.execute(select(ResearchRoute).where(ResearchRoute.id == route_id))).scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    await db.delete(route)
    await db.commit()
    return {"success": True, "message": "Route deleted"}


@router.post("/routes/{route_id}/ai-generate", response_model=RouteResponse)
async def ai_generate_route_analysis(route_id: str, db: AsyncSession = Depends(get_db)) -> RouteResponse:
    """AI 生成研究路线分析"""
    route = (await db.execute(select(ResearchRoute).where(ResearchRoute.id == route_id))).scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    knowledge_list = []
    if route.knowledge_ids:
        for kid in route.knowledge_ids:
            k = (await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kid))).scalar_one_or_none()
            if k: knowledge_list.append(k)

    knowledge_text = "\n".join([f"{i}. {k.title} [{k.category}] - {(k.content or '')[:200]}" for i, k in enumerate(knowledge_list, 1)])

    prompt = f"""你是学术研究顾问。请为研究路线「{route.title}」生成分析报告。

关联知识点：
{knowledge_text or '暂无'}

请输出：研究目标、技术路线图、关键任务、预期成果。用中文。"""

    from app.services.llm.gateway import LLMGateway
    from app.config import get_model_for_task

    # Step 1: 文字分析使用任务主模型；失败后由显式备用模型接管。
    try:
        routed = await chat_with_fallback(
            task="analysis",
            messages=[{"role": "system", "content": "你是学术研究顾问。请用中文输出详细的分析报告，包含研究目标、技术路线图（用文字描述模块关系和数据流）、关键任务。"}, {"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=4096,
        )
        text_analysis = routed.content
        text_label = f"{routed.profile.get('provider')}/{routed.profile.get('model')}"
        if routed.fallback_used:
            text_label += " · 备用模型"
    except AllModelsUnavailableError:
        logger.exception("Research-route text models unavailable", extra={"route_id": route_id})
        text_analysis = _knowledge_fallback(knowledge_list)
        text_label = "规则兜底 · 无模型调用结果"

    # Step 2: 出图保持独立的 diagram 配置，不路由到普通文本备用模型。
    diagram_config = get_model_for_task("diagram")
    diagram_label = f"{diagram_config.get('provider')}/{diagram_config.get('model')}"
    try:
        sn = LLMGateway(provider=diagram_config["provider"])
        sn.configure(
            api_key=diagram_config["api_key"],
            base_url=diagram_config["base_url"],
            model_name=diagram_config["model"],
        )
        # 提示词由 LLM 规划 + Nature 规范引擎组装；LLM 失败时降级到启发式布局。
        planner_gw = LLMGateway(task="analysis")
        image_prompt = await build_prompt_for_route(
            planner_gw,
            route_title=route.title,
            knowledge_text=knowledge_text or "No linked knowledge details",
            text_analysis=text_analysis or "",
        )

        from app.config import runtime_path

        diagram_dir = runtime_path("generated") / "route_diagrams"
        diagram_dir.mkdir(parents=True, exist_ok=True)
        diagram_path = diagram_dir / f"{route.id}.png"
        image_result = await sn.generate_image(
            prompt=image_prompt,
            save_path=str(diagram_path),
        )
    except Exception as exc:
        logger.exception("Research-route diagram generation failed", extra={"route_id": route_id})
        image_result = {"status": "error", "error": str(exc)}

    # 合并结果；模型名称取自实际路由，不再写死供应商。
    if image_result.get("status") == "ok":
        image_url = (
            f"/generated/route_diagrams/{route.id}.png"
            if diagram_path.exists()
            else image_result.get("url", "")
        )
        combined = f"""## 文字分析（{text_label}）
{text_analysis}

---

## 研究架构图（{diagram_label}）
![研究架构图]({image_url})

[查看大图]({image_url})"""
    else:
        fallback_msg = image_result.get("error", "图像生成失败")
        combined = f"""## 文字分析（{text_label}）
{text_analysis}

---

## 研究架构图（{diagram_label}）
> ⚠️ 图像生成暂不可用：{fallback_msg}

请参考上方文字分析中的架构描述。"""

    try:
        route.ai_analysis = combined
        await db.commit()
        await db.refresh(route)
        return RouteResponse(
            id=route.id, title=route.title, description=route.description,
            knowledge_ids=route.knowledge_ids or [], ai_analysis=route.ai_analysis,
            status=route.status, created_at=route.created_at, updated_at=route.updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Saving route analysis failed: {str(e)}")


# ============================================================
# 知识条目 CRUD 端点
# ============================================================

@router.get("/{kid}", response_model=KnowledgeResponse)
async def get_knowledge(
    kid: str,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeResponse:
    """
    获取单条知识详情
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kid)
    )
    knowledge = result.scalar_one_or_none()

    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge not found")

    return KnowledgeResponse(
        id=knowledge.id,
        title=knowledge.title,
        category=knowledge.category,
        content=knowledge.content,
        source_paper_id=knowledge.source_paper_id,
        source_paper_title=knowledge.source_paper_title,
        source_paper_doi=knowledge.source_paper_doi,
        research_points=knowledge.research_points or [],
        tags=knowledge.tags or [],
        notes=knowledge.notes,
        created_at=knowledge.created_at,
        updated_at=knowledge.updated_at,
    )


@router.put("/{kid}", response_model=KnowledgeResponse)
async def update_knowledge(
    kid: str,
    request: KnowledgeUpdate,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeResponse:
    """
    更新知识条目
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kid)
    )
    knowledge = result.scalar_one_or_none()

    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge not found")

    # 更新字段
    if request.title is not None:
        knowledge.title = request.title
    if request.category is not None:
        knowledge.category = request.category
    if request.content is not None:
        knowledge.content = request.content
    if request.source_paper_id is not None:
        knowledge.source_paper_id = request.source_paper_id
    if request.source_paper_title is not None:
        knowledge.source_paper_title = request.source_paper_title
    if request.source_paper_doi is not None:
        knowledge.source_paper_doi = request.source_paper_doi
    if request.research_points is not None:
        knowledge.research_points = request.research_points
    if request.tags is not None:
        knowledge.tags = request.tags
    if request.notes is not None:
        knowledge.notes = request.notes

    await rebuild_knowledge_features(db, knowledge)
    await db.commit()
    await db.refresh(knowledge)

    return KnowledgeResponse(
        id=knowledge.id,
        title=knowledge.title,
        category=knowledge.category,
        content=knowledge.content,
        source_paper_id=knowledge.source_paper_id,
        source_paper_title=knowledge.source_paper_title,
        source_paper_doi=knowledge.source_paper_doi,
        research_points=knowledge.research_points or [],
        tags=knowledge.tags or [],
        notes=knowledge.notes,
        created_at=knowledge.created_at,
        updated_at=knowledge.updated_at,
    )


@router.delete("/{kid}")
async def delete_knowledge(
    kid: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    删除知识条目
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kid)
    )
    knowledge = result.scalar_one_or_none()

    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge not found")

    await delete_knowledge_features(db, knowledge.id)
    await db.delete(knowledge)
    await db.commit()

    return {"success": True, "message": "Knowledge deleted"}


# ============================================================
# AI 分析端点
# ============================================================

@router.post("/ai-analyze", response_model=AIAnalyzeResponse)
async def ai_analyze_research(
    request: AIAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AIAnalyzeResponse:
    """
    AI 分析研究推进方向

    输入多个知识条目的ID，输出研究路线分析+架构图建议
    """
    # 获取所有相关知识条目
    knowledge_list = []
    for kid in request.knowledge_ids:
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kid)
        )
        knowledge = result.scalar_one_or_none()
        if knowledge:
            knowledge_list.append(knowledge)

    if not knowledge_list:
        raise HTTPException(status_code=404, detail="No valid knowledge entries found")

    # 构建知识列表文本（截断过长内容）
    knowledge_text = ""
    for i, k in enumerate(knowledge_list, 1):
        content = (k.content or "")[:500]  # 截断到500字
        knowledge_text += f"{i}. {k.title} [{k.category}] - {content[:200]}...\n"
        if k.research_points:
            knowledge_text += f"   研究点: {', '.join(k.research_points[:3])}\n"

    # 构建 Prompt（精简版，避免 MiMo 超时）
    prompt = f"""你是学术研究顾问。根据以下研究知识点，分析下一步方向。

知识点：
{knowledge_text}

请分析：
1. 核心关注点
2. 3-5个下一步研究方向
3. 研究架构图（文字描述）

用中文输出。"""

    try:
        routed = await chat_with_fallback(
            task="analysis",
            messages=[
                {"role": "system", "content": "你是学术研究顾问，擅长分析研究方向和规划技术路线。请用中文输出详细分析。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        return AIAnalyzeResponse(
            analysis=routed.content,
            knowledge_count=len(knowledge_list),
            provider=routed.profile.get("provider"),
            model=routed.profile.get("model"),
            model_completed=True,
            fallback_used=routed.fallback_used,
            prompt_tokens=routed.usage["prompt_tokens"],
            completion_tokens=routed.usage["completion_tokens"],
            total_tokens=routed.usage["total_tokens"],
            created_at=datetime.utcnow(),
        )
    except AllModelsUnavailableError as exc:
        logger.exception("Knowledge analysis models unavailable")
        return AIAnalyzeResponse(
            analysis=_knowledge_fallback(knowledge_list, request.query),
            knowledge_count=len(knowledge_list),
            model_completed=False,
            fallback_used=False,
            prompt_tokens=exc.usage["prompt_tokens"],
            completion_tokens=exc.usage["completion_tokens"],
            total_tokens=exc.usage["total_tokens"],
            created_at=datetime.utcnow(),
        )


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_papers(
    request: RecommendRequest,
    db: AsyncSession = Depends(get_db),
) -> RecommendResponse:
    """
    基于知识库推荐论文
    """
    # 获取所有相关知识条目
    knowledge_list = []
    for kid in request.knowledge_ids:
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kid)
        )
        knowledge = result.scalar_one_or_none()
        if knowledge:
            knowledge_list.append(knowledge)

    if not knowledge_list:
        raise HTTPException(status_code=404, detail="No valid knowledge entries found")

    # 构建知识列表文本
    knowledge_text = ""
    for i, k in enumerate(knowledge_list, 1):
        knowledge_text += f"""
### 知识点 {i}: {k.title}
- 分类: {k.category}
- 内容摘要: {k.content[:200]}...
- 研究点: {', '.join(k.research_points) if k.research_points else '无'}
- 标签: {', '.join(k.tags) if k.tags else '无'}
"""

    # 构建 Prompt
    prompt = f"""你是学术检索策略专家。根据用户的知识库生成可执行的论文检索与候选核验建议。

## 用户的知识库
{knowledge_text}

## 推荐要求：
1. 最多给出{request.limit}条检索方向或待核验候选
2. 优先覆盖近两年的研究方向和不同技术路线
3. 没有来自学术 API 的真实元数据时，禁止编造论文题目、作者、DOI 或引用量
4. 对每条建议给出可直接用于 ScholarNova 多源搜索的查询词

请用中文输出。"""

    try:
        routed = await chat_with_fallback(
            task="recommendation",
            messages=[
                {"role": "system", "content": "你是严谨的学术检索策略专家。只生成检索策略，不得伪造书目信息。请用中文输出。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        return RecommendResponse(
            recommendations=routed.content,
            knowledge_count=len(knowledge_list),
            provider=routed.profile.get("provider"),
            model=routed.profile.get("model"),
            model_completed=True,
            fallback_used=routed.fallback_used,
            prompt_tokens=routed.usage["prompt_tokens"],
            completion_tokens=routed.usage["completion_tokens"],
            total_tokens=routed.usage["total_tokens"],
            created_at=datetime.utcnow(),
        )
    except AllModelsUnavailableError as exc:
        logger.exception("Knowledge recommendation models unavailable")
        return RecommendResponse(
            recommendations=_recommendation_fallback(knowledge_list),
            knowledge_count=len(knowledge_list),
            model_completed=False,
            fallback_used=False,
            prompt_tokens=exc.usage["prompt_tokens"],
            completion_tokens=exc.usage["completion_tokens"],
            total_tokens=exc.usage["total_tokens"],
            created_at=datetime.utcnow(),
        )
