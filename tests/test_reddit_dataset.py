import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from regime_pilot.reddit_dataset import (
    build_hydration_queue,
    build_id_core,
    build_policy_cards,
    write_jsonl,
)


def _write_metadata(path: Path, subreddit: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "display_name": subreddit,
        "title": f"r/{subreddit}",
        "description": "General description\n\n# Comment Rules\n1. Be civil\n2. Stay on topic",
        "rules": {
            "rules": [
                {
                    "kind": "comment",
                    "short_name": "Be civil",
                    "description": "Comments must not attack other users.",
                    "violation_reason": "Personal attack",
                    "priority": 0,
                },
                {
                    "kind": "comment",
                    "short_name": "Stay on topic",
                    "description": "Comments must discuss the linked topic.",
                    "violation_reason": "Off topic",
                    "priority": 1,
                },
                {
                    "kind": "link",
                    "short_name": "No reposts",
                    "description": "Submissions must not repost existing content.",
                    "violation_reason": "Repost",
                    "priority": 2,
                },
            ],
            "site_rules": ["Spam"],
        },
    }
    path.write_text(json.dumps(metadata), encoding="utf-8")


class RedditDatasetTests(unittest.TestCase):
    def test_build_policy_cards_extracts_comment_rules_without_losing_link_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_metadata(
                root / "rules" / "2022-06-27" / "science" / "subreddit_metadata.json",
                "science",
            )

            cards = build_policy_cards(root / "rules" / "2022-06-27", ["science"])

        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertEqual(card["policy_card_id"], "reddit_science_p0_public_policy")
        self.assertEqual(card["subreddit"], "science")
        self.assertEqual([rule["short_name"] for rule in card["structured_comment_rules"]], ["Be civil", "Stay on topic"])
        self.assertEqual([rule["short_name"] for rule in card["structured_link_rules"]], ["No reposts"])
        self.assertIn("Comment Rules", card["description"])
        self.assertEqual(card["site_rules"], ["Spam"])

    def test_build_id_core_samples_balanced_records_and_keeps_text_unhydrated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            split_dir = root / "balanced" / "data-en"
            split_dir.mkdir(parents=True, exist_ok=True)
            df = pd.DataFrame(
                [
                    {"label": 0, "id": "allow_sci_a", "subreddit": "science"},
                    {"label": 0, "id": "allow_sci_b", "subreddit": "science"},
                    {"label": 1, "id": "remove_sci_a", "subreddit": "science"},
                    {"label": 1, "id": "remove_sci_b", "subreddit": "science"},
                    {"label": 0, "id": "allow_news_a", "subreddit": "news"},
                    {"label": 1, "id": "remove_news_a", "subreddit": "news"},
                    {"label": 0, "id": "ignore_a", "subreddit": "worldnews"},
                    {"label": 1, "id": "ignore_b", "subreddit": "worldnews"},
                ]
            )
            df.to_pickle(split_dir / "test-en.pkl")

            records = build_id_core(
                dataset_root=root,
                source_view="balanced/data-en",
                split_name="test-en",
                subreddits=["science", "news"],
                samples_per_subreddit=2,
                seed=7,
            )

        self.assertEqual(len(records), 4)
        self.assertEqual({record["subreddit"] for record in records}, {"science", "news"})
        self.assertEqual({record["label"] for record in records}, {0, 1})
        for record in records:
            with self.subTest(record=record):
                self.assertEqual(record["dataset"], "multilingual_content_mod")
                self.assertEqual(record["source_view"], "balanced/data-en")
                self.assertEqual(record["split"], "test-en")
                self.assertEqual(record["text_status"], "unhydrated")
                self.assertTrue(record["reddit_fullname"].startswith("t1_"))
                self.assertEqual(
                    record["policy_card_id"],
                    f"reddit_{record['subreddit']}_p0_public_policy",
                )
                self.assertIn(record["expected_decision"], {"allow", "remove"})

    def test_build_hydration_queue_contains_only_fields_needed_to_fetch_text(self):
        records = [
            {
                "case_id": "RB-test-en-science-000001",
                "comment_id": "abc123",
                "reddit_fullname": "t1_abc123",
                "subreddit": "science",
                "label": 1,
                "expected_decision": "remove",
                "policy_card_id": "reddit_science_p0_public_policy",
                "split": "test-en",
            }
        ]

        queue = build_hydration_queue(records)

        self.assertEqual(
            queue,
            [
                {
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
            ],
        )

    def test_write_jsonl_creates_parent_directory_and_round_trips_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "nested" / "records.jsonl"
            write_jsonl(output, [{"a": 1}, {"b": 2}])

            lines = output.read_text(encoding="utf-8").splitlines()

        self.assertEqual([json.loads(line) for line in lines], [{"a": 1}, {"b": 2}])


if __name__ == "__main__":
    unittest.main()
