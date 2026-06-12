from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from regime_pilot.conditions import CONDITIONS, select_memories
from regime_pilot.evaluate import evaluate_retrieval, summarize_metrics
from regime_pilot.schema import load_jsonl, validate_precedent, validate_test_case


def run_pilot(
    policies_path: str | Path,
    precedents_path: str | Path,
    test_cases_path: str | Path,
    top_k: int,
) -> dict[str, Any]:
    Path(policies_path).read_text(encoding="utf-8")
    precedents = [validate_precedent(record) for record in load_jsonl(precedents_path)]
    test_cases = [validate_test_case(record) for record in load_jsonl(test_cases_path)]

    rows_by_condition: dict[str, list[dict[str, Any]]] = {}
    for condition in sorted(CONDITIONS):
        rows = []
        for test_case in test_cases:
            selected = select_memories(condition, test_case, precedents, top_k)
            row = evaluate_retrieval(test_case, selected)
            row["condition"] = condition
            rows.append(row)
        rows_by_condition[condition] = rows

    return {
        "top_k": top_k,
        "rows": rows_by_condition,
        "summaries": {
            condition: summarize_metrics(rows)
            for condition, rows in rows_by_condition.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policies", default="pilot/data/policies.json")
    parser.add_argument("--precedents", default="pilot/data/precedents.jsonl")
    parser.add_argument("--test-cases", default="pilot/data/test_cases.jsonl")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output", default="pilot/results/retrieval_metrics.json")
    args = parser.parse_args()

    result = run_pilot(
        policies_path=args.policies,
        precedents_path=args.precedents,
        test_cases_path=args.test_cases,
        top_k=args.top_k,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
