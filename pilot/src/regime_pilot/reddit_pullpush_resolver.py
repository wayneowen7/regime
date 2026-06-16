from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from regime_pilot.schema import load_jsonl


PULLPUSH_ENDPOINT = "https://api.pullpush.io/reddit/search/comment/"
DEFAULT_USER_AGENT = "regime-research-pullpush-resolver/0.1"
UNAVAILABLE_BODIES = {"", "[deleted]", "[removed]"}


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


def append_jsonl_record(handle: Any, record: dict[str, Any]) -> None:
    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    handle.flush()


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def body_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def pullpush_fetcher(
    comment_id: str,
    timeout: float = 20.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, Any]:
    url = f"{PULLPUSH_ENDPOINT}?ids={quote(comment_id)}"
    request = Request(url, headers={"User-Agent": user_agent})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        raise RuntimeError(f"PullPush HTTP {exc.code} for {comment_id}") from exc
    except URLError as exc:
        raise RuntimeError(f"PullPush URL error for {comment_id}: {exc.reason}") from exc
    return json.loads(payload)


def _base_record(queue_item: dict[str, Any], retrieved_at: str) -> dict[str, Any]:
    output = dict(queue_item)
    output["retrieval_source"] = "pullpush"
    output["retrieved_at"] = retrieved_at
    output["text"] = None
    output["body_sha256"] = None
    output["subreddit_match"] = None
    output["returned_subreddit"] = None
    return output


def _first_comment(pullpush_payload: dict[str, Any]) -> dict[str, Any] | None:
    data = pullpush_payload.get("data", [])
    if not isinstance(data, list) or not data:
        return None
    first = data[0]
    if not isinstance(first, dict):
        return None
    return first


def resolve_pullpush_record(
    queue_item: dict[str, Any],
    pullpush_payload: dict[str, Any],
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    timestamp = retrieved_at or utc_now_iso()
    output = _base_record(queue_item, timestamp)
    comment = _first_comment(pullpush_payload)
    if comment is None:
        output["text_status"] = "missing"
        output["hydration_status"] = "failed"
        output["hydration_error"] = "No PullPush data for comment id"
        return output

    returned_subreddit = str(comment.get("subreddit", ""))
    expected_subreddit = str(queue_item.get("subreddit", ""))
    output["returned_subreddit"] = returned_subreddit
    output["subreddit_match"] = returned_subreddit.lower() == expected_subreddit.lower()
    output["pullpush_created_utc"] = comment.get("created_utc")
    output["pullpush_author"] = comment.get("author")
    output["pullpush_permalink"] = comment.get("permalink")

    body = str(comment.get("body") or "").strip()
    if not output["subreddit_match"]:
        output["text_status"] = "subreddit_mismatch"
        output["hydration_status"] = "failed"
        output["hydration_error"] = (
            f"Expected subreddit {expected_subreddit}, got {returned_subreddit}"
        )
        return output

    if body in UNAVAILABLE_BODIES:
        output["text_status"] = "unavailable"
        output["hydration_status"] = "failed"
        output["hydration_error"] = "PullPush body is deleted, removed, or empty"
        return output

    output["text"] = body
    output["body_sha256"] = body_hash(body)
    output["text_status"] = "hydrated"
    output["hydration_status"] = "hydrated"
    return output


def summarize_resolved_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(str(record.get("text_status", "unknown")) for record in records)
    subreddit_counts = Counter(str(record.get("subreddit", "unknown")) for record in records)
    source_counts = Counter(str(record.get("retrieval_source", "unknown")) for record in records)
    error_counts = Counter(
        str(record.get("hydration_error"))
        for record in records
        if record.get("hydration_error")
    )
    status_by_subreddit: dict[str, Counter[str]] = {}
    for record in records:
        subreddit = str(record.get("subreddit", "unknown"))
        status = str(record.get("text_status", "unknown"))
        status_by_subreddit.setdefault(subreddit, Counter())[status] += 1
    hydrated = status_counts.get("hydrated", 0)
    record_count = len(records)
    return {
        "record_count": record_count,
        "hydrated_count": hydrated,
        "hydrated_rate": hydrated / record_count if record_count else 0.0,
        "status_counts": dict(sorted(status_counts.items())),
        "subreddit_counts": dict(sorted(subreddit_counts.items())),
        "retrieval_source_counts": dict(sorted(source_counts.items())),
        "error_counts": dict(sorted(error_counts.items())),
        "status_by_subreddit": {
            subreddit: dict(sorted(counts.items()))
            for subreddit, counts in sorted(status_by_subreddit.items())
        },
    }


def _record_key(record: dict[str, Any]) -> str:
    for field in ("comment_id", "reddit_fullname", "case_id"):
        value = record.get(field)
        if value:
            return f"{field}:{value}"
    return json.dumps(record, ensure_ascii=False, sort_keys=True)


def _load_existing_records(path: str | Path) -> list[dict[str, Any]]:
    output_path = Path(path)
    if not output_path.exists():
        return []
    return load_jsonl(output_path)


def _summary_with_metadata(
    records: list[dict[str, Any]],
    output_path: str | Path,
    summary_path: str | Path,
    timestamp: str,
    max_retries: int,
    streaming: bool,
    resume: bool,
    processed_existing_count: int,
    skipped_existing_count: int,
    processed_new_count: int,
    pending_count: int,
) -> dict[str, Any]:
    summary = summarize_resolved_records(records)
    summary["output_path"] = str(output_path)
    summary["summary_path"] = str(summary_path)
    summary["retrieved_at"] = timestamp
    summary["contains_raw_text"] = False
    summary["max_retries"] = max_retries
    summary["streaming"] = streaming
    summary["resume"] = resume
    summary["processed_existing_count"] = processed_existing_count
    summary["skipped_existing_count"] = skipped_existing_count
    summary["processed_new_count"] = processed_new_count
    summary["pending_count"] = pending_count
    return summary


def _resolve_one_record(
    item: dict[str, Any],
    fetcher: Callable[[str], dict[str, Any]],
    timestamp: str,
    max_retries: int,
    retry_sleep_seconds: float,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            payload = fetcher(str(item["comment_id"]))
            record = resolve_pullpush_record(item, payload, retrieved_at=timestamp)
            record["fetch_attempts"] = attempt + 1
            return record
        except Exception as exc:
            last_error = exc
            if attempt < max_retries and retry_sleep_seconds > 0:
                time.sleep(retry_sleep_seconds)

    record = _base_record(item, timestamp)
    record["text_status"] = "error"
    record["hydration_status"] = "failed"
    record["hydration_error"] = str(last_error)
    record["fetch_attempts"] = max_retries + 1
    return record


def resolve_queue(
    queue_records: Iterable[dict[str, Any]],
    fetcher: Callable[[str], dict[str, Any]],
    output_path: str | Path,
    summary_path: str | Path,
    limit: int | None = None,
    sleep_seconds: float = 0.0,
    max_retries: int = 0,
    retry_sleep_seconds: float = 1.0,
    retrieved_at: str | None = None,
    resume: bool = False,
    stream: bool = False,
    checkpoint_every: int = 50,
) -> dict[str, Any]:
    queue_list = list(queue_records)
    if limit is not None:
        queue_list = queue_list[:limit]

    timestamp = retrieved_at or utc_now_iso()

    use_streaming_writes = stream or resume
    existing_records = _load_existing_records(output_path) if resume else []
    existing_keys = {_record_key(record) for record in existing_records}
    records: list[dict[str, Any]] = list(existing_records)
    processed_existing_count = len(existing_records)
    skipped_existing_count = 0
    processed_new_count = 0

    def build_summary() -> dict[str, Any]:
        pending_count = max(len(queue_list) - skipped_existing_count - processed_new_count, 0)
        return _summary_with_metadata(
            records=records,
            output_path=output_path,
            summary_path=summary_path,
            timestamp=timestamp,
            max_retries=max_retries,
            streaming=use_streaming_writes,
            resume=resume,
            processed_existing_count=processed_existing_count,
            skipped_existing_count=skipped_existing_count,
            processed_new_count=processed_new_count,
            pending_count=pending_count,
        )

    output_file_path = Path(output_path)
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    stream_handle = None
    if use_streaming_writes:
        stream_handle = output_file_path.open("a" if resume else "w", encoding="utf-8", newline="\n")

    try:
        for item in queue_list:
            if _record_key(item) in existing_keys:
                skipped_existing_count += 1
                continue

            record = _resolve_one_record(
                item=item,
                fetcher=fetcher,
                timestamp=timestamp,
                max_retries=max_retries,
                retry_sleep_seconds=retry_sleep_seconds,
            )
            records.append(record)

            processed_new_count += 1
            if stream_handle is not None:
                append_jsonl_record(stream_handle, record)
                if checkpoint_every > 0 and processed_new_count % checkpoint_every == 0:
                    write_json(summary_path, build_summary())

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
    finally:
        if stream_handle is not None:
            stream_handle.close()

    if not use_streaming_writes:
        write_jsonl(output_path, records)

    summary = build_summary()
    write_json(summary_path, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve Reddit comment IDs through PullPush.")
    parser.add_argument("--queue", default="pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl")
    parser.add_argument("--output", default="data/raw/reddit_bao_pullpush_hydrated.jsonl")
    parser.add_argument("--summary", default="pilot/results/reddit_bao_pullpush_summary.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--retry-sleep-seconds", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--checkpoint-every", type=int, default=50)
    args = parser.parse_args()

    queue_records = load_jsonl(args.queue)

    def fetcher(comment_id: str) -> dict[str, Any]:
        return pullpush_fetcher(
            comment_id,
            timeout=args.timeout,
            user_agent=args.user_agent,
        )

    summary = resolve_queue(
        queue_records=queue_records,
        fetcher=fetcher,
        output_path=args.output,
        summary_path=args.summary,
        limit=args.limit,
        sleep_seconds=args.sleep_seconds,
        max_retries=args.max_retries,
        retry_sleep_seconds=args.retry_sleep_seconds,
        resume=args.resume,
        stream=args.stream,
        checkpoint_every=args.checkpoint_every,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
