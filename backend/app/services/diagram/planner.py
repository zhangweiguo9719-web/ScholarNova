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


# 常见中文科研术语 → 英文模块名（供启发式降级路径使用）
_TERM_TO_MODULE = {
    "图卷积": "Graph Convolution",
    "图神经": "Graph Neural Net",
    "卷积": "Convolution",
    "注意力": "Attention",
    "transformer": "Transformer",
    "多模态": "Multi-modal Fusion",
    "融合": "Feature Fusion",
    "知识图谱": "Knowledge Graph",
    "知识库": "Knowledge Base",
    "检索": "Retrieval",
    "生成": "Generation",
    "预测": "Prediction",
    "分类": "Classification",
    "聚类": "Clustering",
    "强化学习": "Reinforcement",
    "深度学习": "Deep Learning",
    "预训练": "Pre-training",
    "微调": "Fine-tuning",
    "大模型": "Foundation Model",
    "llm": "LLM",
    "向量": "Embedding",
    "时序": "Time Series",
    "时空": "Spatio-temporal",
    "图网络": "Graph Network",
    "传感器": "Sensor Data",
    "天气": "Weather Data",
    "路网": "Road Network",
    "轨迹": "Trajectory",
    "优化": "Optimization",
    "评估": "Evaluation",
    "验证": "Validation",
}


def _extract_domain_terms(knowledge_text: str, limit: int = 3) -> List[str]:
    """
    从知识库文本中抽取领域术语（启发式，命中则转英文模块名）。

    - 按配置顺序匹配；命中更具体的术语后，跳过其子串（如"图卷积"命中后跳过"卷积"）
    - limit 为最大返回数，但保证先取多样化的领域词
    """
    if not knowledge_text:
        return []
    lowered = knowledge_text.lower()
    found: List[str] = []
    matched_terms: List[str] = []
    for term, eng in _TERM_TO_MODULE.items():
        t = term.lower()
        if t not in lowered:
            continue
        # 若该术语是已命中更具体术语的子串，跳过（避免"图卷积"与"卷积"并存）
        if any(t in m and len(t) < len(m) for m in matched_terms):
            continue
        if eng not in found:
            found.append(eng)
            matched_terms.append(t)
        if len(found) >= limit:
            break
    return found


def _fallback_modules(route_title: str, knowledge_text: str = "") -> List[Dict[str, str]]:
    """
    启发式模块生成：当 LLM 规划失败时，从知识库文本抽取领域术语，
    组装成贴近研究主题的流水线模块（而非纯通用骨架）。

    结构：Input → [抽取的领域模块...] → Output，数量 4-6 个。
    """
    domain = _extract_domain_terms(knowledge_text, limit=3)
    skeleton = [
        ("Data Input", "multi-source data collection"),
        *[(d, "core processing module") for d in domain],
        ("Training & Validation", "loss optimization and evaluation"),
        ("Output", "predictions and metrics"),
    ]
    return [{"name": n, "desc": d} for n, d in skeleton]


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
) -> str:
    """
    一站式：尝试 LLM 规划，失败则启发式布局，返回**渲染层**最终提示词。

    注：出图比例不在此控制，由调用方 generate_image(aspect_ratio=...) 决定。

    Args:
        llm_gateway: 已配置 LLMGateway（analysis 任务即可）
        route_title: 研究路线标题
        knowledge_text: 知识库条目
        text_analysis: 文字分析

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
        )
    # 降级：启发式布局 + 兜底模块
    layout = pe.select_layout(route_title, text_analysis, knowledge_text)
    modules = _fallback_modules(route_title, knowledge_text)
    return pe.build_render_prompt(
        route_title=route_title,
        modules=modules,
        layout=layout,
    )
