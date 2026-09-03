"""
研究路线分析流水线（可流式编排）。

把 ai_generate_route_analysis 的三步逻辑（文字分析 → 架构图 → 科研阶段路线图）
抽成异步生成器，逐步 yield 进度事件，供：
- 原 REST 端点消费（向后兼容，返回 RouteResponse）
- 新增 SSE 端点流式推送（前端实时展示进度）

事件格式：
  {"event": "stage", "stage": "analysis", "progress": 15,
   "message": "正在生成文字分析...", "data": {...}}
  {"event": "stage", "stage": "diagram", "progress": 45, ...}
  {"event": "stage", "stage": "roadmap", "progress": 75, ...}
  {"event": "done", "progress": 100, "data": {RouteResponse 字段}}
  {"event": "error", "message": "..."}
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _resolve_route_context(route_id: str, db: AsyncSession) -> Dict[str, Any]:
    """加载 route + 关联知识，返回上下文。route 不存在返回 None。"""
    from sqlalchemy import select

    from app.models.knowledge import KnowledgeBase, ResearchRoute

    route = (await db.execute(select(ResearchRoute).where(ResearchRoute.id == route_id))).scalar_one_or_none()
    if not route:
        return {"route": None, "knowledge_list": [], "knowledge_text": ""}

    knowledge_list = []
    if route.knowledge_ids:
        for kid in route.knowledge_ids:
            k = (await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kid))).scalar_one_or_none()
            if k:
                knowledge_list.append(k)

    knowledge_text = "\n".join(
        [f"{i}. {k.title} [{k.category}] - {(k.content or '')[:200]}" for i, k in enumerate(knowledge_list, 1)]
    )
    return {"route": route, "knowledge_list": knowledge_list, "knowledge_text": knowledge_text}


async def stream_route_analysis(
    route_id: str,
    db: AsyncSession,
) -> AsyncGenerator[Dict[str, Any], None]:
    """研究路线三步分析流水线（生成器）。

    每步完成后 yield 一个事件；最后 yield "done"（含 RouteResponse 字段）或 "error"。
    """
    from app.config import get_model_for_task, runtime_path
    from app.schemas.knowledge import RouteResponse
    from app.services.diagram.planner import build_prompt_for_route
    from app.services.diagram.route_planner import build_roadmap_for_route
    from app.services.inference import AllModelsUnavailableError, chat_with_fallback
    from app.services.llm.gateway import LLMGateway

    ctx = await _resolve_route_context(route_id, db)
    route = ctx["route"]
    if not route:
        yield {"event": "error", "progress": 0, "message": "Route not found"}
        return

    knowledge_list = ctx["knowledge_list"]
    knowledge_text = ctx["knowledge_text"]

    prompt = f"""你是学术研究顾问。请为研究路线「{route.title}」生成分析报告。

关联知识点：
{knowledge_text or '暂无'}

请输出：研究目标、技术路线图、关键任务、预期成果。用中文。"""

    # ---- Step 1: 文字分析 ----
    try:
        yield {
            "event": "stage", "stage": "analysis", "progress": 10,
            "message": "正在生成文字分析...",
        }
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
        from app.api.v1.knowledge import _knowledge_fallback
        text_analysis = _knowledge_fallback(knowledge_list)
        text_label = "规则兜底 · 无模型调用结果"

    yield {
        "event": "stage", "stage": "analysis", "progress": 30,
        "message": "文字分析完成",
        "data": {"text_analysis": text_analysis, "text_label": text_label},
    }

    # ---- Step 2: 架构图 ----
    diagram_config = get_model_for_task("diagram")
    diagram_label = f"{diagram_config.get('provider')}/{diagram_config.get('model')}"
    image_result: Dict[str, Any] = {"status": "error", "error": "diagram not started"}
    image_url = ""
    try:
        yield {
            "event": "stage", "stage": "diagram", "progress": 40,
            "message": "正在规划并生成研究架构图...",
        }
        sn = LLMGateway(provider=diagram_config["provider"])
        sn.configure(
            api_key=diagram_config["api_key"],
            base_url=diagram_config["base_url"],
            model_name=diagram_config["model"],
        )
        planner_gw = LLMGateway(task="analysis")
        image_prompt = await build_prompt_for_route(
            planner_gw,
            route_title=route.title,
            knowledge_text=knowledge_text or "No linked knowledge details",
            text_analysis=text_analysis or "",
        )
        diagram_dir = runtime_path("generated") / "route_diagrams"
        diagram_dir.mkdir(parents=True, exist_ok=True)
        diagram_path = diagram_dir / f"{route.id}.png"
        image_result = await sn.generate_image(prompt=image_prompt, save_path=str(diagram_path))
        if image_result.get("status") == "ok":
            image_url = (
                f"/generated/route_diagrams/{route.id}.png"
                if diagram_path.exists()
                else image_result.get("url", "")
            )
    except Exception as exc:
        logger.exception("Research-route diagram generation failed", extra={"route_id": route_id})
        image_result = {"status": "error", "error": str(exc)}

    yield {
        "event": "stage", "stage": "diagram", "progress": 60,
        "message": "研究架构图完成" if image_url else f"研究架构图失败：{image_result.get('error', '')}",
        "data": {"image_url": image_url, "diagram_label": diagram_label},
    }

    # ---- Step 3: 科研阶段路线图 ----
    roadmap_result = None
    try:
        yield {
            "event": "stage", "stage": "roadmap", "progress": 70,
            "message": "正在规划并生成科研阶段路线图...",
        }
        roadmap = await build_roadmap_for_route(
            planner_gw,
            route_title=route.title,
            knowledge_text=knowledge_text or "No linked knowledge details",
            text_analysis=text_analysis or "",
        )
        roadmap_prompt = roadmap["prompt"]
        roadmap_plan = roadmap["plan"]
        stage_lines = []
        for s in roadmap_plan.get("stages", []):
            tasks = "、".join(s.get("tasks", []))
            stage_lines.append(
                f"- **{s.get('id')}. {s.get('zh', s.get('name', ''))}**："
                f"任务（{tasks}）；产出：{s.get('deliverable', '')}；"
                f"决策门：{s.get('gate', '')}"
            )
        roadmap_md = "\n".join(stage_lines)
        # 时效性 / 幻觉防线报告（若规划器已生成）
        evidence_summary = roadmap_plan.get("evidence_summary", "")
        if evidence_summary:
            roadmap_md += (
                "\n\n> 🛡️ **时效性与幻觉防线**：" + evidence_summary
            )
        roadmap_result = {"md": roadmap_md, "url": ""}
        roadmap_path = diagram_dir / f"{route.id}_roadmap.png"
        roadmap_img = await sn.generate_image(prompt=roadmap_prompt, save_path=str(roadmap_path))
        if roadmap_img.get("status") == "ok":
            roadmap_result["url"] = (
                f"/generated/route_diagrams/{route.id}_roadmap.png"
                if roadmap_path.exists()
                else roadmap_img.get("url", "")
            )
    except Exception:
        logger.exception("Research-route roadmap generation failed", extra={"route_id": route_id})
        roadmap_result = None

    roadmap_md = (roadmap_result or {}).get("md", "> 路线图生成暂不可用。")
    yield {
        "event": "stage", "stage": "roadmap", "progress": 85,
        "message": "科研阶段路线图完成",
        "data": {"roadmap_md": roadmap_md, "roadmap_url": (roadmap_result or {}).get("url", "")},
    }

    # ---- 合并结果 ----
    if image_url:
        combined = f"""## 文字分析（{text_label}）
{text_analysis}

---

## 研究架构图（{diagram_label}）
![研究架构图]({image_url})

[查看大图]({image_url})

---

## 科研阶段路线图
{roadmap_md}"""
    else:
        fallback_msg = image_result.get("error", "图像生成失败")
        combined = f"""## 文字分析（{text_label}）
{text_analysis}

---

## 研究架构图（{diagram_label}）
> ⚠️ 图像生成暂不可用：{fallback_msg}

请参考上方文字分析中的架构描述。

---

## 科研阶段路线图
{roadmap_md}"""

    try:
        route.ai_analysis = combined
        await db.commit()
        await db.refresh(route)
        data = {
            "id": route.id,
            "title": route.title,
            "description": route.description,
            "knowledge_ids": route.knowledge_ids or [],
            "ai_analysis": route.ai_analysis,
            "status": route.status,
            "created_at": route.created_at,
            "updated_at": route.updated_at,
        }
        # 显式转成 schema 以触发序列化校验
        payload = RouteResponse(**data).model_dump()
        yield {"event": "done", "progress": 100, "message": "分析完成", "data": payload}
    except Exception as e:
        logger.exception("Save route analysis failed", extra={"route_id": route_id})
        yield {"event": "error", "progress": 100, "message": f"Saving route analysis failed: {e}"}
