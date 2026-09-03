"""AI 架构评判：把研究分析文字提炼成统一的结构化架构 JSON。

两级流水线的"内容层"：无论主分析的架构文字是什么格式（markdown 列表、
ASCII 表格、流水账），都由一次独立的 LLM 评判调用规范成同一 schema：
    {
      "title": "总体架构名",
      "layers": [
        {"name": "层名", "modules": [{"name":"模块名","desc":"一句话"}], "formula":"可选公式"}
      ]
    }
最终 SVG 由前端确定性渲染引擎依据这份 JSON 决定，与 AI 文字排版无关。
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.inference.model_router import chat_with_fallback

ARCH_JSON_TAG = "ARCH_JSON"

_SYSTEM_PROMPT = (
    "你是一名严谨的科研论文图表审稿人。把用户给出的研究架构描述提炼成统一、"
    "规范、可直接绘图的 JSON 结构。只输出 JSON，不要任何解释。"
)

_USER_PROMPT_TEMPLATE = """请对下面的研究架构进行"评判式提炼"：去掉噪音、纠正重复与空泛，输出一份干净、专业、适合绘制科研架构图的 JSON。

要求：
1. 结构字段严格如下（不要增删字段）：
{{
  "title": "架构总名称（简短）",
  "layers": [
    {{
      "name": "层名（如 输入层 / 特征融合 / 编码器 / LLM 推理层 / 决策层 / 反馈层）",
      "modules": [
        {{"name": "模块名（简短）", "desc": "一句话作用，可为空字符串"}}
      ],
      "formula": "该层核心公式或表达式；无则留空字符串"
    }}
  ]
}}
2. 层按数据流从上到下排序，3~6 层最合适；不要超过 8 层。
3. 每层 1~6 个模块；模块名要具体（如"跨模态注意力"、"Prompt-as-Prefix"），不要写空话。
4. 公式用 ASCII/LaTeX 简写（如 F = concat(F1, F2, ...)；Y = LightGPT(X, P)；theta = theta + alpha*dL）。
5. 合并同名层、去掉没有内容的空层；从原文提取真实模块，不要臆造。
6. 用 <{tag}>...</{tag}> 包裹 JSON，例如：
<{tag}>
{{"title": "...", "layers": [...]}}
</{tag}>

研究架构原文如下：
----- 原文开始 -----
{{analysis}}
----- 原文结束 -----
"""


def _extract_arch_json(content: str) -> dict[str, Any] | None:
    """从模型输出里提取 JSON：优先 <ARCH_JSON> 包裹，再兜底全 JSON 对象。"""
    if not content:
        return None
    # 优先：包裹标签
    m = re.search(r"<" + ARCH_JSON_TAG + r">\s*(\{.*?\})\s*</" + ARCH_JSON_TAG + r">", content, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            pass
    # 兜底：第一个 { ... } 完整对象（花括号配平）
    start = content.find("{")
    if start >= 0:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(content)):
            ch = content[i]
            if esc:
                esc = False
                continue
            if ch == "\\" and in_str:
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
            elif not in_str:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(content[start : i + 1])
                        except (json.JSONDecodeError, ValueError):
                            return None
    return None


def _clean_text(value: Any, limit: int = 60) -> str:
    if not isinstance(value, str):
        return ""
    text = re.sub(r"\s+", " ", value).strip()
    return text[:limit]


def _normalize_arch(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    """校验并规范化 JSON：剔空层、限层数与模块数、保证字段形状。"""
    if not isinstance(raw, dict):
        return None
    title = _clean_text(raw.get("title") or "研究架构", 40)
    raw_layers = raw.get("layers")
    if not isinstance(raw_layers, list):
        return None

    layers: list[dict[str, Any]] = []
    for item in raw_layers:
        if not isinstance(item, dict):
            continue
        name = _clean_text(item.get("name"), 30)
        if not name:
            continue
        modules: list[dict[str, str]] = []
        raw_modules = item.get("modules")
        if isinstance(raw_modules, list):
            for mod in raw_modules:
                if isinstance(mod, dict):
                    mname = _clean_text(mod.get("name"), 24)
                    if not mname:
                        continue
                    desc = _clean_text(mod.get("desc"), 80)
                    modules.append({"name": mname, "desc": desc})
        formula = _clean_text(item.get("formula"), 80)
        if not modules and not formula:
            continue  # 剔除空层
        layers.append({"name": name, "modules": modules, "formula": formula})
        if len(layers) >= 8:
            break

    if not layers:
        return None
    # 每层最多 8 个模块
    for layer in layers:
        layer["modules"] = layer["modules"][:8]
    return {"title": title, "layers": layers}


async def judge_architecture(
    knowledge_text: str,
    analysis_text: str,
) -> dict[str, Any] | None:
    """AI 中间评判：把主分析提炼成统一架构 JSON。失败返回 None（前端文字兜底）。"""
    analysis_snippet = (analysis_text or "")[:6000]
    if not analysis_snippet.strip():
        return None
    prompt = _USER_PROMPT_TEMPLATE.format(
        tag=ARCH_JSON_TAG,
        analysis=analysis_snippet,
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    try:
        routed = await chat_with_fallback(
            task="analysis",
            messages=messages,
            temperature=0.2,
            max_tokens=2048,
        )
        return _normalize_arch(_extract_arch_json(routed.content))
    except Exception:  # noqa: BLE001 - 评判失败不影响主流程
        return None
