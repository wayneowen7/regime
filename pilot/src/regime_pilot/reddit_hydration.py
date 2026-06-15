from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from regime_pilot.schema import load_jsonl


class MissingRedditCredentials(RuntimeError):
    pass


def _write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def make_reddit_client_from_env(env: Mapping[str, str] | None = None):
    values = os.environ if env is None else env
    missing = [
        name
        for name in ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]
        if not values.get(name)
    ]
    if missing:
        raise MissingRedditCredentials(
            "Missing Reddit API credentials: " + ", ".join(missing)
        )

    try:
        import praw
    except ImportError as exc:
        raise RuntimeError(
            "PRAW is required for hydration. Install praw in the active Python environment."
        ) from exc

    return praw.Reddit(
        client_id=values["REDDIT_CLIENT_ID"],
        client_secret=values["REDDIT_CLIENT_SECRET"],
        user_agent=values["REDDIT_USER_AGENT"],
    )


def _comment_to_record(queue_item: dict[str, Any], comment: Any) -> dict[str, Any]:
    output = dict(queue_item)
    output["text"] = getattr(comment, "body", None)
    output["text_status"] = "hydrated"
    output["hydration_status"] = "hydrated"
    output["permalink"] = getattr(comment, "permalink", None)
    output["author"] = str(getattr(comment, "author", None)) if getattr(comment, "author", None) else None
    output["created_utc"] = getattr(comment, "created_utc", None)
    return output


def _error_record(queue_item: dict[str, Any], exc: Exception) -> dict[str, Any]:
    output = dict(queue_item)
    output["text"] = None
    output["text_status"] = "hydrate_error"
    output["hydration_status"] = "failed"
    output["hydration_error"] = str(exc)
    return output


def hydrate_queue(
    queue_records: Iterable[dict[str, Any]],
    output_path: str | Path,
    reddit_client: Any,
    limit: int | None = None,
) -> dict[str, int]:
    hydrated_records: list[dict[str, Any]] = []
    counts = {"attempted": 0, "hydrated": 0, "failed": 0}
    for item in queue_records:
        if limit is not None and counts["attempted"] >= limit:
            break
        counts["attempted"] += 1
        try:
            comment = reddit_client.comment(id=item["comment_id"])
            hydrated_records.append(_comment_to_record(item, comment))
            counts["hydrated"] += 1
        except Exception as exc:  # External API failures should not lose batch state.
            hydrated_records.append(_error_record(item, exc))
            counts["failed"] += 1
    _write_jsonl(output_path, hydrated_records)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Hydrate Reddit comment ids with PRAW.")
    parser.add_argument("--queue", default="pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl")
    parser.add_argument("--output", default="data/raw/reddit_bao_hydrated_comments.jsonl")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    queue_records = load_jsonl(args.queue)
    reddit_client = make_reddit_client_from_env()
    summary = hydrate_queue(
        queue_records=queue_records,
        output_path=args.output,
        reddit_client=reddit_client,
        limit=args.limit,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
