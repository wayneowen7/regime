from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Protocol

from regime_pilot.conditions import select_memories
from regime_pilot.llm_pilot import (
    MEMORY_VIEWS,
    POLICY_VIEWS,
    build_agent_prompt,
    evaluate_agent_output,
    parse_agent_output,
)
from regime_pilot.ollama_client import OllamaClient
from regime_pilot.schema import load_jsonl, validate_precedent, validate_test_case


class GenerationClient(Protocol):
    def generate(self, model: str, prompt: str) -> str:
        ...


def summarize_agent_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "n": 0,
            "policy_adherence_rate": 0.0,
            "decision_family_adherence_rate": 0.0,
            "mean_invalid_used_precedents": 0.0,
            "mean_unknown_used_precedents": 0.0,
            "mean_stale_rationale_matches": 0.0,
            "parse_error_rate": 0.0,
        }
    return {
        "n": len(rows),
        "policy_adherence_rate": sum(1 for row in rows if row["policy_adherence"]) / len(rows),
        "decision_family_adherence_rate": (
            sum(1 for row in rows if row["decision_family_adherence"]) / len(rows)
        ),
        "mean_invalid_used_precedents": (
            sum(row["invalid_used_precedent_count"] for row in rows) / len(rows)
        ),
        "mean_unknown_used_precedents": (
            sum(row["unknown_used_precedent_count"] for row in rows) / len(rows)
        ),
        "mean_stale_rationale_matches": (
            sum(row["stale_rationale_match_count"] for row in rows) / len(rows)
        ),
        "parse_error_rate": sum(1 for row in rows if row["model_decision"] == "parse_error") / len(rows),
    }


def run_llm_pilot(
    policies_path: str | Path,
    precedents_path: str | Path,
    test_cases_path: str | Path,
    client: GenerationClient,
    model: str,
    conditions: list[str],
    top_k: int,
    limit_cases: int | None = None,
    memory_view: str = "transparent",
    policy_view: str = "full",
    stale_warning: bool = True,
) -> dict[str, Any]:
    policies = json.loads(Path(policies_path).read_text(encoding="utf-8"))
    precedents = [validate_precedent(record) for record in load_jsonl(precedents_path)]
    test_cases = [validate_test_case(record) for record in load_jsonl(test_cases_path)]
    if limit_cases is not None:
        test_cases = test_cases[:limit_cases]

    rows_by_condition: dict[str, list[dict[str, Any]]] = {}
    for condition in conditions:
        rows = []
        for test_case in test_cases:
            selected = select_memories(condition, test_case, precedents, top_k)
            policy = policies[test_case.active_regime_id]
            prompt = build_agent_prompt(
                policy,
                test_case,
                selected,
                memory_view=memory_view,
                policy_view=policy_view,
                stale_warning=stale_warning,
            )
            raw_response = client.generate(model=model, prompt=prompt)
            output = parse_agent_output(raw_response)
            row = evaluate_agent_output(test_case, selected, output)
            row["condition"] = condition
            row["retrieved_case_ids"] = [item.precedent.case_id for item in selected]
            row["raw_response"] = raw_response
            rows.append(row)
        rows_by_condition[condition] = rows

    return {
        "model": model,
        "top_k": top_k,
        "memory_view": memory_view,
        "policy_view": policy_view,
        "stale_warning": stale_warning,
        "conditions": conditions,
        "rows": rows_by_condition,
        "summaries": {
            condition: summarize_agent_rows(rows)
            for condition, rows in rows_by_condition.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policies", default="pilot/data/policies.json")
    parser.add_argument("--precedents", default="pilot/data/precedents.jsonl")
    parser.add_argument("--test-cases", default="pilot/data/test_cases.jsonl")
    parser.add_argument("--model", default="llama3.2:latest")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--conditions", default="policy_only,naive_memory,regime_aware")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--limit-cases", type=int, default=3)
    parser.add_argument("--memory-view", choices=sorted(MEMORY_VIEWS), default="transparent")
    parser.add_argument("--policy-view", choices=sorted(POLICY_VIEWS), default="full")
    parser.add_argument("--stale-warning", choices=["on", "off"], default="on")
    parser.add_argument("--output", default="pilot/results/llm_pilot_smoke.json")
    args = parser.parse_args()

    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    result = run_llm_pilot(
        policies_path=args.policies,
        precedents_path=args.precedents,
        test_cases_path=args.test_cases,
        client=OllamaClient(base_url=args.base_url),
        model=args.model,
        conditions=conditions,
        top_k=args.top_k,
        limit_cases=args.limit_cases,
        memory_view=args.memory_view,
        policy_view=args.policy_view,
        stale_warning=args.stale_warning == "on",
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
