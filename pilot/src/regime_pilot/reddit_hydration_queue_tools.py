from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable

from regime_pilot.schema import load_jsonl


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


def _latest_by_comment_id(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        comment_id = record.get("comment_id")
        if comment_id:
            latest[str(comment_id)] = record
    return latest


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def build_priority_queue(
    queue_records: Iterable[dict[str, Any]],
    resolved_records: Iterable[dict[str, Any]],
    label: int | None = None,
    include_statuses: list[str] | None = None,
    include_unseen: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    include_status_set = set(include_statuses or ["error", "missing", "subreddit_mismatch"])
    resolved_by_id = _latest_by_comment_id(resolved_records)
    selected: list[dict[str, Any]] = []
    selected_reasons: Counter[str] = Counter()
    skipped_statuses: Counter[str] = Counter()
    skipped_hydrated_count = 0
    label_seen_count = 0

    for item in queue_records:
        if label is not None and int(item.get("label")) != label:
            continue
        label_seen_count += 1
        comment_id = str(item["comment_id"])
        resolved = resolved_by_id.get(comment_id)
        if resolved is None:
            if include_unseen:
                selected.append(dict(item))
                selected_reasons["not_seen"] += 1
            continue

        status = str(resolved.get("text_status", "unknown"))
        if status == "hydrated":
            skipped_hydrated_count += 1
            continue
        if status in include_status_set:
            selected.append(dict(item))
            selected_reasons[status] += 1
        else:
            skipped_statuses[status] += 1

    summary = {
        "source_queue_count": label_seen_count,
        "resolved_record_count": len(resolved_by_id),
        "label_filter": label,
        "include_statuses": sorted(include_status_set),
        "include_unseen": include_unseen,
        "selected_count": len(selected),
        "selected_reason_counts": _counter_dict(selected_reasons),
        "skipped_hydrated_count": skipped_hydrated_count,
        "skipped_status_counts": _counter_dict(skipped_statuses),
        "contains_raw_text": False,
    }
    return selected, summary


def build_priority_queue_files(
    queue_path: str | Path,
    resolved_path: str | Path,
    output_path: str | Path,
    summary_path: str | Path,
    label: int | None = None,
    include_statuses: list[str] | None = None,
    include_unseen: bool = True,
) -> dict[str, Any]:
    selected, summary = build_priority_queue(
        queue_records=load_jsonl(queue_path),
        resolved_records=load_jsonl(resolved_path),
        label=label,
        include_statuses=include_statuses,
        include_unseen=include_unseen,
    )
    summary["queue_path"] = str(queue_path)
    summary["resolved_path"] = str(resolved_path)
    summary["output_path"] = str(output_path)
    summary["summary_path"] = str(summary_path)
    write_jsonl(output_path, selected)
    write_json(summary_path, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build priority hydration queues from current resolved output.")
    parser.add_argument("--queue", default="pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl")
    parser.add_argument("--resolved", default="data/raw/reddit_bao_pullpush_full_stream.jsonl")
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--label", type=int)
    parser.add_argument("--include-statuses", nargs="+", default=["error", "missing", "subreddit_mismatch"])
    parser.add_argument("--exclude-unseen", action="store_true")
    args = parser.parse_args()

    summary = build_priority_queue_files(
        queue_path=args.queue,
        resolved_path=args.resolved,
        output_path=args.output,
        summary_path=args.summary,
        label=args.label,
        include_statuses=args.include_statuses,
        include_unseen=not args.exclude_unseen,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
