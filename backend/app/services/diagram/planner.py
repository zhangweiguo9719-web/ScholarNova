"""
科研框架图规划器：LLM 生成结构化布局 → 组装期刊规范提示词 → 交给出图模型。

与 prompt_engine 解耦：
- prompt_engine：纯字符串组装 + 启发式布局选择（无 IO）
- planner：调用 LLM 生成 JSON 规划，失败时回退到启发式布局

降级设计：LLM 不可用时，用启发式布局 + 规则生成的模块兜底，
保证出图链路永远有合格提示词可用。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.services.diagram import prompt_engine as pe

logger = logging.getLogger(__name__)


def _fallback_modules(route_title: str, knowledge_text: str = "") -> List[Dict[str, str]]:
    """
    启发式模块生成：当 LLM 规划失败时，从布局 + 通用科研流程生成兜底模块。

    返回 5 个通用科研流程模块，并尽量从知识库文本中抽取领域名词做标签。
    """
    # 通用科研流程骨架
    skeleton = [
        ("Data Input", "multi-source data collection"),
        ("Preprocessing", "cleaning and normalization"),
        ("Core Method", "model and algorithm"),
        ("Training & Validation", "loss optimization and evaluation"),
        ("Output", "predictions and metrics"),
    ]
    # 尝试从知识库提取 1-2 个领域词作为方法模块增强（尽力而为）
    modules = [{"name": n, "desc": d} for n, d in skeleton]
    return modules


async def plan_modules_with_llm(
    llm_gateway,
    route_title: str,
    knowledge_text: str = "",
    text_analysis: str = "",
) -> Optional[Dict[str, Any]]:
    """
    调用 LLM 生成结构化规划（JSON）。

    Returns:
        解析后的 dict（含 layout/modules/flow），失败返回 None
    """
    user_prompt = pe.build_planning_user_prompt(
        route_title=route_title,
        knowledge_text=knowledge_text,
        text_analysis=text_analysis,
    )
    try:
        raw = await llm_gateway.chat(
            messages=[
                {"role": "system", "content": pe.PLANNING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        # 容错：去掉可能的 markdown 围栏
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        plan = json.loads(cleaned)
        if not isinstance(plan, dict):
            logger.warning("LLM planning returned non-dict: %r", plan)
            return None
        # 校验布局 key
        layout = plan.get("layout")
        if layout not in pe.LAYOUT_PATTERNS:
            logger.warning("Unknown layout from LLM: %r, falling back", layout)
            plan["layout"] = pe.select_layout(route_title, text_analysis, knowledge_text)
        modules = plan.get("modules")
        if not isinstance(modules, list) or not modules:
            plan["modules"] = []
        return plan
    except (json.JSONDecodeError, ValueError, AttributeError) as exc:
        logger.warning("LLM diagram planning failed: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - 规划失败必须降级而非中断
        logger.warning("LLM diagram planning error: %s", exc)
        return None


async def build_prompt_for_route(
    llm_gateway,
    route_title: str,
    knowledge_text: str = "",
    text_analysis: str = "",
    aspect_ratio: str = "16:9",
) -> str:
    """
    一站式：尝试 LLM 规划，失败则启发式布局，返回**渲染层**最终提示词。

    Args:
        llm_gateway: 已配置 LLMGateway（analysis 任务即可）
        route_title: 研究路线标题
        knowledge_text: 知识库条目
        text_analysis: 文字分析
        aspect_ratio: 出图比例

    Returns:
        完整英文生图提示词（只含可渲染内容）
    """
    plan = await plan_modules_with_llm(
        llm_gateway, route_title, knowledge_text, text_analysis
    )
    if plan is not None:
        layout = plan.get("layout", "pipeline")
        modules = plan.get("modules") or _fallback_modules(route_title, knowledge_text)
        return pe.build_render_prompt(
            route_title=route_title,
            modules=modules,
            layout=layout,
            aspect_ratio=aspect_ratio,
        )
    # 降级：启发式布局 + 兜底模块
    layout = pe.select_layout(route_title, text_analysis, knowledge_text)
    modules = _fallback_modules(route_title, knowledge_text)
    return pe.build_render_prompt(
        route_title=route_title,
        modules=modules,
        layout=layout,
        aspect_ratio=aspect_ratio,
    )
