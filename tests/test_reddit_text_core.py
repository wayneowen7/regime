import json
from pathlib import Path
import tempfile
import unittest

from regime_pilot.reddit_text_core import (
    build_text_core_snapshot,
    select_text_core_records,
)
from regime_pilot.run_reddit_text_benchmark import (
    build_reddit_prompt,
    parse_reddit_decision,
    run_reddit_text_benchmark,
)
from regime_pilot.schema import load_jsonl


def _raw_record(case_id, subreddit, label, text_status="hydrated", text=None):
    decision = "remove" if label == 1 else "allow"
    return {
        "case_id": case_id,
        "comment_id": case_id.lower(),
        "reddit_fullname": f"t1_{case_id.lower()}",
        "subreddit": subreddit,
        "split": "test-en",
        "label": label,
        "expected_decision": decision,
        "policy_card_id": f"reddit_{subreddit}_p0_public_policy",
        "text_status": text_status,
        "hydration_status": "hydrated" if text_status == "hydrated" else "failed",
        "text": text or f"Example {case_id} text",
        "body_sha256": f"hash-{case_id}",
        "retrieval_source": "pullpush",
        "retrieved_at": "2026-06-16T00:00:00Z",
    }


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, model, prompt):
        self.calls.append({"model": model, "prompt": prompt})
        return self.responses.pop(0)


class RedditTextCoreTests(unittest.TestCase):
    def test_select_text_core_records_balances_labels_when_available_and_reports_shortfalls(self):
        records = [
            _raw_record("S-allow-1", "science", 0),
            _raw_record("S-allow-2", "science", 0),
            _raw_record("S-remove-1", "science", 1),
            _raw_record("N-allow-1", "news", 0),
            _raw_record("N-allow-2", "news", 0),
            _raw_record("N-removed-body", "news", 1, text_status="unavailable"),
        ]

        selected, summary = select_text_core_records(
            records,
            samples_per_subreddit=2,
            seed=7,
            subreddits=["science", "news"],
        )

        self.assertEqual(len(selected), 4)
        science_labels = [record["label"] for record in selected if record["subreddit"] == "science"]
        news_labels = [record["label"] for record in selected if record["subreddit"] == "news"]
        self.assertEqual(sorted(science_labels), [0, 1])
        self.assertEqual(news_labels, [0, 0])
        self.assertEqual(
            summary["label_shortfalls"]["news"]["1"],
            {"requested": 1, "available": 0, "selected": 0},
        )
        self.assertFalse(summary["contains_raw_text"])
        self.assertNotIn("Example S-allow-1 text", json.dumps(summary))

    def test_build_text_core_snapshot_writes_local_text_and_text_free_summary(self):
        records = [
            _raw_record("S-allow-1", "science", 0),
            _raw_record("S-remove-1", "science", 1),
            _raw_record("N-allow-1", "news", 0),
            _raw_record("N-allow-2", "news", 0),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_path = root / "raw.jsonl"
            output_path = root / "text_core.jsonl"
            summary_path = root / "summary.json"
            raw_path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )

            summary = build_text_core_snapshot(
                raw_path=raw_path,
                output_path=output_path,
                summary_path=summary_path,
                samples_per_subreddit=2,
                seed=7,
                subreddits=["science", "news"],
            )
            selected = load_jsonl(output_path)
            saved_summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["selected_count"], 4)
        self.assertEqual(len(selected), 4)
        self.assertEqual(selected[0]["text"], "Example S-allow-1 text")
        self.assertEqual(saved_summary["selected_count"], 4)
        self.assertFalse(saved_summary["contains_raw_text"])
        self.assertNotIn("Example S-allow-1 text", json.dumps(saved_summary))

    def test_parse_reddit_decision_accepts_only_allow_remove_json(self):
        self.assertEqual(parse_reddit_decision('{"decision":"allow","rationale":"ok"}')["decision"], "allow")
        self.assertEqual(parse_reddit_decision('{"decision":"remove","rationale":"bad"}')["decision"], "remove")
        self.assertEqual(parse_reddit_decision('{"decision":"escalate"}')["decision"], "parse_error")
        self.assertEqual(parse_reddit_decision("not json")["decision"], "parse_error")

    def test_run_reddit_text_benchmark_compares_comment_only_and_public_policy_without_text_in_summary(self):
        cases = [
            _raw_record("S-allow-1", "science", 0, text="Helpful science comment."),
            _raw_record("S-remove-1", "science", 1, text="Cheap joke."),
        ]
        policy_cards = [
            {
                "policy_card_id": "reddit_science_p0_public_policy",
                "subreddit": "science",
                "title": "Science",
                "structured_comment_rules": [
                    {
                        "short_name": "No low-effort comments",
                        "description": "Cheap jokes should be removed.",
                        "violation_reason": "Low effort",
                    }
                ],
                "site_rules": ["Spam"],
            }
        ]
        client = FakeClient(
            [
                '{"decision":"allow","rationale":"looks fine"}',
                '{"decision":"allow","rationale":"missed policy"}',
                '{"decision":"allow","rationale":"looks fine"}',
                '{"decision":"remove","rationale":"low effort"}',
            ]
        )

        result = run_reddit_text_benchmark(
            cases=cases,
            policy_cards=policy_cards,
            client=client,
            model="fake",
            conditions=["comment_only", "public_policy"],
        )

        self.assertEqual(result["summaries"]["comment_only"]["accuracy"], 0.5)
        self.assertEqual(result["summaries"]["public_policy"]["accuracy"], 1.0)
        self.assertIn("No low-effort comments", client.calls[2]["prompt"])
        self.assertNotIn("No low-effort comments", client.calls[0]["prompt"])
        self.assertFalse(result["text_free_summary"]["contains_raw_text"])
        self.assertNotIn("Cheap joke.", json.dumps(result["text_free_summary"]))

    def test_build_reddit_prompt_keeps_comment_only_condition_policy_free(self):
        case = _raw_record("S-allow-1", "science", 0, text="Helpful science comment.")
        policy_card = {
            "policy_card_id": "reddit_science_p0_public_policy",
            "subreddit": "science",
            "structured_comment_rules": [{"short_name": "No jokes", "description": "No jokes."}],
            "site_rules": [],
        }

        comment_prompt = build_reddit_prompt(case, policy_card, condition="comment_only")
        policy_prompt = build_reddit_prompt(case, policy_card, condition="public_policy")

        self.assertIn("Helpful science comment.", comment_prompt)
        self.assertNotIn("No jokes", comment_prompt)
        self.assertIn("No jokes", policy_prompt)


if __name__ == "__main__":
    unittest.main()
