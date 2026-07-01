"""兼容 PaSa 风格和通用论文检索结果的轻量离线评测。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable


def normalize_paper_key(value: Any) -> str:
    """统一 DOI、标题和 ID，降低格式差异导致的假阴性。"""
    if isinstance(value, dict):
        value = (
            value.get("corpus_id")
            or value.get("paper_id")
            or value.get("title")
            or value.get("doi")
            or value.get("id")
            or ""
        )
    text = str(value or "").lower().replace("https://doi.org/", "")
    return re.sub(r"[^a-z0-9]+", "", text)


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    """读取 JSON 数组、JSONL 或以 case id 为键的 JSON 对象。"""
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    if file_path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in content.splitlines() if line.strip()]
    data = json.loads(content)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return data["data"]
    if isinstance(data, dict):
        return [
            {"case_id": key, **value} if isinstance(value, dict)
            else {"case_id": key, "answers": value}
            for key, value in data.items()
        ]
    raise ValueError(f"Unsupported benchmark format: {type(data).__name__}")


def _case_id(case: dict[str, Any], index: int) -> str:
    nested_input = case.get("input") if isinstance(case.get("input"), dict) else {}
    return str(
        case.get("case_id")
        or case.get("id")
        or case.get("query_id")
        or case.get("qid")
        or case.get("question_id")
        or nested_input.get("query_id")
        or index
    )


def _as_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (set, tuple)):
        return list(value)
    return [value]


def extract_gold(case: dict[str, Any]) -> set[str]:
    """抽取 PaSa extra.answer 及常见 benchmark gold 字段。"""
    extra = case.get("extra") if isinstance(case.get("extra"), dict) else {}
    criteria = (
        case.get("scorer_criteria")
        if isinstance(case.get("scorer_criteria"), dict)
        else {}
    )
    value = (
        extra.get("answer")
        or criteria.get("known_to_be_good")
        or criteria.get("corpus_ids")
        or case.get("answers")
        or case.get("answer")
        or case.get("relevant_papers")
        or case.get("gold_papers")
        or case.get("gold")
        or []
    )
    return {key for item in _as_items(value) if (key := normalize_paper_key(item))}


def _walk_pasa_tree(root: dict[str, Any]) -> Iterable[dict[str, Any]]:
    queue = [root]
    while queue:
        node = queue.pop(0)
        children = node.get("child", {})
        if not isinstance(children, dict):
            continue
        for branch in children.values():
            for paper in _as_items(branch):
                if isinstance(paper, dict):
                    yield paper
                    queue.append(paper)


def extract_predictions(case: dict[str, Any]) -> list[str]:
    """抽取本项目平铺结果或 PaSa crawler 树，并保留排序。"""
    value = (
        case.get("results")
        or case.get("papers")
        or case.get("predictions")
        or case.get("retrieved_papers")
    )
    items = _as_items(value)
    if not items and "child" in case:
        items = sorted(
            _walk_pasa_tree(case),
            key=lambda item: float(item.get("select_score", 0)),
            reverse=True,
        )
    result: list[str] = []
    seen = set()
    for item in items:
        key = normalize_paper_key(item)
        if key and key not in seen:
            seen.add(key)
            result.append(key)
    return result


def evaluate_cases(
    gold_cases: list[dict[str, Any]],
    prediction_cases: list[dict[str, Any]],
    cutoffs: tuple[int, ...] = (20, 50, 100),
) -> dict[str, Any]:
    """计算 micro F1/Precision/Recall、Recall@K 和平均运行成本。"""
    predictions_by_id = {
        _case_id(case, index): case for index, case in enumerate(prediction_cases)
    }
    tp = fp = fn = 0
    recall_hits = dict.fromkeys(cutoffs, 0)
    gold_total = 0
    evaluated = 0
    api_calls = latency_ms = tokens = 0.0

    for index, gold_case in enumerate(gold_cases):
        gold = extract_gold(gold_case)
        if not gold:
            continue
        prediction_case = predictions_by_id.get(_case_id(gold_case, index), {})
        predicted = extract_predictions(prediction_case)
        predicted_set = set(predicted)
        hits = len(predicted_set & gold)
        tp += hits
        fp += len(predicted_set - gold)
        fn += len(gold - predicted_set)
        gold_total += len(gold)
        evaluated += 1
        for cutoff in cutoffs:
            recall_hits[cutoff] += len(set(predicted[:cutoff]) & gold)

        runtime = prediction_case.get("runtime_metrics", {})
        api_calls += float(runtime.get("api_calls", prediction_case.get("api_calls", 0)) or 0)
        latency_ms += float(runtime.get("latency_ms", prediction_case.get("latency_ms", 0)) or 0)
        usage = runtime.get("token_usage", prediction_case.get("token_usage", {})) or {}
        tokens += float(usage.get("total_tokens", 0) or 0)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    denominator = evaluated or 1
    return {
        "cases": evaluated,
        "micro": {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        },
        "recall_at_k": {
            str(cutoff): round(recall_hits[cutoff] / gold_total, 6) if gold_total else 0.0
            for cutoff in cutoffs
        },
        "efficiency": {
            "avg_api_calls": round(api_calls / denominator, 3),
            "avg_latency_ms": round(latency_ms / denominator, 3),
            "avg_total_tokens": round(tokens / denominator, 3),
        },
    }
