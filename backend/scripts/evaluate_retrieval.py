"""命令行离线评测：python scripts/evaluate_retrieval.py gold.json predictions.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.evaluation import evaluate_cases, load_cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate academic retrieval predictions")
    parser.add_argument("gold", help="PaSa-style or generic JSON/JSONL gold file")
    parser.add_argument("predictions", help="ScholarNova or PaSa-style prediction file")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()

    report = evaluate_cases(load_cases(args.gold), load_cases(args.predictions))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
