from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Protocol

from regime_pilot.ollama_client import OllamaClient
from regime_pilot.schema import load_jsonl


REDDIT_DECISIONS = {"allow", "remove"}
CONDITIONS = {"comment_only", "public_policy"}


class GenerationClient(Protocol):
    def generate(self, model: str, prompt: str) -> str:
        ...


def write_json(path: str | Path, data: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("No JSON object found")


def parse_reddit_decision(text: str) -> dict[str, Any]:
    try:
        parsed = _extract_json_object(text)
    except ValueError:
        return {"decision": "parse_error", "rationale": "", "raw_response": text}
    decision = str(parsed.get("decision", "parse_error"))
    if decision not in REDDIT_DECISIONS:
        decision = "parse_error"
    return {
        "decision": decision,
        "rationale": str(parsed.get("rationale", "")),
        "raw_response": text,
    }


def _policy_card_by_id(policy_cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(card["policy_card_id"]): card for card in policy_cards}


def _format_rule(rule: dict[str, Any]) -> str:
    parts = [
        str(rule.get("short_name", "")).strip(),
        str(rule.get("description", "")).strip(),
        str(rule.get("violation_reason", "")).strip(),
    ]
    return " | ".join(part for part in parts if part)


def _format_policy_context(policy_card: dict[str, Any]) -> str:
    comment_rules = [
        _format_rule(rule)
        for rule in policy_card.get("structured_comment_rules", [])
        if isinstance(rule, dict)
    ]
    if not comment_rules:
        comment_rules = [
            "No explicit structured comment rules were available; use subreddit description and site rules cautiously."
        ]
    site_rules = [str(rule) for rule in policy_card.get("site_rules", [])]
    lines = [
        f"subreddit: r/{policy_card.get('subreddit', '')}",
        f"title: {policy_card.get('title', '')}",
        "Comment rules:",
    ]
    lines.extend(f"- {rule}" for rule in comment_rules)
    if site_rules:
        lines.append("Site-wide rules:")
        lines.extend(f"- {rule}" for rule in site_rules)
    return "\n".join(lines)


def build_reddit_prompt(
    case: dict[str, Any],
    policy_card: dict[str, Any],
    condition: str,
) -> str:
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    policy_section = (
        "Policy context: not provided. Classify from the comment alone."
        if condition == "comment_only"
        else f"Policy context:\n{_format_policy_context(policy_card)}"
    )
    return f"""You are a Reddit comment moderation classifier.

Task:
- Decide whether the comment should be allowed or removed.
- Return JSON only.
- The "decision" value must be either "allow" or "remove".

{policy_section}

Comment:
subreddit: r/{case.get('subreddit')}
comment_id: {case.get('comment_id')}
text: {case.get('text')}

Required JSON schema:
{{"decision":"allow","rationale":"short reason"}}
"""


def _empty_summary() -> dict[str, Any]:
    return {
        "n": 0,
        "accuracy": 0.0,
        "parse_error_rate": 0.0,
        "expected_remove_rate": 0.0,
        "predicted_remove_rate": 0.0,
        "allow_accuracy": 0.0,
        "remove_accuracy": 0.0,
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return _empty_summary()
    expected_allow = [row for row in rows if row["expected_decision"] == "allow"]
    expected_remove = [row for row in rows if row["expected_decision"] == "remove"]

    def accuracy(subset: list[dict[str, Any]]) -> float:
        if not subset:
            return 0.0
        return sum(1 for row in subset if row["correct"]) / len(subset)

    return {
        "n": len(rows),
        "accuracy": sum(1 for row in rows if row["correct"]) / len(rows),
        "parse_error_rate": sum(1 for row in rows if row["model_decision"] == "parse_error") / len(rows),
        "expected_remove_rate": sum(1 for row in rows if row["expected_decision"] == "remove") / len(rows),
        "predicted_remove_rate": sum(1 for row in rows if row["model_decision"] == "remove") / len(rows),
        "allow_accuracy": accuracy(expected_allow),
        "remove_accuracy": accuracy(expected_remove),
    }


def _summaries_by_subreddit(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["subreddit"])].append(row)
    return {subreddit: summarize_rows(items) for subreddit, items in sorted(grouped.items())}


def _label_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row["expected_decision"]) for row in rows)
    return {key: counts[key] for key in sorted(counts)}


def run_reddit_text_benchmark(
    cases: list[dict[str, Any]],
    policy_cards: list[dict[str, Any]],
    client: GenerationClient,
    model: str,
    conditions: list[str],
    limit_cases: int | None = None,
) -> dict[str, Any]:
    if limit_cases is not None:
        cases = cases[:limit_cases]
    card_by_id = _policy_card_by_id(policy_cards)

    rows_by_condition: dict[str, list[dict[str, Any]]] = {}
    for condition in conditions:
        if condition not in CONDITIONS:
            raise ValueError(f"Unknown condition: {condition}")
        rows = []
        for case in cases:
            policy_card = card_by_id[str(case["policy_card_id"])]
            prompt = build_reddit_prompt(case, policy_card, condition)
            raw_response = client.generate(model=model, prompt=prompt)
            parsed = parse_reddit_decision(raw_response)
            expected = str(case["expected_decision"])
            row = {
                "case_id": str(case["case_id"]),
                "comment_id": str(case["comment_id"]),
                "subreddit": str(case["subreddit"]),
                "split": str(case.get("split", "")),
                "label": int(case["label"]),
                "policy_card_id": str(case["policy_card_id"]),
                "condition": condition,
                "expected_decision": expected,
                "model_decision": parsed["decision"],
                "correct": parsed["decision"] == expected,
                "rationale": parsed["rationale"],
                "raw_response": raw_response,
            }
            rows.append(row)
        rows_by_condition[condition] = rows

    summaries = {
        condition: summarize_rows(rows)
        for condition, rows in rows_by_condition.items()
    }
    text_free_summary = {
        "model": model,
        "conditions": conditions,
        "case_count": len(cases),
        "label_counts": _label_counts(rows_by_condition[conditions[0]]) if conditions else {},
        "summaries": summaries,
        "by_subreddit": {
            condition: _summaries_by_subreddit(rows)
            for condition, rows in rows_by_condition.items()
        },
        "contains_raw_text": False,
    }
    return {
        "model": model,
        "conditions": conditions,
        "rows": rows_by_condition,
        "summaries": summaries,
        "text_free_summary": text_free_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Reddit-Text-Core v0 benchmark.")
    parser.add_argument("--cases", default="data/raw/reddit_text_core_v0.jsonl")
    parser.add_argument("--policy-cards", default="pilot/data/reddit_bao/reddit_bao_policy_cards.json")
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--conditions", default="comment_only,public_policy")
    parser.add_argument("--limit-cases", type=int)
    parser.add_argument("--output-full", default="data/raw/reddit_text_benchmark_v0_full.json")
    parser.add_argument("--summary", default="pilot/results/reddit_text_benchmark_v0_summary.json")
    args = parser.parse_args()

    cases = load_jsonl(args.cases)
    policy_cards = json.loads(Path(args.policy_cards).read_text(encoding="utf-8"))
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    result = run_reddit_text_benchmark(
        cases=cases,
        policy_cards=policy_cards,
        client=OllamaClient(base_url=args.base_url),
        model=args.model,
        conditions=conditions,
        limit_cases=args.limit_cases,
    )
    write_json(args.output_full, result)
    write_json(args.summary, result["text_free_summary"])
    print(json.dumps(result["text_free_summary"], ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
