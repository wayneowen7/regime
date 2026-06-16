import json
from pathlib import Path
import tempfile
import unittest

from regime_pilot.reddit_pullpush_resolver import (
    resolve_pullpush_record,
    resolve_queue,
    summarize_resolved_records,
)
from regime_pilot.schema import load_jsonl


QUEUE_ITEM = {
    "case_id": "RB-test-en-science-000001",
    "comment_id": "abc123",
    "reddit_fullname": "t1_abc123",
    "subreddit": "science",
    "label": 1,
    "expected_decision": "remove",
    "policy_card_id": "reddit_science_p0_public_policy",
    "split": "test-en",
    "hydration_status": "pending",
}


def _pullpush_comment(**overrides):
    record = {
        "id": "abc123",
        "body": "This is the public comment body.",
        "subreddit": "science",
        "author": "example_user",
        "created_utc": 1650000000,
        "permalink": "/r/science/comments/thread/comment",
    }
    record.update(overrides)
    return record


class RedditPullPushResolverTests(unittest.TestCase):
    def test_resolve_pullpush_record_hydrates_matching_comment_and_hashes_body(self):
        record = resolve_pullpush_record(
            QUEUE_ITEM,
            {"data": [_pullpush_comment()]},
            retrieved_at="2026-06-16T00:00:00Z",
        )

        self.assertEqual(record["text_status"], "hydrated")
        self.assertEqual(record["hydration_status"], "hydrated")
        self.assertEqual(record["retrieval_source"], "pullpush")
        self.assertEqual(record["text"], "This is the public comment body.")
        self.assertEqual(record["body_sha256"], "41444c06ae90d630177cd2161c80deb6d25d287bee4821bec6a5ffd1ffa5e12d")
        self.assertTrue(record["subreddit_match"])
        self.assertEqual(record["retrieved_at"], "2026-06-16T00:00:00Z")

    def test_resolve_pullpush_record_marks_missing_when_data_is_empty(self):
        record = resolve_pullpush_record(
            QUEUE_ITEM,
            {"data": []},
            retrieved_at="2026-06-16T00:00:00Z",
        )

        self.assertEqual(record["text_status"], "missing")
        self.assertEqual(record["hydration_status"], "failed")
        self.assertIsNone(record["text"])
        self.assertIn("No PullPush data", record["hydration_error"])

    def test_resolve_pullpush_record_marks_deleted_or_removed_as_unavailable(self):
        for body in ["[deleted]", "[removed]", ""]:
            with self.subTest(body=body):
                record = resolve_pullpush_record(
                    QUEUE_ITEM,
                    {"data": [_pullpush_comment(body=body)]},
                    retrieved_at="2026-06-16T00:00:00Z",
                )

                self.assertEqual(record["text_status"], "unavailable")
                self.assertEqual(record["hydration_status"], "failed")
                self.assertIsNone(record["text"])

    def test_resolve_pullpush_record_marks_subreddit_mismatch_without_keeping_text(self):
        record = resolve_pullpush_record(
            QUEUE_ITEM,
            {"data": [_pullpush_comment(subreddit="news")]},
            retrieved_at="2026-06-16T00:00:00Z",
        )

        self.assertEqual(record["text_status"], "subreddit_mismatch")
        self.assertEqual(record["hydration_status"], "failed")
        self.assertFalse(record["subreddit_match"])
        self.assertEqual(record["returned_subreddit"], "news")
        self.assertIsNone(record["text"])

    def test_summarize_resolved_records_counts_statuses_without_text(self):
        records = [
            {"text_status": "hydrated", "subreddit": "science", "text": "secret text"},
            {"text_status": "missing", "subreddit": "science", "text": None, "hydration_error": "No PullPush data"},
            {"text_status": "hydrated", "subreddit": "news", "text": "another secret"},
        ]

        summary = summarize_resolved_records(records)

        self.assertEqual(summary["record_count"], 3)
        self.assertEqual(summary["status_counts"], {"hydrated": 2, "missing": 1})
        self.assertEqual(summary["subreddit_counts"], {"news": 1, "science": 2})
        self.assertEqual(
            summary["status_by_subreddit"],
            {
                "news": {"hydrated": 1},
                "science": {"hydrated": 1, "missing": 1},
            },
        )
        self.assertEqual(summary["error_counts"], {"No PullPush data": 1})
        self.assertNotIn("secret text", json.dumps(summary))

    def test_resolve_queue_writes_raw_records_and_text_free_summary(self):
        queue = [QUEUE_ITEM, {**QUEUE_ITEM, "case_id": "RB-test-en-news-000002", "comment_id": "missing", "subreddit": "news"}]

        def fetcher(comment_id):
            if comment_id == "missing":
                return {"data": []}
            return {"data": [_pullpush_comment(id=comment_id)]}

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "raw.jsonl"
            summary = Path(tmp) / "summary.json"

            result = resolve_queue(
                queue_records=queue,
                fetcher=fetcher,
                output_path=output,
                summary_path=summary,
                retrieved_at="2026-06-16T00:00:00Z",
            )
            raw_records = load_jsonl(output)
            summary_data = json.loads(summary.read_text(encoding="utf-8"))

        self.assertEqual(result["status_counts"], {"hydrated": 1, "missing": 1})
        self.assertEqual(len(raw_records), 2)
        self.assertEqual(raw_records[0]["text"], "This is the public comment body.")
        self.assertNotIn("This is the public comment body.", json.dumps(summary_data))

    def test_resolve_queue_retries_transient_fetch_errors(self):
        attempts = {"abc123": 0}

        def flaky_fetcher(comment_id):
            attempts[comment_id] += 1
            if attempts[comment_id] == 1:
                raise RuntimeError("PullPush HTTP 429 for abc123")
            return {"data": [_pullpush_comment(id=comment_id)]}

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "raw.jsonl"
            summary = Path(tmp) / "summary.json"

            result = resolve_queue(
                queue_records=[QUEUE_ITEM],
                fetcher=flaky_fetcher,
                output_path=output,
                summary_path=summary,
                max_retries=1,
                retry_sleep_seconds=0.0,
                retrieved_at="2026-06-16T00:00:00Z",
            )

        self.assertEqual(attempts["abc123"], 2)
        self.assertEqual(result["status_counts"], {"hydrated": 1})

    def test_resolve_queue_resume_skips_existing_comment_ids_and_appends_new_records(self):
        calls = []
        existing_record = {
            **QUEUE_ITEM,
            "text": "Already collected.",
            "body_sha256": "existing-hash",
            "text_status": "hydrated",
            "hydration_status": "hydrated",
            "retrieval_source": "pullpush",
            "retrieved_at": "2026-06-16T00:00:00Z",
        }
        new_item = {
            **QUEUE_ITEM,
            "case_id": "RB-test-en-news-000002",
            "comment_id": "new123",
            "subreddit": "news",
        }

        def fetcher(comment_id):
            calls.append(comment_id)
            return {"data": [_pullpush_comment(id=comment_id, subreddit="news")]}

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "raw.jsonl"
            summary = Path(tmp) / "summary.json"
            output.write_text(json.dumps(existing_record) + "\n", encoding="utf-8")

            result = resolve_queue(
                queue_records=[QUEUE_ITEM, new_item],
                fetcher=fetcher,
                output_path=output,
                summary_path=summary,
                resume=True,
                checkpoint_every=1,
                retrieved_at="2026-06-16T00:00:00Z",
            )
            raw_records = load_jsonl(output)

        self.assertEqual(calls, ["new123"])
        self.assertEqual(len(raw_records), 2)
        self.assertEqual(raw_records[0]["text"], "Already collected.")
        self.assertEqual(raw_records[1]["comment_id"], "new123")
        self.assertEqual(result["record_count"], 2)
        self.assertEqual(result["skipped_existing_count"], 1)
        self.assertEqual(result["processed_new_count"], 1)

    def test_resolve_queue_checkpoint_summary_reflects_partial_stream_progress(self):
        queue = [
            QUEUE_ITEM,
            {
                **QUEUE_ITEM,
                "case_id": "RB-test-en-news-000002",
                "comment_id": "new123",
                "subreddit": "news",
            },
        ]

        def fetcher(comment_id):
            if comment_id == "new123":
                raise KeyboardInterrupt("stop after first streamed record")
            return {"data": [_pullpush_comment(id=comment_id)]}

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "raw.jsonl"
            summary = Path(tmp) / "summary.json"
            with self.assertRaises(KeyboardInterrupt):
                resolve_queue(
                    queue_records=queue,
                    fetcher=fetcher,
                    output_path=output,
                    summary_path=summary,
                    stream=True,
                    checkpoint_every=1,
                    retrieved_at="2026-06-16T00:00:00Z",
                )
            raw_records = load_jsonl(output)
            summary_data = json.loads(summary.read_text(encoding="utf-8"))

        self.assertEqual(len(raw_records), 1)
        self.assertEqual(raw_records[0]["comment_id"], "abc123")
        self.assertEqual(summary_data["record_count"], 1)
        self.assertEqual(summary_data["processed_new_count"], 1)
        self.assertTrue(summary_data["streaming"])


if __name__ == "__main__":
    unittest.main()
