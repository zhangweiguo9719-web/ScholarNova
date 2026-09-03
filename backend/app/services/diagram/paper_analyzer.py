"""
论文分析图规划器：把知识库/论文内容转为「论文结构图」渲染提示词。

把 nature-figure-prompts 的 Paper Analysis → Figure Planning 方法论，和
research-planning-architect 的"贡献陈述公式 / 证据锚定"思想，适配到
"分析一篇论文 / 一组知识点 → 出论文结构图"的场景：

  Research Question → Method → Contribution → Evidence

与绘图引擎解耦（同 planner / route_planner 模式）：
- 规划层：LLM 生成结构化 JSON（问题/方法/贡献/证据/布局）
- 渲染层：只含可渲染描述的英文提示词
- 失败降级：启发式骨架，保证链路不断
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _fallback_sections(knowledge_text: str = "") -> List[Dict[str, Any]]:
    """兜底：标准论文结构骨架（LLM 失败时保证可出图）。"""
    return [
        {"id": 1, "name": "Question", "zh": "研究问题",
         "items": ["research gap", "objective"], "evidence": "from knowledge items"},
        {"id": 2, "name": "Method", "zh": "方法",
         "items": ["proposed mechanism", "architecture"], "evidence": "method design"},
        {"id": 3, "name": "Contribution", "zh": "贡献",
         "items": ["novelty", "main result"], "evidence": "experiments"},
        {"id": 4, "name": "Evidence", "zh": "证据",
         "items": ["datasets", "metrics", "ablations"], "evidence": "verified results"},
    ]


PLANNING_SYSTEM_PROMPT = (
    "You are a scientific paper analyst. Given research knowledge items, "
    "produce a structured analysis of the paper/research as a figure plan: "
    "research question, method, contribution, and evidence. Follow "
    "publication standards: every claim must be traceable to the provided "
    "knowledge items, do not invent results. Reply with JSON only, no markdown fences."
)

PLANNING_USER_TEMPLATE = """Knowledge items to analyze:
{knowledge_text}

Output JSON with this exact schema:
{{
  "paper_title": "short English working title of the research",
  "layout": "pipeline" | "hierarchy" | "comparison",
  "sections": [
    {{
      "id": 1,
      "name": "Question",
      "zh": "研究问题",
      "items": ["2-3 short English items"],
      "evidence": "one short phrase describing what supports this"
    }}
  ]
}}

Rules:
- 4 sections: Question, Method, Contribution, Evidence (in that order)
- Items must come from the knowledge items; do not invent numeric results
- Items are short English phrases (3-5 words), for a diagram
- Choose layout: pipeline (Q→M→C→E flow), hierarchy (stacked), or
  comparison (if knowledge contrasts baselines)"""


def build_planning_user_prompt(knowledge_text: str = "") -> str:
    """组装规划层提示词。"""
    return PLANNING_USER_TEMPLATE.format(
        knowledge_text=knowledge_text or "No knowledge items provided"
    )


async def plan_paper_sections_with_llm(
    llm_gateway,
    knowledge_text: str = "",
) -> Optional[Dict[str, Any]]:
    """调用 LLM 生成论文结构 JSON；失败返回 None。"""
    user_prompt = build_planning_user_prompt(knowledge_text)
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
            logger.warning("Paper analysis returned non-dict: %r", plan)
            return None
        sections = plan.get("sections")
        if not isinstance(sections, list) or not sections:
            plan["sections"] = _fallback_sections(knowledge_text)
        for i, s in enumerate(sections):
            if not isinstance(s, dict):
                sections[i] = _fallback_sections(knowledge_text)[i]
                continue
            s["id"] = i + 1
            if not isinstance(s.get("items"), list):
                s["items"] = []
            for key in ("name", "zh", "evidence"):
                if key not in s:
                    s[key] = _fallback_sections(knowledge_text)[i].get(key)
        layout = plan.get("layout")
        if layout not in ("pipeline", "hierarchy", "comparison"):
            plan["layout"] = "pipeline"
        return plan
    except (json.JSONDecodeError, ValueError, AttributeError) as exc:
        logger.warning("Paper analysis planning failed: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - 必须降级而非中断
        logger.warning("Paper analysis planning error: %s", exc)
        return None


async def build_paper_diagram_prompt(
    llm_gateway,
    knowledge_text: str = "",
    paper_title: str = "",
) -> Dict[str, Any]:
    """
    一站式：LLM 规划论文结构（失败则兜底骨架），返回：
    - "plan": 结构化论文分析（供文档展示）
    - "prompt": 渲染层论文结构图提示词
    """
    plan = await plan_paper_sections_with_llm(llm_gateway, knowledge_text)
    if plan is None:
        plan = {
            "paper_title": paper_title or "Research Analysis",
            "layout": "pipeline",
            "sections": _fallback_sections(knowledge_text),
        }

    title = plan.get("paper_title") or paper_title or "Research Analysis"
    sections = plan["sections"]
    layout = plan.get("layout", "pipeline")

    # 渲染层提示词
    section_lines = []
    for s in sections:
        items = ", ".join(s.get("items", [])[:3])
        section_lines.append(
            f"- Section {s.get('id')} {s.get('name', '')}: {items}; "
            f"supported by {s.get('evidence', '')}"
        )

    layout_desc = {
        "pipeline": (
            "Layout: left-to-right pipeline: Question → Method → Contribution → "
            "Evidence, four labeled sections connected by arrows."
        ),
        "hierarchy": (
            "Layout: top-to-bottom stack: Question on top, Method below, "
            "Contribution, then Evidence at the bottom."
        ),
        "comparison": (
            "Layout: left-to-right flow with a comparison zone between Method "
            "and Evidence, contrasting the proposed approach with baselines."
        ),
    }.get(layout, "Layout: left-to-right pipeline with four labeled sections.")

    prompt_lines = [
        f"Create a clean, publication-quality paper analysis diagram for: "
        f"\"{title}\".",
        "The diagram has 4 labeled sections: Question, Method, Contribution, Evidence.",
        "The sections, in order:",
        *section_lines,
        layout_desc,
        "Visual style: publication-quality scientific figure, flat design with "
        "subtle shadows, rounded rectangles, concise short English labels only, "
        "generous white space.",
        "Color palette: restrained academic colors — navy for section titles, "
        "teal for method emphasis, muted gold for contributions, on a clean "
        "off-white background.",
    ]
    return {
        "plan": plan,
        "prompt": "\n".join(prompt_lines),
    }
