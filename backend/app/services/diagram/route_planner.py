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
      "gate": "one short continue/revise/stop criterion",
      "evidence_status": "grounded" | "partial" | "unverified",
      "evidence_note": "one short Chinese sentence: does this stage's tasks have direct support in the knowledge items? grounded = fully supported, partial = some supported, unverified = planning guess needing literature verification"
    }}
  ]
}}

Rules:
- 5 stages exactly, ordered by research progression
- Stage names and tasks MUST reflect the actual research content (method,
  datasets, models from knowledge items); do not invent unrelated tasks
- Tasks are short English phrases (3-5 words), to be rendered in a diagram
- The final stage is paper writing
- No numeric results in task labels
- evidence_status must be honest: mark "unverified" for stages that are pure
  planning actions (literature search, drafting) with no direct knowledge
  support; mark "grounded"/"partial" when knowledge items already cover the
  method/datasets/results. Chinese knowledge items are the ground truth."""


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
            # evidence_status：优先采用 LLM 标注，非法/缺失时交给规则兜底
            status = s.get("evidence_status")
            if status not in ("grounded", "partial", "unverified"):
                s["evidence_status"] = None
            if not isinstance(s.get("evidence_note"), str) or not s["evidence_note"]:
                s["evidence_note"] = ""
        current = plan.get("current_stage")
        if not isinstance(current, int) or not (1 <= current <= 5):
            plan["current_stage"] = 1
        # 时效性/幻觉防线：补齐缺失的标注（LLM 未标注的用规则兜底）
        plan["stages"] = _annotate_evidence_status(stages, knowledge_text)
        return plan
    except (json.JSONDecodeError, ValueError, AttributeError) as exc:
        logger.warning("Stage planning failed: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - 规划失败必须降级而非中断
        logger.warning("Stage planning error: %s", exc)
        return None


# ---------------------------------------------------------------------------
# 时效性 / 幻觉防线
# ---------------------------------------------------------------------------

# 常见"动作性"任务词（提示这是规划动作，而非来自知识库的既有结论）
_PLANNING_ACTION_WORDS = {
    "search", "build", "design", "plan", "run", "compare", "draft", "write",
    "collect", "construct", "implement", "train", "evaluate", "assess",
    "review", "gather", "define", "identify", "select", "develop", "verify",
    "survey", "explore", "prepare", "organize", "red-team", "baseline",
}

# 通用科研名词（出现在任务里但不应被当作"已验证结论"）
_GENERIC_SCI_TERMS = {
    "data", "dataset", "model", "method", "result", "paper", "literature",
    "experiment", "ablation", "mechanism", "question", "problem", "approach",
    "framework", "system", "feature", "task", "research", "baseline",
    "prediction", "forecast", "traffic", "network", "graph", "attention",
}

# 中文知识库中的"证据性"信号词：出现这些词说明知识库包含实质结论/数据/实验
_KB_EVIDENCE_ZH = (
    "实验", "结果", "数据", "验证", "消融", "评估", "精度", "误差",
    "性能", "对比", "测试", "指标", "提升", "效果", "结论", "准确性",
    "鲁棒", "benchmark", "baseline", "accuracy", "result", "dataset",
    "experiment", "evaluation", "performance", "improve", "ablation",
)


def _tokenize(text: str) -> set[str]:
    """小写化并抽取英文单词。"""
    import re

    return set(re.findall(r"[a-z][a-z0-9-]{2,}", text.lower()))


def _has_zh_evidence(knowledge_text: str) -> bool:
    """知识库是否包含证据性内容（实验/数据/结果等信号词）。"""
    if not knowledge_text:
        return False
    lower = knowledge_text.lower()
    return any(sig in lower for sig in _KB_EVIDENCE_ZH)


def _annotate_evidence_status(
    stages: List[Dict[str, Any]],
    knowledge_text: str,
) -> List[Dict[str, Any]]:
    """
    补齐每个阶段的 evidence_status / evidence_note。

    优先保留 LLM 的标注；仅对缺失（None/空）的阶段做规则兜底：
      - 知识库为空 → unverified
      - 知识库含证据信号词 → partial（至少部分有据）
      - 否则 → unverified
    该函数是防线的一部分：即使 LLM 未标注，路线仍带风险提示。
    """
    kb_has_evidence = _has_zh_evidence(knowledge_text)
    kb_tokens = _tokenize(knowledge_text or "")
    domain_terms = (kb_tokens - _GENERIC_SCI_TERMS - _PLANNING_ACTION_WORDS) if kb_tokens else set()

    for s in stages:
        status = s.get("evidence_status")
        if status in ("grounded", "partial", "unverified"):
            # LLM 已标注
            if not s.get("evidence_note"):
                s["evidence_note"] = (
                    "全部任务有知识库支撑"
                    if status == "grounded"
                    else "部分任务为规划推测，结论时效性需文献验证"
                    if status == "partial"
                    else "本阶段以规划动作为主，具体结论需验证文献与实验"
                )
            continue

        # 规则兜底
        if not knowledge_text or not kb_has_evidence:
            s["evidence_status"] = "unverified"
            s["evidence_note"] = (
                "知识库为空或缺少证据性内容，本阶段结论需自行检索文献验证"
                if not kb_has_evidence
                else "知识库为空，全部阶段为规划性推测，需自行文献验证"
            )
            continue

        # 知识库有证据：任务是否含知识库英文技术词
        hit = False
        for t in s.get("tasks", []):
            content_words = _tokenize(t) - _PLANNING_ACTION_WORDS - _GENERIC_SCI_TERMS
            if content_words and (content_words & domain_terms):
                hit = True
                break
        if hit:
            s["evidence_status"] = "grounded"
            s["evidence_note"] = "任务涉及知识库已覆盖的技术内容，结论有据可查"
        else:
            s["evidence_status"] = "partial"
            s["evidence_note"] = "知识库含证据性内容，但本阶段任务偏规划动作，时效性需复核"
    return stages


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
            "stages": _annotate_evidence_status(
                _fallback_stages(route_title, knowledge_text), knowledge_text
            ),
        }

    # 整体时效性 / 幻觉防线报告
    stages = plan["stages"]
    grounded_n = sum(1 for s in stages if s.get("evidence_status") == "grounded")
    partial_n = sum(1 for s in stages if s.get("evidence_status") == "partial")
    total = len(stages) or 1
    if grounded_n == total:
        plan["evidence_summary"] = "全部阶段均有知识库支撑，可执行度高；仍建议在写作前对文献时效性做一次复核。"
    elif grounded_n + partial_n >= total * 0.6:
        plan["evidence_summary"] = (
            f"{grounded_n}/{total} 个阶段有知识库支撑、{partial_n}/{total} 个部分支撑；"
            "多数结论可落地，但部分推测性结论需补充文献验证以控制时效性风险。"
        )
    else:
        plan["evidence_summary"] = (
            f"仅 {grounded_n}/{total} 个阶段有知识库支撑。当前路线以规划推测为主，"
            "存在时效性与幻觉风险：请优先检索近 1-2 年文献核验各阶段方法可行性。"
        )

    # 组装渲染层提示词（roadmap 布局，纯描述）
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
