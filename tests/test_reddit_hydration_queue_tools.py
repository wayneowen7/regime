import json
from pathlib import Path
import tempfile
import unittest

from regime_pilot.reddit_hydration_queue_tools import (
    build_priority_queue,
    build_priority_queue_files,
)
from regime_pilot.schema import load_jsonl


def _queue_item(comment_id, label=1, subreddit="science"):
    decision = "remove" if label == 1 else "allow"
    return {
        "case_id": f"case-{comment_id}",
        "comment_id": comment_id,
        "reddit_fullname": f"t1_{comment_id}",
        "subreddit": subreddit,
        "label": label,
        "expected_decision": decision,
        "policy_card_id": f"reddit_{subreddit}_p0_public_policy",
        "split": "train",
        "hydration_status": "pending",
    }


def _resolved(comment_id, label=1, status="hydrated", text="body"):
    item = _queue_item(comment_id, label=label)
    item.update(
        {
            "text_status": status,
            "hydration_status": "hydrated" if status == "hydrated" else "failed",
            "text": text if status == "hydrated" else None,
            "retrieval_source": "pullpush",
        }
    )
    return item


class RedditHydrationQueueToolsTests(unittest.TestCase):
    def test_build_priority_queue_skips_hydrated_and_selects_unseen_and_error_label(self):
        queue = [
            _queue_item("already_hydrated", label=1),
            _queue_item("transient_error", label=1),
            _queue_item("unseen_remove", label=1),
            _queue_item("terminal_unavailable", label=1),
            _queue_item("allow_error", label=0),
        ]
        resolved = [
            _resolved("already_hydrated", label=1, status="hydrated"),
            _resolved("transient_error", label=1, status="error"),
            _resolved("terminal_unavailable", label=1, status="unavailable"),
            _resolved("allow_error", label=0, status="error"),
        ]

        selected, summary = build_priority_queue(
            queue_records=queue,
            resolved_records=resolved,
            label=1,
            include_statuses=["error"],
            include_unseen=True,
        )

        self.assertEqual([item["comment_id"] for item in selected], ["transient_error", "unseen_remove"])
        self.assertEqual(summary["selected_count"], 2)
        self.assertEqual(summary["selected_reason_counts"], {"error": 1, "not_seen": 1})
        self.assertEqual(summary["skipped_hydrated_count"], 1)
        self.assertEqual(summary["skipped_status_counts"], {"unavailable": 1})
        self.assertFalse(summary["contains_raw_text"])
        self.assertNotIn("body", json.dumps(summary))

    def test_build_priority_queue_files_writes_text_free_queue_and_summary(self):
        queue = [_queue_item("already_hydrated"), _queue_item("transient_error"), _queue_item("unseen_remove")]
        resolved = [_resolved("already_hydrated", status="hydrated"), _resolved("transient_error", status="error")]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.jsonl"
            resolved_path = root / "resolved.jsonl"
            output_path = root / "priority.jsonl"
            summary_path = root / "summary.json"
            queue_path.write_text("".join(json.dumps(item) + "\n" for item in queue), encoding="utf-8")
            resolved_path.write_text("".join(json.dumps(item) + "\n" for item in resolved), encoding="utf-8")

            summary = build_priority_queue_files(
                queue_path=queue_path,
                resolved_path=resolved_path,
                output_path=output_path,
                summary_path=summary_path,
                label=1,
                include_statuses=["error"],
                include_unseen=True,
            )
            selected = load_jsonl(output_path)
            saved_summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual([item["comment_id"] for item in selected], ["transient_error", "unseen_remove"])
        self.assertEqual(saved_summary["selected_count"], 2)
        self.assertEqual(summary["selected_count"], 2)
        self.assertNotIn("body", json.dumps(saved_summary))


if __name__ == "__main__":
    unittest.main()
