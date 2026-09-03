"""
科研阶段路线规划器：把研究路线拆解为可执行的阶段路线图。

方法来源：research-planning-architect（clear0215）的"Tiered Experiment Matrix"
与决策门思想——把研究拆成若干阶段，每阶段有明确目标、关键任务、可交付产出、
以及 continue/revise/stop 决策门。适配到 ScholarNova 的科研场景：

  选题定位 → 文献调研 → 方法设计 → 实验验证 → 论文写作

与绘图引擎解耦：
- route_planner：LLM 生成结构化阶段路线 JSON（无绘图依赖）
- prompt_engine：把阶段路线渲染成期刊规范生图提示词（roadmap 布局）
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 科研阶段骨架（LLM 可覆盖，作为兜底）
STAGE_SKELETON = [
    {"id": 1, "name": "Topic", "zh": "选题定位",
     "tasks": ["define problem", "identify gap", "set goal"],
     "deliverable": "research question", "gate": "clear, falsifiable question"},
    {"id": 2, "name": "Literature", "zh": "文献调研",
     "tasks": ["search recent works", "build baseline table", "assess novelty"],
     "deliverable": "evidence ledger", "gate": "gap confirmed, baselines listed"},
    {"id": 3, "name": "Method", "zh": "方法设计",
     "tasks": ["design mechanism", "pick architecture", "plan ablations"],
     "deliverable": "method blueprint", "gate": "mechanism falsifiable"},
    {"id": 4, "name": "Experiment", "zh": "实验验证",
     "tasks": ["tier-1 feasibility", "tier-2 improvement", "tier-3 comparison"],
     "deliverable": "result tables", "gate": "claim supported by evidence"},
    {"id": 5, "name": "Paper", "zh": "论文写作",
     "tasks": ["draft sections", "draw figures", "reviewer red-team"],
     "deliverable": "submission draft", "gate": "every claim evidenced"},
]


def _fallback_stages(route_title: str, knowledge_text: str = "") -> List[Dict[str, Any]]:
    """兜底：LLM 失败时用标准阶段骨架（保证路线图始终可出）。"""
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "zh": s["zh"],
            "tasks": s["tasks"],
            "deliverable": s["deliverable"],
            "gate": s["gate"],
        }
        for s in STAGE_SKELETON
    ]


PLANNING_SYSTEM_PROMPT = (
    "You are a research roadmap planner. Given a research route and its "
    "knowledge base content, decompose the research work into a 5-stage "
    "roadmap, following evidence-grounded planning (each stage has tasks, a "
    "deliverable, and a continue/revise/stop decision gate). Reply with JSON "
    "only, no markdown fences."
)

PLANNING_USER_TEMPLATE = """Research route: {route_title}

Verified knowledge items (ground truth):
{knowledge_text}

Route analysis (content reference only):
{text_analysis}

Output JSON with this exact schema:
{{
  "current_stage": 1..5 (which stage the researcher is likely at, based on knowledge maturity),
  "stages": [
    {{
      "id": 1,
      "name": "short English stage name (1-2 words)",
      "zh": "中文阶段名",
      "tasks": ["2-3 short English tasks"],
      "deliverable": "one short English deliverable",
      "gate": "one short continue/revise/stop criterion"
    }}
  ]
}}

Rules:
- 5 stages exactly, ordered by research progression
- Stage names and tasks MUST reflect the actual research content (method,
  datasets, models from knowledge items); do not invent unrelated tasks
- Tasks are short English phrases (3-5 words), to be rendered in a diagram
- The final stage is paper writing
- No numeric results in task labels"""


def build_planning_user_prompt(
    route_title: str,
    knowledge_text: str = "",
    text_analysis: str = "",
) -> str:
    """组装规划层提示词。"""
    return PLANNING_USER_TEMPLATE.format(
        route_title=route_title,
        knowledge_text=knowledge_text or "No linked knowledge details",
        text_analysis=text_analysis or "No analysis available",
    )


async def plan_stages_with_llm(
    llm_gateway,
    route_title: str,
    knowledge_text: str = "",
    text_analysis: str = "",
) -> Optional[Dict[str, Any]]:
    """
    调用 LLM 生成阶段路线 JSON。

    Returns:
        {"current_stage": int, "stages": [...]} 或 None（失败时）
    """
    user_prompt = build_planning_user_prompt(route_title, knowledge_text, text_analysis)
    try:
        raw = await llm_gateway.chat(
            messages=[
                {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1536,
        )
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        plan = json.loads(cleaned)
        if not isinstance(plan, dict):
            logger.warning("Stage planning returned non-dict: %r", plan)
            return None
        stages = plan.get("stages")
        if not isinstance(stages, list) or not stages:
            plan["stages"] = _fallback_stages(route_title, knowledge_text)
        # 校验并归一化每个阶段
        for i, s in enumerate(stages):
            if not isinstance(s, dict):
                stages[i] = _fallback_stages(route_title, knowledge_text)[i]
                continue
            for key in ("name", "zh", "tasks", "deliverable", "gate"):
                if key not in s:
                    s[key] = _fallback_stages(route_title, knowledge_text)[i].get(key)
            s["id"] = i + 1
            if not isinstance(s.get("tasks"), list):
                s["tasks"] = []
        current = plan.get("current_stage")
        if not isinstance(current, int) or not (1 <= current <= 5):
            plan["current_stage"] = 1
        return plan
    except (json.JSONDecodeError, ValueError, AttributeError) as exc:
        logger.warning("Stage planning failed: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - 规划失败必须降级而非中断
        logger.warning("Stage planning error: %s", exc)
        return None


async def build_roadmap_for_route(
    llm_gateway,
    route_title: str,
    knowledge_text: str = "",
    text_analysis: str = "",
) -> Dict[str, Any]:
    """
    一站式：LLM 规划阶段路线（失败则兜底骨架），返回：
    - "plan": 结构化阶段路线（供存储/前端展示）
    - "prompt": 渲染层路线图提示词（供商汤出图）
    """
    plan = await plan_stages_with_llm(
        llm_gateway, route_title, knowledge_text, text_analysis
    )
    if plan is None:
        plan = {
            "current_stage": 1,
            "stages": _fallback_stages(route_title, knowledge_text),
        }

    # 组装渲染层提示词（roadmap 布局，纯描述）
    stages = plan["stages"]
    current = int(plan.get("current_stage") or 1)

    stage_lines = []
    for s in stages:
        tasks = ", ".join(s.get("tasks", [])[:3])
        marker = " [CURRENT]" if int(s.get("id", 1)) == current else ""
        stage_lines.append(
            f"- Stage {s.get('id')} {s.get('name', '')}{marker}: tasks = {tasks}; "
            f"deliverable = {s.get('deliverable', '')}"
        )

    prompt_lines = [
        f"Create a clean, publication-quality research roadmap diagram for "
        f"the topic: \"{route_title}\".",
        "The roadmap has 5 stages arranged left to right, connected by arrows.",
        "The 5 stages, in order:",
        *stage_lines,
        "Highlight the current stage with a distinct accent color.",
        "Layout: horizontal research roadmap, each stage is a column with its "
        "task labels and one deliverable; arrows show stage progression only.",
        "Visual style: publication-quality scientific figure, flat design with "
        "subtle shadows, rounded rectangles, concise short English labels only, "
        "generous white space.",
        "Color palette: restrained academic colors — navy for stage columns, "
        "teal for the current stage highlight, muted gold for deliverables, "
        "on a clean off-white background.",
    ]
    return {
        "plan": plan,
        "prompt": "\n".join(prompt_lines),
    }
