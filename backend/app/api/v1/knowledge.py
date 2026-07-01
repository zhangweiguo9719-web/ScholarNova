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
            from app.services.llm.gateway import LLMGateway
            from app.config import get_model_for_task

            task_config = get_model_for_task("analysis")
            llm = LLMGateway()
            llm.configure(
                api_key=task_config["api_key"],
                base_url=task_config["base_url"],
                model_name=task_config["model"],
            )

            polish_prompt = f"""请对以下学术笔记进行润色和结构化提取：

原文：
{request.content[:1000]}

请输出 JSON 格式：
{{"polished_content": "精炼后的核心内容（200字以内）", "research_points": ["研究点1", "研究点2"], "tags": ["标签1", "标签2"]}}"""

            result = await llm.chat(
                messages=[
                    {"role": "system", "content": "你是学术笔记润色专家。输出JSON格式。"},
                    {"role": "user", "content": polish_prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
            )

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
    from app.config import settings

    try:
        # Step 1: MiMo 生成文字分析
        from app.config import get_model_for_task
        text_config = get_model_for_task("analysis")
        mimo = LLMGateway()
        mimo.configure(
            api_key=text_config["api_key"],
            base_url=text_config["base_url"],
            model_name=text_config["model"],
        )
        text_analysis = await mimo.chat(
            messages=[{"role": "system", "content": "你是学术研究顾问。请用中文输出详细的分析报告，包含研究目标、技术路线图（用文字描述模块关系和数据流）、关键任务。"}, {"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=4096,
        )

        # Step 2: SenseNova-U1 生成可视化架构图（真实图片）
        diagram_config = get_model_for_task("diagram")
        sn = LLMGateway(provider="sensenova")
        sn.configure(
            api_key=diagram_config["api_key"],
            base_url=diagram_config["base_url"],
            model_name=diagram_config["model"],
        )
        image_prompt = f"""Create a publication-quality research framework infographic for:
"{route.title}"

Ground the diagram in these verified knowledge items:
{knowledge_text[:1200] or "No linked knowledge details"}

Use the following route analysis only as layout guidance:
{text_analysis[:1500]}

Requirements:
- 16:9 landscape, clean white background, academic paper style
- clear left-to-right data flow with arrows
- 3 to 5 labeled modules covering inputs, core methods, validation, and outputs
- concise English labels to avoid unreadable generated text
- navy, teal, and restrained gold palette
- no decorative filler, no invented numeric results, no logos or watermarks
"""

        from pathlib import Path

        diagram_dir = Path(__file__).resolve().parents[3] / "generated" / "route_diagrams"
        diagram_path = diagram_dir / f"{route.id}.png"
        image_result = await sn.generate_image(
            prompt=image_prompt,
            save_path=str(diagram_path),
        )

        # 合并结果
        if image_result.get("status") == "ok":
            image_url = (
                f"http://127.0.0.1:8000/generated/route_diagrams/{route.id}.png"
                if diagram_path.exists()
                else image_result.get("url", "")
            )
            combined = f"""## 文字分析（MiMo）
{text_analysis}

---

## 研究架构图（SenseNova-U1）
![研究架构图]({image_url})

[查看大图]({image_url})"""
        else:
            # 图像生成失败，回退到文字描述
            fallback_msg = image_result.get("error", "图像生成失败")
            combined = f"""## 文字分析（MiMo）
{text_analysis}

---

## 研究架构图（SenseNova-U1）
> ⚠️ 图像生成暂不可用：{fallback_msg}

请参考上方文字分析中的架构描述。"""

        route.ai_analysis = combined
        await db.commit()
        await db.refresh(route)
        return RouteResponse(
            id=route.id, title=route.title, description=route.description,
            knowledge_ids=route.knowledge_ids or [], ai_analysis=route.ai_analysis,
            status=route.status, created_at=route.created_at, updated_at=route.updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI route analysis failed: {str(e)}")


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

    # 调用 LLM
    from app.services.llm.gateway import LLMGateway
    from app.config import get_model_for_task

    task_config = get_model_for_task("analysis")
    llm_gateway = LLMGateway()
    llm_gateway.configure(
        api_key=task_config["api_key"],
        base_url=task_config["base_url"],
        model_name=task_config["model"],
    )

    try:
        response = await llm_gateway.chat(
            messages=[
                {"role": "system", "content": "你是学术研究顾问，擅长分析研究方向和规划技术路线。请用中文输出详细分析。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        return AIAnalyzeResponse(
            analysis=response,
            knowledge_count=len(knowledge_list),
            created_at=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")


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
    prompt = f"""你是学术论文推荐专家。根据用户的知识库，推荐值得阅读的新论文。

## 用户的知识库
{knowledge_text}

## 推荐要求：
1. 推荐{request.limit}篇与用户研究方向高度相关的新论文
2. 优先推荐近两年的论文
3. 覆盖不同技术路线
4. 每篇论文说明为什么推荐

请用中文输出。"""

    # 调用 LLM
    from app.services.llm.gateway import LLMGateway
    from app.config import get_model_for_task

    task_config = get_model_for_task("analysis")
    llm_gateway = LLMGateway()
    llm_gateway.configure(
        api_key=task_config["api_key"],
        base_url=task_config["base_url"],
        model_name=task_config["model"],
    )

    try:
        response = await llm_gateway.chat(
            messages=[
                {"role": "system", "content": "你是学术论文推荐专家，擅长根据研究方向推荐高质量论文。请用中文输出推荐结果。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        return RecommendResponse(
            recommendations=response,
            knowledge_count=len(knowledge_list),
            created_at=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"Paper recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Paper recommendation failed: {str(e)}")
