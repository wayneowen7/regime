from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
from typing import Any, Iterable

from regime_pilot.schema import load_jsonl


TEXT_CORE_FIELDS = [
    "case_id",
    "comment_id",
    "reddit_fullname",
    "subreddit",
    "split",
    "label",
    "expected_decision",
    "policy_card_id",
    "text",
    "body_sha256",
    "retrieval_source",
    "retrieved_at",
]


def write_json(path: str | Path, data: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _is_hydrated_with_text(record: dict[str, Any]) -> bool:
    return (
        record.get("text_status") == "hydrated"
        and record.get("hydration_status") == "hydrated"
        and isinstance(record.get("text"), str)
        and bool(str(record.get("text")).strip())
    )


def _text_core_record(record: dict[str, Any]) -> dict[str, Any]:
    output = {field: record.get(field) for field in TEXT_CORE_FIELDS}
    output["label"] = int(output["label"])
    output["expected_decision"] = str(output["expected_decision"])
    output["source_text_status"] = str(record.get("text_status"))
    return output


def _counter_to_dict(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def _nested_counts(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        counts[str(record.get("subreddit", "unknown"))][str(record.get("label", "unknown"))] += 1
    return {
        subreddit: _counter_to_dict(counter)
        for subreddit, counter in sorted(counts.items())
    }


def _label_targets(samples_per_subreddit: int) -> dict[str, int]:
    if samples_per_subreddit < 1:
        raise ValueError("samples_per_subreddit must be positive")
    allow_target = samples_per_subreddit // 2
    remove_target = samples_per_subreddit - allow_target
    return {"0": allow_target, "1": remove_target}


def _sample_records(records: list[dict[str, Any]], size: int, rng: random.Random) -> list[dict[str, Any]]:
    if size <= 0 or not records:
        return []
    if len(records) <= size:
        return sorted(records, key=lambda item: str(item.get("case_id", "")))
    return sorted(rng.sample(records, size), key=lambda item: str(item.get("case_id", "")))


def select_text_core_records(
    records: Iterable[dict[str, Any]],
    samples_per_subreddit: int,
    seed: int = 20260616,
    subreddits: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_records = list(records)
    requested_subreddits = subreddits or sorted({str(record.get("subreddit")) for record in source_records})
    wanted = set(requested_subreddits)
    hydrated = [
        _text_core_record(record)
        for record in source_records
        if str(record.get("subreddit")) in wanted and _is_hydrated_with_text(record)
    ]
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {
        subreddit: {"0": [], "1": []} for subreddit in requested_subreddits
    }
    for record in hydrated:
        label = str(record.get("label"))
        if label in {"0", "1"}:
            grouped[str(record["subreddit"])][label].append(record)

    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    shortfalls: dict[str, dict[str, dict[str, int]]] = {}
    targets = _label_targets(samples_per_subreddit)
    for subreddit in requested_subreddits:
        selected_for_subreddit: list[dict[str, Any]] = []
        label_shortfalls: dict[str, dict[str, int]] = {}
        for label, target in targets.items():
            available = grouped[subreddit][label]
            take = min(target, len(available))
            selected_for_subreddit.extend(_sample_records(available, take, rng))
            if take < target:
                label_shortfalls[label] = {
                    "requested": target,
                    "available": len(available),
                    "selected": take,
                }

        selected_ids = {str(record["case_id"]) for record in selected_for_subreddit}
        deficit = samples_per_subreddit - len(selected_for_subreddit)
        if deficit > 0:
            fillers = [
                record
                for label_records in grouped[subreddit].values()
                for record in label_records
                if str(record["case_id"]) not in selected_ids
            ]
            selected_for_subreddit.extend(_sample_records(fillers, deficit, rng))

        selected.extend(sorted(selected_for_subreddit, key=lambda item: str(item["case_id"])))
        if label_shortfalls:
            shortfalls[subreddit] = label_shortfalls

    source_status_counts = Counter(str(record.get("text_status", "unknown")) for record in source_records)
    summary = {
        "source_record_count": len(source_records),
        "source_status_counts": _counter_to_dict(source_status_counts),
        "available_hydrated_count": len(hydrated),
        "selected_count": len(selected),
        "samples_per_subreddit": samples_per_subreddit,
        "seed": seed,
        "requested_subreddits": requested_subreddits,
        "available_hydrated_by_subreddit_label": _nested_counts(hydrated),
        "selected_by_subreddit_label": _nested_counts(selected),
        "label_shortfalls": shortfalls,
        "contains_raw_text": False,
    }
    return selected, summary


def build_text_core_snapshot(
    raw_path: str | Path,
    output_path: str | Path,
    summary_path: str | Path,
    samples_per_subreddit: int = 25,
    seed: int = 20260616,
    subreddits: list[str] | None = None,
) -> dict[str, Any]:
    records = load_jsonl(raw_path)
    selected, summary = select_text_core_records(
        records,
        samples_per_subreddit=samples_per_subreddit,
        seed=seed,
        subreddits=subreddits,
    )
    summary["raw_path"] = str(raw_path)
    summary["output_path"] = str(output_path)
    summary["summary_path"] = str(summary_path)
    write_jsonl(output_path, selected)
    write_json(summary_path, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Reddit-Text-Core snapshot.")
    parser.add_argument("--raw", default="data/raw/reddit_bao_pullpush_full_stream.jsonl")
    parser.add_argument("--output", default="data/raw/reddit_text_core_v0.jsonl")
    parser.add_argument("--summary", default="pilot/results/reddit_text_core_v0_summary.json")
    parser.add_argument("--samples-per-subreddit", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20260616)
    parser.add_argument("--subreddits", nargs="+")
    args = parser.parse_args()

    summary = build_text_core_snapshot(
        raw_path=args.raw,
        output_path=args.output,
        summary_path=args.summary,
        samples_per_subreddit=args.samples_per_subreddit,
        seed=args.seed,
        subreddits=args.subreddits,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
